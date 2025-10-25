#!/usr/bin/env python3
"""
Export assignments per course into CSV files.

Behavior:
 - Reads `data.json` for course list.
 - If `data_assignments.json` exists in project root, it will use that to get assignments per course.
   Expected format: {"<course_id>": [<assignment dicts>], ...}
 - Otherwise, if environment variable `CANVAS_KEY` is set, it will use the Canvas API
   (https://canvas.instructure.com) to fetch assignments for each course id in `data.json`.
 - Writes CSV files to `data/assignments_<course_id>_<slugified_name>.csv`.

Usage:
  python scripts/export_assignments_per_course.py

"""
import os
import json
import csv
from dotenv import load_dotenv
import re
import sys


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")[:80]


def flatten(item):
    out = {}
    for k, v in item.items():
        if isinstance(v, (str, int, float)) or v is None or isinstance(v, bool):
            out[k] = v
        elif isinstance(v, dict):
            try:
                out[k] = json.dumps(v, ensure_ascii=False, default=str)
            except Exception:
                out[k] = str(v)
        else:
            try:
                out[k] = json.dumps(v, ensure_ascii=False, default=str)
            except Exception:
                out[k] = str(v)
    return out


def collect_fieldnames(rows):
    fields = set()
    for r in rows:
        fields.update(r.keys())
    # keep common fields first
    preferred = ["id", "name", "description", "due_at", "lock_at", "created_at", "points_possible", "submission_types", "workflow_state", "html_url"]
    ordered = [f for f in preferred if f in fields]
    remaining = sorted(fields - set(ordered))
    return ordered + remaining


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            clean = {k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames}
            writer.writerow(clean)


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_path = os.path.join(root, "data.json")
    assignments_json_path = os.path.join(root, "data_assignments.json")
    out_dir = os.path.join(root, "data")
    ensure_dir(out_dir)

    # load .env if present so CANVAS_KEY can be read from it
    try:
        load_dotenv()
    except Exception:
        pass
    if not os.path.exists(data_path):
        print("Could not find data.json in project root.")
        sys.exit(1)

    courses = load_json(data_path)

    # load local assignments mapping if present
    local_assignments = None
    if os.path.exists(assignments_json_path):
        try:
            local_assignments = load_json(assignments_json_path)
            print(f"Loaded local assignments from {assignments_json_path}")
        except Exception as e:
            print(f"Failed to load {assignments_json_path}: {e}")
            local_assignments = None

    use_canvas = False
    canvas_key = os.getenv("CANVAS_KEY")
    if local_assignments is None and canvas_key:
        # try to import canvasapi lazily
        try:
            from canvasapi import Canvas

            use_canvas = True
            API_URL = "https://canvas.instructure.com"
            canvas = Canvas(API_URL, canvas_key)
            print("Canvas API available via CANVAS_KEY; will fetch assignments from Canvas.")
        except Exception as e:
            print(f"canvasapi import or Canvas init failed: {e}")
            use_canvas = False

    if local_assignments is None and not use_canvas:
        print("No local assignments file found and CANVAS_KEY not available or failed.\n"
              "Create `data_assignments.json` mapping course_id -> [assignments] or set CANVAS_KEY in the environment.")
        sys.exit(1)

    created = []

    for course in courses:
        course_id = course.get("id")
        course_name = course.get("name") or "course"
        if course_id is None:
            # skip entries without id
            continue

        # get assignments list
        assignments = None
        if local_assignments and str(course_id) in local_assignments:
            assignments = local_assignments[str(course_id)]
        elif local_assignments and course_id in local_assignments:
            assignments = local_assignments[course_id]
        elif use_canvas:
            try:
                c = canvas.get_course(course_id)
                assignments = []
                for a in c.get_assignments():
                    # prefer raw data if available
                    raw = getattr(a, "_data", None) or getattr(a, "__dict__", None)
                    if isinstance(raw, dict):
                        assignments.append(raw)
                    else:
                        # fallback: try to build a small dict
                        assignments.append({
                            "id": getattr(a, "id", None),
                            "name": getattr(a, "name", None),
                            "due_at": getattr(a, "due_at", None),
                            "points_possible": getattr(a, "points_possible", None),
                        })
            except Exception as e:
                print(f"Failed to fetch assignments for course {course_id}: {e}")
                assignments = []

        if not assignments:
            print(f"No assignments for course {course_id} ({course_name}); skipping CSV.")
            continue

        rows = [flatten(a) for a in assignments]
        fieldnames = collect_fieldnames(rows)
        fname = f"assignments_{course_id}_{slugify(course_name)}.csv"
        path = os.path.join(out_dir, fname)
        write_csv(path, fieldnames, rows)
        created.append(path)
        print(f"Wrote {path} ({len(rows)} assignments)")

    if not created:
        print("No assignment CSVs created.")
    else:
        print("Created assignment CSVs:")
        for p in created:
            print(" - ", p)


if __name__ == "__main__":
    main()
