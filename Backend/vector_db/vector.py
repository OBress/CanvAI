from langchain.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

# Step 1 — Load CSV data
loader = CSVLoader(file_path="titanic.csv", encoding="utf-8")
data = loader.load()

# Step 2 — Split long text entries into smaller chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
docs = splitter.split_documents(data)

# Step 3 — Generate embeddings with a Sentence Transformer
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Step 4 — Create FAISS vector database
db = FAISS.from_documents(docs, embeddings)
db.save_local("vectorstore/db_faiss")

# Step 5 — Perform semantic search
results = db.similarity_search("survival rate of women passengers", k=3)
