import sys
import traceback
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




def vectorize(csv_filename: str = "sample.csv", out_dir_name: str = "vectorstore", db_name: str = "db_faiss"):
	"""Create embeddings and a FAISS vectorstore from the CSV and save to disk.

	Returns the created DB object (or None on failure).
	"""
	base = Path(__file__).parent
	csv_path = base / csv_filename
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
		embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")
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


def perform_search(query: str, k: int = 3, csv_filename: str = "sample.csv", out_dir_name: str = "vectorstore", recreate_if_missing: bool = False, db_name: str = "db_faiss"):
	"""Perform a semantic search using an existing saved FAISS vectorstore.

	If the saved DB is missing and recreate_if_missing==True, the function will attempt to
	recreate the vectorstore by calling `vectorize()`.
	"""
	base = Path(__file__).parent
	out_dir = base / out_dir_name
	db_path = out_dir / db_name

	# Prepare embeddings (needed for loading)
	try:
		embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
	except Exception:
		print("Failed while creating embeddings object needed to load DB:")
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
			print("Loaded vectorstore from", str(db_path))
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

	# Perform the search
	try:
		results = db.similarity_search(query, k=k)
		print(results)
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
	parser.add_argument("--dbname", type=str, default="db_faiss", help="Name to use for saved vectorstore (folder name)")
	parser.add_argument("--query", type=str, help="Run a semantic search with this query")
	parser.add_argument("--k", type=int, default=3, help="Number of results to return for search")
	parser.add_argument("--recreate", action="store_true", help="If search is requested and DB missing, recreate it")
	args = parser.parse_args()

	if args.vectorize:
		vectorize(db_name=args.dbname)

	if args.query:
		perform_search(args.query, k=args.k, recreate_if_missing=args.recreate, db_name=args.dbname)
    
