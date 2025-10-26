import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from vector_db.vector import perform_search, vectorize  # noqa: E402
from llm import query_to_structured, generate_user_response_from_file  # noqa: E402
# if __package__ in (None, ""):
#     from chat_store import ensure_chat_storage  # type: ignore  # noqa: E402
#     from chat_router import router as chat_router  # type: ignore  # noqa: E402
# else:
#     from .chat_store import ensure_chat_storage  # noqa: E402
#     from .chat_router import router as chat_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize vector stores for all CSV files
    data_dir = PROJECT_ROOT / "sample_data"
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

    #TODO: Initialize Canvas API and populate extract_text files (if time allows)
    # ensure_chat_storage()

    yield


app = FastAPI(lifespan=lifespan)
# app.include_router(chat_router)


# Endpoint to handle search queries
@app.get("/search")
async def search(query: str):
    # Calls the llm with the query to get structured information on what to search for in the vector DB
    structured_query_to_DB = query_to_structured(query)
    
    print(structured_query_to_DB)
    # Handle error cases returned from query_to_structured
    if "error" in structured_query_to_DB:
        return {"response": "Failed to generate structured query to Vector DB.", "error": structured_query_to_DB["error"]}

    # Feed the information into the vector DB search function to output top relevant documents
    print(structured_query_to_DB["table_to_query"] + ".csv", " and ", structured_query_to_DB["table_to_query"])
    relevant_documents = perform_search(query=query, csv_filename=(structured_query_to_DB["table_to_query"] + ".csv"), db_name=structured_query_to_DB["table_to_query"])
    # Error handling for no relevant documents found
    if not relevant_documents:
        return {"response": "No relevant documents found in the database."}

    # Llm function that takes in relevant documents and outputs final response
    print(relevant_documents)
    response = generate_user_response_from_file(user_query=query, file_path = relevant_documents)

    return {"response": response}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)