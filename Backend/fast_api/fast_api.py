from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Imports for functions used during startup
    from Backend.vector_db.vector import vectorize

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
        
    yield


app = FastAPI(lifespan=lifespan)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
