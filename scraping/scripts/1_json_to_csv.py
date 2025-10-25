#!/usr/bin/env python3
"""
Convert courses in data.json into CSV files:
 - data/courses.csv : one row per course, nested objects JSON-encoded or flattened (calendar.ics -> calendar_ics)
 - data/enrollments.csv : one row per enrollment with course_id FK

Usage: run from project root: python scripts/json_to_csv.py
"""
import os
import json
import csv


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def flatten_course(course):
    """Return a flat dict suitable for CSV writing. Nested dicts/lists are JSON-encoded except calendar.ics."""
    out = {}
    for k, v in course.items():
        if k == "enrollments":
            # handled separately
            continue
        if isinstance(v, (str, int, float)) or v is None or isinstance(v, bool):
            out[k] = v
        elif isinstance(v, dict):
            # special-case calendar.ics
            if k == "calendar" and isinstance(v, dict) and "ics" in v:
                out["calendar_ics"] = v.get("ics")
            else:
                out[k] = json.dumps(v, ensure_ascii=False)
        else:
            # lists, etc.
            out[k] = json.dumps(v, ensure_ascii=False)
    return out


def collect_fieldnames(dicts):
    fields = set()
    for d in dicts:
        fields.update(d.keys())
    # keep a stable order: common Canvas fields first if present
    preferred = [
        "id",
        "name",
        "course_code",
        "uuid",
        "account_id",
        "enrollment_term_id",
        "start_at",
        "end_at",
        "created_at",
        "workflow_state",
        "is_public",
        "calendar_ics",
    ]
    ordered = [f for f in preferred if f in fields]
    remaining = sorted(fields - set(ordered))
    return ordered + remaining


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            # ensure all keys exist
            clean = {k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames}
            writer.writerow(clean)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(root, "data.json")
    out_dir = os.path.join(root, "data")
    ensure_dir(out_dir)

    data = load_json(data_path)
    courses_rows = []
    enrollments_rows = []

    for item in data:
        flat = flatten_course(item)
        courses_rows.append(flat)
        enrolls = item.get("enrollments")
        if isinstance(enrolls, list):
            for e in enrolls:
                e_row = dict(e)
                # attach course id for FK
                e_row["course_id"] = item.get("id")
                enrollments_rows.append(e_row)

    # Write courses.csv
    courses_fields = collect_fieldnames(courses_rows)
    courses_path = os.path.join(out_dir, "courses.csv")
    write_csv(courses_path, courses_fields, courses_rows)

    # Write enrollments.csv if any
    enrollments_path = os.path.join(out_dir, "enrollments.csv")
    if enrollments_rows:
        enroll_fields = collect_fieldnames(enrollments_rows)
        write_csv(enrollments_path, enroll_fields, enrollments_rows)

    print(f"Wrote {courses_path} ({len(courses_rows)} rows)")
    if enrollments_rows:
        print(f"Wrote {enrollments_path} ({len(enrollments_rows)} rows)")
    else:
        print("No enrollments found to write.")


if __name__ == "__main__":
    main()
