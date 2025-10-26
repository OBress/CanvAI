# import requests
# import json

# # ======= CONFIGURATION =======
# API_KEY = "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"  # Replace with the key your friend gave you
# MODEL = "google/gemini-2.5-pro"
# ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# def query_to_structured(user_query):
#     prompt = f"""
#     Convert this user query into a structured JSON query:
#     User query: "{user_query}"
#     Output format:
#     {{
#         "student_name": "<student_name>"
#         "course": "<course_type>",
#         "assignment": "<assignment_name>",
#         "which table needs queried": "<
#         "announcement": {{ "<filter_key>": "<filter_value>" }},
#         "syllabus": <file>
#     }}
#     """
    
#     headers = {
#         "Authorization": f"Bearer {API_KEY}",
#         "Content-Type": "application/json"
#     }
    
#     data = {
#         "model": MODEL,
#         "messages": [
#             {"role": "user", "content": prompt}
#         ],
#         "temperature": 0
#     }
    
#     response = requests.post(ENDPOINT, headers=headers, json=data)
    
#     if response.status_code == 200:
#         content = response.json()
#         return content["choices"][0]["message"]["content"]
#     else:
#         return f"API Error {response.status_code}: {response.text}"

# if __name__ == "__main__":
#     user_input = input("Enter your query: ")
#     result = query_to_structured(user_input)
#     print("\nStructured Query Output:\n", result)

import csv
import requests
import json
import re
import ast
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ======= CONFIGURATION =======

PROJECT_ROOT = Path(__file__).resolve().parent
USER_SETTINGS_PATH = PROJECT_ROOT / "data" / "user_db" / "user_settings.csv"


def _get_openrouter_api_key() -> str:
    """Read the OpenRouter API key from the CSV user store."""

    key_from_store: Optional[str] = None

    if USER_SETTINGS_PATH.exists():
        try:
            with USER_SETTINGS_PATH.open("r", newline="", encoding="utf-8") as fp:
                reader = csv.DictReader(fp)
                first_row = next(reader, None)
                if first_row:
                    key_from_store = (first_row.get("openrouter_api_key", "") or "").strip()
        except Exception:
            key_from_store = None

    if key_from_store:
        return key_from_store

    raise RuntimeError(
        "OpenRouter API key is not configured in data/user_db/user_settings.csv."
    )


def _build_headers() -> dict:
    """Construct the authorization headers using the latest API key."""

    api_key = _get_openrouter_api_key()
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


MODEL = "google/gemini-2.5-pro"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# ======= PROMPT =======
system_instructions = """
You are a query planner for a student + course management database.
Your job is to extract structured information AND determine which
table(s) and which columns must be queried to answer the request.

DATABASE SCHEMA DEFINITIONS:

users
columns in this table: id,name,short_name,primary_email,login_id,time_zone

courses
columns in this table: id,name,course_code,calendar_ics

course_content_summary
columns in this table: canvas_id,course_name,type,title,date,link,is_completed,grade,summary,text_id

grades 
columns in this table: course_id,course_name,assignment_name,points_possible,submission_score,submission_grade


TABLE SELECTION GUIDELINES:

Student-related details
Examples: who the student is, their email, timezone, etc.

courses
Core course details
Examples: course name, course code, calendar info

course_content_summary
Everything that looks like course materials or tasks in a list format
Examples: assignments, announcements, completion status, linked resources, due dates

grades
Grade and scoring data
Examples: assignment scores, points possible, final grade in a course

OUTPUT RULE:
Provide ONLY a valid JSON object in this format:

{
    "student_name": string or null,
    "course_name": string or null,
    "content_type": string or null,
    "item_name": string or null,
    "filters": {},
    "table_to_query": "<users | courses | course_content_summary | course_content | chat_sessions | chat_messages>",
    "required_columns": ["<column>", "..."]
}

NEVER explain your reasoning.
NEVER include SQL.
Output JSON only.
"""

# ======= HELPERS =======
def _extract_json_text(raw_text: str) -> str:
    """Clean model output: remove code fences, quotes, extract first {...}"""
    if raw_text is None:
        raise ValueError("No text to parse")

    text = raw_text.strip()
    # Remove markdown code fences
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    # Remove surrounding quotes
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    # Extract first {...} block
    first = text.find('{')
    last = text.rfind('}')
    if first != -1 and last != -1 and last > first:
        text = text[first:last+1]
    return text

def _parse_to_dict(json_like: str):
    """Try parsing cleaned JSON-like string to Python dict"""
    try:
        parsed = json.loads(json_like)
        if isinstance(parsed, dict):
            return parsed
        return parsed
    except Exception:
        pass
    try:
        parsed = ast.literal_eval(json_like)
        if isinstance(parsed, (dict, list)):
            return parsed
    except Exception:
        pass
    try:
        fixed = json_like.replace("'", '"')
        parsed = json.loads(fixed)
        return parsed
    except Exception:
        pass
    raise ValueError("Failed to parse text as JSON or Python literal")

# ======= MAIN FUNCTION =======
def query_to_structured(user_query: str):
    try:
        headers = _build_headers()
    except RuntimeError as exc:
        return {"error": str(exc)}

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0
    }

    resp = requests.post(ENDPOINT, headers=headers, json=data)

    if resp.status_code != 200:
        return {"error": f"API Error {resp.status_code}: {resp.text}"}

    content = resp.json()
    try:
        raw_reply = content["choices"][0]["message"]["content"]
    except Exception:
        raw_reply = content.get("response") or str(content)

    try:
        cleaned = _extract_json_text(raw_reply)
        parsed = _parse_to_dict(cleaned)
        return parsed
    except Exception as e:
        return {
            "error": "Failed to parse model output as JSON",
            "exception": str(e),
            "raw_reply": raw_reply,
            "cleaned_attempt": cleaned if 'cleaned' in locals() else None
        }


def generate_user_response_from_file(user_query: str, file_path: str):
    """
    Takes a user's query and a text file with relevant information,
    and generates a natural language response using the Gemini/OpenRouter API.

    Parameters:
        user_query (str): The user's original query.
        file_path (str): Path to a .txt file containing the relevant info.

    Returns:
        str: The response text for the user.
    """
    # Read the file content
    relevant_info_text = file_path

    try:
        headers = _build_headers()
    except RuntimeError as exc:
        return f"Configuration error: {exc}"

    # System instructions for the model
    system_prompt = """
You are an intelligent and friendly academic assistant that helps users explore their course and grade data.
Use the provided information to generate helpful, concise, and natural responses.

- You may infer or summarize key insights as long as they are grounded in the provided data.
- If the data does not explicitly contain an answer, offer an educated summary or note patterns instead of saying you don’t know.
- Keep your tone natural and clear.
"""

    user_content = f"""
User Query: {user_query}

Relevant Information (from file):
{relevant_info_text}
"""

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.7
    }

    resp = requests.post(ENDPOINT, headers=headers, json=data)

    if resp.status_code != 200:
        return f"API Error {resp.status_code}: {resp.text}"

    try:
        reply = resp.json()["choices"][0]["message"]["content"]
    except Exception:
        reply = resp.json().get("response") or str(resp.json())

    return reply


if __name__ == "__main__":
    user_input = input("Enter your query: ")
    result = query_to_structured(user_input)
    print("\nStructured Query Output:\n", json.dumps(result, indent=4))
    
    response = generate_user_response_from_file(user_input, "/Users/rohiinhavre/CanvAI/message (5).txt")
    print("\nModel Response:\n", response)
