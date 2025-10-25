from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
import uvicorn
from llm import query_to_structured
from Backend.vector_db.vector import perform_search

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Imports for functions used during startup
    from Backend.vector_db.vector import vectorize

    # Initialize vector stores for all CSV files
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    # All filetypes that are going made into vector stores
    csv_filetypes = [
        "users.csv",
        "courses.csv",
        "grades.csv",
        "course_content_summary.csv",
    ]
    # Runs through each CSV and creates a vector store for it
    for csv_filename in csv_filetypes:
        # CSV's will be located in data directory
        csv_path = data_dir / csv_filename
        # Error handling for missing CSV files
        if not csv_path.exists():
            print(f"Skipping missing CSV: {csv_path}")
            continue
        # Use the stem of the CSV filename as the DB name
        db_name = csv_filename.split(".")[0]
        # Create the vector store
        vectorize(csv_filename=csv_filename, db_name=db_name)

    # Initialize Canvas API and populate extract_text files 


    yield


app = FastAPI(lifespan=lifespan)

# Endpoint to handle search queries
@app.get("/search")
async def search(query: str):
    # Calls the llm with the query to get structured information on what to search for in the vector DB
    structured_query_to_DB = query_to_structured(query)
    # Feed the information into the vector DB search function to output top relevant documents
    relevant_documents = perform_search(structured_query_to_DB)
    # TODO: Integrate new llm function that takes in relevant documents and outputs final response

    # FOr now returns relevant documents to see if it works, will output response later

    return {"relevant documents": relevant_documents}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
