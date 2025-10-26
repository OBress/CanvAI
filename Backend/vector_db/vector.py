import sys
import traceback
import re
from pathlib import Path

try:
	from langchain_community.document_loaders.csv_loader import CSVLoader
	from langchain_text_splitters import RecursiveCharacterTextSplitter
	from langchain_community.vectorstores import FAISS
	from langchain_huggingface import HuggingFaceEmbeddings
except Exception as e:
	print("ImportError while importing dependencies:", e)
	print("Make sure required packages are installed. Try: pip install -r requirements.txt")
	# exit with non-zero so CI / callers know it failed
	sys.exit(1)

# Cache for embeddings model to avoid reloading on every search
_EMBEDDINGS_CACHE = None




def vectorize(csv_filename: str = "sample.csv", out_dir_name: str = "vectorstore", db_name: str = "db_faiss"):
	"""Create embeddings and a FAISS vectorstore from the CSV and save to disk.

	Returns the created DB object (or None on failure).
	"""
	base = Path(__file__).parent
	# Prefer a top-level project 'data' folder (two parents up from this file).
	# e.g., <repo>/data/<csv_filename>
	project_root = Path(__file__).resolve().parents[2]
	data_dir = project_root / "data"
	if data_dir.exists():
		csv_path = data_dir / csv_filename
		print(f"Using CSV from project data folder: {csv_path}")
	else:
		csv_path = base / csv_filename
		print(f"Using CSV from script folder: {csv_path}")
	if not csv_path.exists():
		print(f"CSV file not found at {csv_path.resolve()}")
		return None

	# Step 1 — Load CSV data
	try:
		loader = CSVLoader(file_path=str(csv_path), encoding="utf-8")
		data = loader.load()
	except Exception:
		print("Failed to load CSV data:")
		traceback.print_exc()
		return None

	print("loaded data")

	# Step 2 — Split long text entries into smaller chunks
	try:
		splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
		docs = splitter.split_documents(data)
	except Exception:
		print("Failed while splitting documents:")
		traceback.print_exc()
		return None

	print("split data (document count)", len(docs))

	# Step 3 — Generate embeddings with a Sentence Transformer
	try:
		embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
	except Exception:
		print("Failed while creating embeddings object:")
		traceback.print_exc()
		return None

	print("generated embeddings")

	# Step 4 — Create FAISS vector database
	try:
		db = FAISS.from_documents(docs, embeddings)
		out_dir = base / out_dir_name
		out_dir.mkdir(exist_ok=True)
		db.save_local(str(out_dir / db_name))
	except Exception:
		print("Failed while creating or saving FAISS DB:")
		traceback.print_exc()
		return None

	print("db saved to", str(out_dir / db_name))
	return db


def extract_identifiers(query: str) -> dict:
	"""
	Extract various types of identifiers from a query that should be exact-matched.
	Returns a dict of identifier types and their values.
	
	This makes the search scalable - it works for any course code, assignment, etc.
	without hardcoding specific values.
	"""
	identifiers = {
		'course_codes': [],
		'course_numbers': [],
		'assignment_patterns': [],
		'raw_numbers': []
	}
	
	# Course codes: CMPSC461, CMPEN 270, etc.
	course_code_pattern = r'\b([A-Z]{4,6})\s*[\-]?\s*(\d{3})\b'
	for match in re.finditer(course_code_pattern, query, re.IGNORECASE):
		dept, num = match.group(1), match.group(2)
		identifiers['course_codes'].append(f"{dept.upper()}{num}")
		identifiers['course_codes'].append(f"{dept.lower().capitalize()}{num}")
		identifiers['course_numbers'].append(num)  # Also keep just the number
	
	# Assignment patterns: "Assignment 1", "HW #2", "Quiz 3", etc.
	assignment_pattern = r'\b(assignment|homework|hw|quiz|exam|test|project|lab)\s*#?\s*(\d+)\b'
	for match in re.finditer(assignment_pattern, query, re.IGNORECASE):
		identifiers['assignment_patterns'].append(match.group(0))
	
	# Standalone important numbers (might be assignment numbers, etc.)
	# But avoid dates and common numbers
	number_pattern = r'\b(\d{1,3})\b'
	for match in re.finditer(number_pattern, query):
		num = match.group(1)
		# Skip very common/likely non-identifier numbers
		if num not in ['1', '2', '3', '10', '20', '100']:
			identifiers['raw_numbers'].append(num)
	
	return identifiers


