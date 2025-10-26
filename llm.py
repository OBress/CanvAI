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

import requests
import json
import re
import ast

# ======= CONFIGURATION =======
API_KEY = "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"  # replace with your Gemini/OpenRouter API key
MODEL = "google/gemini-2.5-pro"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# ======= PROMPT =======
system_instructions = """
You are a query planner for a student + course management database.
Your job is to extract structured information AND determine which
table(s) and which columns must be queried to answer the request.

DATABASE SCHEMA DEFINITIONS:

users
- ID
- NAME
- SCHOOL
- GPA
- CREDITS
- MAJOR
- GOALS
- GRAD_DATE

courses
- ID
- CANVAS_ID
- NAME
- SECTION
- GRADE
- PROFESSOR
- TAs

course_content_summary
- ID
- CANVAS_CONTENT_ID
- CANVAS_COURSE_ID
- TYPE (assignment, lecture, syllabus, email, announcement)
- TITLE
- DATE
- LINK
- IS_COMPLETED
- GRADE
- SUMMARY

course_content
- ID
- CANVAS_CONTENT_ID
- FULL_TEXT

chat_sessions
- ID
- USER_ID
- TITLE
- CREATED_AT

chat_messages
- ID
- SESSION_ID
- SENDER
- MESSAGE
- TIMESTAMP


TABLE SELECTION GUIDELINES:

users
Student details (GPA, major, name, goals, credits, graduation)

courses
Course details or course grade (class list, professor, section, final grade)

course_content_summary
Assignments, announcements, syllabus metadata, lecture listings,
completion status, assignment grades

course_content
Requests to read/show/view full text content for assignments,
announcements, syllabus, emails, lectures

chat_sessions or chat_messages
Messaging history, titles, timestamps, text queries


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
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

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

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # System instructions for the model
    system_prompt = """
You are a helpful academic assistant. You have access to information from a student + course
management system. Use the relevant data provided to answer the user's question in natural, friendly,
and concise language. Do not invent any information. If the data does not contain the answer, politely say so.
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