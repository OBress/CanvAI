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


def main():
	base = Path(__file__).parent
	csv_path = base / "sample.csv"
	if not csv_path.exists():
		print(f"CSV file not found at {csv_path.resolve()}")
		print("Place 'sample.csv' next to this script or run from the Backend/vector_db folder.")
		return
	
	# Step 1 — Load CSV data
	try:
		loader = CSVLoader(file_path=str(csv_path), encoding="utf-8")
		data = loader.load()
	except Exception:
		print("Failed to load CSV data:")
		traceback.print_exc()
		return

	print("loaded data")

	# Step 2 — Split long text entries into smaller chunks
	try:
		splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
		docs = splitter.split_documents(data)
	except Exception:
		print("Failed while splitting documents:")
		traceback.print_exc()
		return



	# Step 3 — Generate embeddings with a Sentence Transformer
	try:
		embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
	except Exception:
		print("Failed while creating embeddings object:")
		traceback.print_exc()
		return



	# Step 4 — Create FAISS vector database
	try:
		db = FAISS.from_documents(docs, embeddings)
		out_dir = base / "vectorstore"
		out_dir.mkdir(exist_ok=True)
		db.save_local(str(out_dir / "db_faiss"))
	except Exception:
		print("Failed while creating or saving FAISS DB:")
		traceback.print_exc()
		return

	print("db saved to", str(out_dir / "db_faiss"))

	# Step 5 — Perform semantic search
	try:
		results = db.similarity_search("Emma's email is what?", k=3)
		print(results)
	except Exception:
		print("Failed during similarity search:")
		traceback.print_exc()


if __name__ == "__main__":
	main()