def should_require_identifier(results, identifiers: dict, threshold: float = 0.5) -> bool:
	"""
	Decide if we should enforce identifier filtering based on how well
	current results match the identifiers.
	
	If top results don't contain the identifier, we should filter.
	"""
	if not any(identifiers.values()):
		return False
	
	# Check if top results contain any identifier
	for doc, score in results[:3]:  # Check top 3 results
		text = doc.page_content.lower()
		
		# Check if any identifier appears
		for id_list in identifiers.values():
			if any(str(id_val).lower() in text for id_val in id_list):
				return False  # Found identifier in top results, no filtering needed
	
	return True  # Identifier not in top results, need to filter


def filter_by_identifiers(results, identifiers: dict):
	"""
	Filter results to only include those containing at least one identifier.
	"""
	if not any(identifiers.values()):
		return results
	
	filtered = []
	for doc, score in results:
		text = doc.page_content.lower()
		metadata_text = ' '.join(str(v).lower() for v in doc.metadata.values())
		combined_text = f"{text} {metadata_text}"
		
		# Check if document contains any identifier
		match = False
		for id_type, id_list in identifiers.items():
			if id_type == 'course_numbers':
				# For course numbers alone, be more strict - require nearby context
				# Skip standalone numbers for now to avoid false positives
				continue
			
			for id_val in id_list:
				if str(id_val).lower() in combined_text:
					match = True
					break
			if match:
				break
		
		if match:
			filtered.append((doc, score))
	
	return filtered


def perform_search(query: str, k: int = 10, csv_filename: str = "sample.csv", out_dir_name: str = "vectorstore", recreate_if_missing: bool = False, db_name: str = "db_faiss", min_score: float = None):
	"""Perform an optimized hybrid semantic search using an existing saved FAISS vectorstore.
	
	Features:
	- Semantic search with FAISS vector similarity
	- Automatic identifier extraction (course codes, assignment names, etc.)
	- Smart hybrid filtering: combines semantic + exact matching when needed
	- Uses cached embeddings model for faster repeated searches
	- Correct score normalization for normalized embeddings (0-1 range)
	
	How Hybrid Search Works:
	- Detects identifiers in query (e.g., "CMPSC461", "Assignment 3")
	- If top semantic results don't contain the identifier, applies strict filtering
	- This prevents confusion between similar courses (e.g., CMPSC461 vs CMPSC221)
	- Scales automatically without hardcoding - works for any course/assignment
	
	Args:
		query: Search query string (e.g., "grades in CMPSC461", "Assignment 3")
		k: Number of results to return (default: 10)
		csv_filename: CSV file to use if recreating DB
		out_dir_name: Directory containing vectorstore
		recreate_if_missing: Whether to recreate DB if missing
		db_name: Name of the database
		min_score: Minimum similarity score (0-1), None for no filtering
	
	Returns:
		List of (Document, similarity_score) tuples, sorted by score (highest first)
		Returns None on error
	"""
	global _EMBEDDINGS_CACHE
	
	base = Path(__file__).parent
	out_dir = base / out_dir_name
	db_path = out_dir / db_name

	# Use cached embeddings model for efficiency (avoids reloading on every search)
	try:
		if _EMBEDDINGS_CACHE is None:
			print("Loading embeddings model (first time only)...")
			_EMBEDDINGS_CACHE = HuggingFaceEmbeddings(
				model_name="BAAI/bge-small-en-v1.5",
				encode_kwargs={'normalize_embeddings': True}  # Better cosine similarity
			)
		embeddings = _EMBEDDINGS_CACHE
	except Exception:
		print("Failed while creating embeddings object:")
		traceback.print_exc()
		return None

	# Load existing DB if possible
	db = None
	if db_path.exists():
		try:
			# allow_dangerous_deserialization must be set True when loading a locally saved
			# pickle-based vectorstore that we created ourselves. This is safe for local
			# files you control, but don't enable it for untrusted sources.
			db = FAISS.load_local(str(db_path), embeddings, allow_dangerous_deserialization=True)
			print(f"Loaded vectorstore from {db_path}")
		except Exception:
			print("Failed to load saved FAISS DB:")
			traceback.print_exc()
			# fall through to optional recreate

	if db is None:
		if recreate_if_missing:
			print("Saved vectorstore missing or failed to load — recreating by running vectorize()...")
			db = vectorize(csv_filename=csv_filename, out_dir_name=out_dir_name, db_name=db_name)
			if db is None:
				print("Recreation failed — aborting search.")
				return None
		else:
			print(f"No saved vectorstore found at {db_path}. Run the vectorize() function first or call with recreate_if_missing=True.")
			return None

	# Perform optimized search - always get scores for transparency
	try:
		query_clean = query.strip()
		
		# Extract identifiers from query for hybrid search
		identifiers = extract_identifiers(query_clean)
		has_identifiers = any(identifiers.values())
		
		# Fetch more results if we might filter by identifiers
		k_fetch = k * 5 if has_identifiers else k
		
		# Always use similarity_search_with_score for better results
		pairs = db.similarity_search_with_score(query_clean, k=k_fetch)
		
		if not pairs:
			print("No results found")
			return []
		
		# Process and normalize scores
		results = []
		for doc, distance in pairs:
			# For normalized embeddings with FAISS, L2 distance relates to cosine similarity as:
			# cosine_similarity = 1 - (distance^2 / 2)
			similarity = max(0.0, 1.0 - (distance * distance / 2.0))
			
			# Apply min_score filter if specified
			if min_score is None or similarity >= min_score:
				results.append((doc, similarity))
		
		# Sort by similarity (highest first)
		results.sort(key=lambda x: x[1], reverse=True)
		
		# Smart filtering: only filter if identifiers exist AND top results don't match
		if has_identifiers and should_require_identifier(results, identifiers):
			identifier_list = [v for vals in identifiers.values() for v in vals if v]
			print(f"Detected identifiers: {identifier_list}")
			print("Top results don't match identifiers - applying strict filtering...")
			results = filter_by_identifiers(results, identifiers)
			
			if not results:
				print("Warning: No results found after identifier filtering. Try a broader search.")
				# Fall back to original results if filtering removes everything
				results = []
				for doc, distance in pairs:
					similarity = max(0.0, 1.0 - (distance * distance / 2.0))
					if min_score is None or similarity >= min_score:
						results.append((doc, similarity))
				results.sort(key=lambda x: x[1], reverse=True)
		
		# Limit to k results
		results = results[:k]
		
		# Print summary
		print(f"Query: '{query_clean}'")
		print(f"Found {len(results)} results" + (f" (filtered by min_score={min_score})" if min_score else ""))
		for i, (doc, score) in enumerate(results[:3], 1):  # Show top 3
			preview = doc.page_content[:80].replace('\n', ' ')
			print(f"  {i}. Score: {score:.4f} | {preview}...")
		
		return results
		
	except Exception:
		print("Failed during similarity search:")
		traceback.print_exc()
		return None




