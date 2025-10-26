import sys
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from vector_db.vector import perform_search, vectorize  # noqa: E402
from llm import query_to_structured, generate_user_response_from_file  # noqa: E402

if __package__ in (None, ""):
    from chat_store import ensure_chat_storage  # type: ignore  # noqa: E402
    from chat_router import router as chat_router  # type: ignore  # noqa: E402
    from user_store import (  # type: ignore  # noqa: E402
        ensure_user_storage,
        format_user_payload,
        get_user_settings,
    )
    from user_router import router as user_router  # type: ignore  # noqa: E402
else:
    from .chat_store import ensure_chat_storage  # noqa: E402
    from .chat_router import router as chat_router  # noqa: E402
    from .user_store import (  # noqa: E402
        ensure_user_storage,
        format_user_payload,
        get_user_settings,
    )
    from .user_router import router as user_router  # noqa: E402


REQUIRED_API_KEY_FIELDS = [
    "canvas_key",
    "gemini_key",
    "canvas_base_url",
    "elevenlabs_api_key",
    "openrouter_api_key",
]


def _missing_api_keys() -> List[str]:
    """Return a list of required API keys that are still blank."""
    values = format_user_payload(get_user_settings())
    return [field for field in REQUIRED_API_KEY_FIELDS if not values.get(field)]


async def _wait_for_api_keys() -> None:
    """Block startup until every API key has been provided, logging progress."""
    pending = _missing_api_keys()
    if not pending:
        print("[CanvAI] All API keys detected. DONE!")
        return

    print(
        "[CanvAI] Waiting for required API keys before enabling backend: "
        + ", ".join(pending)
    )

    try:
        while pending:
            await asyncio.sleep(2)
            pending = _missing_api_keys()
            if pending:
                print(
                    "[CanvAI] Still waiting for API keys: "
                    + ", ".join(pending)
                )
    except asyncio.CancelledError:
        print(
            "[CanvAI] Shutdown requested while waiting for API keys. "
            "Exiting startup loop."
        )
        return

    print("[CanvAI] All API keys detected. DONE!")


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

    ensure_chat_storage()
    ensure_user_storage()
    await _wait_for_api_keys()

    #TODO: Initialize Canvas API and populate extract_text files (if time allows)
    


    yield


app = FastAPI(lifespan=lifespan)
app.include_router(chat_router)
app.include_router(user_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Endpoint to handle search queries
@app.get("/search")
async def search(query: str):
    missing = _missing_api_keys()
    if missing:
        message = (
            "Required API keys are missing. Please add: "
            + ", ".join(missing)
        )
        return {"response": message, "error": "missing_api_keys"}

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
