https://developerdocs.instructure.com/services/canvas

## Install dependencies

```bash
pip install -r requirements.txt
```

## Download user data

Get initial user data for yourself as csv.
```bash
python "scripts/export_canvas_users.py" --user-ids-file users_self.txt --out-csv data/canvas_user_self.csv --live
```

Get your own grades as csv.
```bash
python "scripts/get_user_grades.py" --user-id self --out-csv data/user_grades_self.csv --live
```

## Download course data

Get basic course data for all your courses as csv.
```bash
python "scripts/get_courses.py"
python "scripts/json_to_csv.py"
```

Get all resources for each course as csv (files, assignments, discussions, pages, quizzes).
```bash
python "scripts/export_via_http.py"
```

Download any files from each course listed in the files csv.
```bash
python "scripts/download_from_files_csv.py"
```

Extract text from downloaded files.
```bash
python "scripts/extract_text_from_downloads.py"
python "scripts/extract_text_from_videos.py"
```

Generate summaries using Gemini API (slow).
```bash
python "scripts/generate_summaries_gemini.py" --input-root extracted_text --out-csv extracted_text/summaries.csv --sleep 0.5 --max-chars 300
```