if __name__ == "__main__":
	# Simple CLI to either build the vectorstore or run a query against it
	import argparse
	parser = argparse.ArgumentParser(description="Vectorize CSV and/or perform semantic search")
	parser.add_argument("--vectorize", action="store_true", help="Run vectorization to build/save the vector database")
	parser.add_argument("--dbname", "--db_name", dest="dbname", type=str, default="db_faiss", help="Name to use for saved vectorstore (folder name)")
	parser.add_argument("--csv", "--csv_filename", dest="csv", type=str, default="sample.csv", help="CSV filename to vectorize (relative to project data/ or script folder)")
	parser.add_argument("--outdir", dest="outdir", type=str, default="vectorstore", help="Directory to save/load the vectorstore")
	parser.add_argument("--query", type=str, help="Run a semantic search with this query")
	parser.add_argument("--k", type=int, default=5, help="Number of results to return for search (default: 5)")
	parser.add_argument("--recreate", action="store_true", help="If search is requested and DB missing, recreate it")
	parser.add_argument("--min_score", type=float, default=None, help="Minimum similarity (0-1) required to return a result; results below are filtered out")
	parser.add_argument("--export", nargs="?", const="vectorstore_export.csv", help="Export saved vectorstore to CSV; optionally provide output filename")
	args = parser.parse_args()

	if args.vectorize:
		vectorize(csv_filename=args.csv, out_dir_name=args.outdir, db_name=args.dbname)

	if args.query:
		results = perform_search(args.query, k=args.k, csv_filename=args.csv, out_dir_name=args.outdir, recreate_if_missing=args.recreate, db_name=args.dbname, min_score=args.min_score)
		
		# Enhanced result display
		if results:
			print(f"\n{'='*80}")
			print(f"DETAILED RESULTS ({len(results)} found)")
			print(f"{'='*80}")
			for i, (doc, score) in enumerate(results, 1):
				print(f"\n[Result {i}] Similarity Score: {score:.4f}")
				print(f"Content: {doc.page_content[:200]}...")
				if doc.metadata:
					print(f"Metadata: {doc.metadata}")
				print("-" * 80)

	