#!/usr/bin/env python3
"""
Fetch grades (assignment submissions) for a Canvas user and write to CSV.

Usage:
  # get grades for current token user across visible courses (live):
  python scripts/get_user_grades.py --user-id self --out-csv data/user_grades_self.csv --live

  # get grades for a specific course and user:
  python scripts/get_user_grades.py --course-id 98765 --user-id 123 --out-csv data/grades_course_98765_user_123.csv --live

Notes:
- Reads `CANVAS_BASE_URL` and `CANVAS_KEY` or `ACCESS_TOKEN` from environment (loads .env).
- By default runs in dry-run mode; add --live to perform network calls and write CSV.
"""

from __future__ import annotations
import os
import csv
import time
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

import requests

# Load environment variables from csv
import load_user_settings


def get_auth(headers: Dict[str, str], params: Dict[str, str]):
    key = os.getenv("CANVAS_KEY") or os.getenv("ACCESS_TOKEN")
    use_query = os.getenv("CANVAS_USE_QUERY_TOKEN", "").lower() in ("1", "true", "yes")
    if not key:
        return headers, params
    if use_query:
        params = dict(params)
        params["access_token"] = key
    else:
        headers = dict(headers)
        headers.setdefault("Authorization", f"Bearer {key}")
    return headers, params


def _get_all(session: requests.Session, url: str, headers: Dict[str, str], params: Dict[str, str]):
    results = []
    params = dict(params or {})
    params.setdefault("per_page", 100)
    while True:
        r = session.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        page_items = r.json()
        if isinstance(page_items, dict):
            page_items = [page_items]
        results.extend(page_items)
        links = r.links
        if links and links.get("next"):
            url = links["next"]["url"]
            params = {}
            time.sleep(0.1)
            continue
        break
    return results


def list_visible_courses(session: requests.Session, base_url: str, headers: Dict[str, str], params: Dict[str, str]):
    url = f"{base_url}/api/v1/courses"
    params = dict(params or {})
    params.setdefault("enrollment_state", "active")
    params.setdefault("per_page", 100)
    return _get_all(session, url, headers, params)


def list_assignments(session: requests.Session, base_url: str, course_id: str, headers: Dict[str, str], params: Dict[str, str]):
    url = f"{base_url}/api/v1/courses/{course_id}/assignments"
    return _get_all(session, url, headers, params)


def get_submission(session: requests.Session, base_url: str, course_id: str, assignment_id: str, user_id: str, headers: Dict[str, str], params: Dict[str, str]):
    # GET /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id
    url = f"{base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
    r = session.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def write_csv(rows: List[Dict[str, Any]], out_path: Path):
    if not rows:
        print("No grade rows to write")
        return
    fieldnames = [
        "course_id",
        "course_name",
        "assignment_id",
        "assignment_name",
        "points_possible",
        "submission_score",
        "submission_grade",
        "workflow_state",
        "submitted_at",
        "graded_at",
        "grader_id",
        "user_id",
        "user_name",
        "raw",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    p = argparse.ArgumentParser(description="Fetch Canvas grades (assignment submissions) for a user")
    p.add_argument("--user-id", default="self", help="User id or 'self' (default)")
    p.add_argument("--course-id", help="Limit to a specific course id")
    p.add_argument("--out-csv", default="data/user_grades_self.csv", help="Output CSV path")
    p.add_argument("--live", action="store_true", help="Perform live API calls")
    p.add_argument("--sleep", type=float, default=0.1, help="Sleep between calls")
    args = p.parse_args()

    base_url = os.getenv("CANVAS_BASE_URL")
    if not base_url:
        print("ERROR: set CANVAS_BASE_URL in environment or .env")
        return

    headers = {"Accept": "application/json"}
    params = {}
    headers, params = get_auth(headers, params)
    session = requests.Session()

    out_path = Path(args.out_csv)
    print("Resolved output:", out_path)

    if not args.live:
        print("Dry-run: would fetch grades for user", args.user_id, "(limit course=" + (args.course_id or "ALL") + ")")
        return

    courses = []
    if args.course_id:
        courses = [{"id": args.course_id}]
    else:
        print("Listing visible courses...")
        try:
            courses = list_visible_courses(session, base_url.rstrip('/'), headers, params)
        except Exception as exc:
            print("Error listing courses:", exc)
            return

    rows = []
    for c in courses:
        cid = str(c.get("id"))
        cname = c.get("name") or ""
        print(f"Processing course {cid} - {cname}")
        try:
            assignments = list_assignments(session, base_url.rstrip('/'), cid, headers, params)
        except Exception as exc:
            print(f"  Could not list assignments for course {cid}: {exc}")
            continue

        for a in assignments:
            aid = str(a.get("id"))
            aname = a.get("name")
            points = a.get("points_possible")
            try:
                sub = get_submission(session, base_url.rstrip('/'), cid, aid, args.user_id, headers, params)
            except requests.HTTPError as e:
                # If 404, submission might not exist; record as missing
                print(f"    Submission missing or error for assignment {aid}: {e}")
                continue
            except Exception as exc:
                print(f"    Error fetching submission for assignment {aid}: {exc}")
                continue

            # submission object may have 'submission' key or be the submission itself
            submission = sub.get("submission") if isinstance(sub, dict) and sub.get("submission") else sub

            row = {
                "course_id": cid,
                "course_name": cname,
                "assignment_id": aid,
                "assignment_name": aname,
                "points_possible": points,
                "submission_score": submission.get("score") if isinstance(submission, dict) else None,
                "submission_grade": submission.get("grade") if isinstance(submission, dict) else None,
                "workflow_state": submission.get("workflow_state") if isinstance(submission, dict) else None,
                "submitted_at": submission.get("submitted_at") if isinstance(submission, dict) else None,
                "graded_at": submission.get("graded_at") if isinstance(submission, dict) else None,
                "grader_id": submission.get("grader_id") if isinstance(submission, dict) else None,
                "user_id": args.user_id,
                "user_name": submission.get("user_id") if isinstance(submission, dict) else "",
                "raw": json.dumps(sub, ensure_ascii=False),
            }
            rows.append(row)
            time.sleep(args.sleep)

    write_csv(rows, out_path)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == '__main__':
    main()
