import requests
import json

# ======= CONFIGURATION =======
API_KEY = "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"  # Replace with the key your friend gave you
MODEL = "google/gemini-2.5-pro"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

def query_to_structured(user_query):
    prompt = f"""
    Convert this user query into a structured JSON query:
    User query: "{user_query}"
    Output format:
    {{
        "student_name": "<student_name>"
        "course": "<course_type>",
        "assignment": "<assignment_name>",
        "announcement": {{ "<filter_key>": "<filter_value>" }},
        "syllabus": <file>
    }}
    """
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }
    
    response = requests.post(ENDPOINT, headers=headers, json=data)
    
    if response.status_code == 200:
        content = response.json()
        return content["choices"][0]["message"]["content"]
    else:
        return f"API Error {response.status_code}: {response.text}"

if __name__ == "__main__":
    user_input = input("Enter your query: ")
    result = query_to_structured(user_input)
    print("\nStructured Query Output:\n", result)