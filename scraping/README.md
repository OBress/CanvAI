https://developerdocs.instructure.com/services/canvas

# install dependencies

```bash
pip install -r requirements.txt
```

# Pipeline

```bash
bash scripts/0_get_data.sh
python "scripts/1_json_to_csv.py"
python "scripts/2_export_assignments_per_course.py"
python "scripts/3_export_via_http.py"
python "scripts/4_download_from_files_csv.py"
python "scripts/5_extract_text_from_downloads.py"
python "scripts/6_generate_summaries_gemini.py" --input-root extracted_text --out-csv extracted_text/summaries.csv --sleep 0.5 --max-chars 300
python "scripts/7_export_canvas_users.py" --user-ids-file users_self.txt --out-csv canvas_user_self.csv --live
python "scripts/8_get_user_grades.py" --user-id self --out-csv data/user_grades_self.csv --live 
```
