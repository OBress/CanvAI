
# Load environment variables from csv
import load_user_settings
import os
import requests

CANVAS_BASE_URL = os.getenv("CANVAS_BASE_URL")
CANVAS_KEY = os.getenv("CANVAS_KEY")
URL = f"{CANVAS_BASE_URL}/api/v1/courses?access_token={CANVAS_KEY}"

def main():
    response = requests.get(URL)
    if response.status_code == 200:
        with open("data/courses.json", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Courses data saved to data/courses.json")
    else:
        print(f"Failed to retrieve courses data. Status code: {response.status_code}")


if __name__ == "__main__":
    main()
