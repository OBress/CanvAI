#!/usr/bin/env python3
"""
Export Canvas user profile information to CSV.

Usage patterns:
  - Export users in a course:
      python scripts/export_canvas_users.py --course-id 12345 --out-csv canvas_users.csv

  - Export users in an account (all users):
      python scripts/export_canvas_users.py --account-id 1 --out-csv canvas_users.csv

  - Export specific user ids listed in a file (one id per line):
      python scripts/export_canvas_users.py --user-ids-file users.txt --out-csv canvas_users.csv

Notes:
- Authentication: set `CANVAS_BASE_URL` and either `CANVAS_KEY` (Bearer) or `ACCESS_TOKEN` env vars.
- By default the script runs in dry-run mode; add `--live` to perform HTTP requests and write the CSV.
- Canvas does not expose 'GPA' by default; the script will include common profile fields and any SIS/custom fields
  if present. You can extend it to read grades per user and compute GPA externally.
"""

from __future__ import annotations
import os
import csv
import time
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

# Load environment variables from csv
import load_user_settings


def get_auth(headers: Dict[str, str], params: Dict[str, str]):
    # Read env vars set in other scripts
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
            # sometimes Canvas returns an object for single item; make it a list
            page_items = [page_items]
        results.extend(page_items)
        # check pagination via Link header
        links = r.links
        if links and links.get("next"):
            url = links["next"]["url"]
            params = {}
            time.sleep(0.1)
            continue
        break
    return results


def fetch_users_from_course(session: requests.Session, base_url: str, course_id: str, headers: Dict[str, str], params: Dict[str, str]) -> List[Dict[str, Any]]:
    url = f"{base_url}/api/v1/courses/{course_id}/users"
    # include enrollments and email where available
    params = dict(params or {})
    # limit roles to students/instructors? Leave open
    params.setdefault("include[]", "enrollments")
    return _get_all(session, url, headers, params)


def fetch_users_from_account(session: requests.Session, base_url: str, account_id: str, headers: Dict[str, str], params: Dict[str, str]) -> List[Dict[str, Any]]:
    url = f"{base_url}/api/v1/accounts/{account_id}/users"
    params = dict(params or {})
    return _get_all(session, url, headers, params)


def fetch_user_profile(session: requests.Session, base_url: str, user_id: str, headers: Dict[str, str], params: Dict[str, str]) -> Dict[str, Any]:
    # Prefer the profile endpoint for rich info
    url = f"{base_url}/api/v1/users/{user_id}/profile"
    r = session.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def normalize_user(u: Dict[str, Any]) -> Dict[str, Any]:
    # Map Canvas user JSON to flat CSV row. Keep unrecognized fields in a 'raw' column.
    row: Dict[str, Any] = {}
    row["id"] = u.get("id")
    row["name"] = u.get("name") or u.get("display_name")
    row["sortable_name"] = u.get("sortable_name")
    row["short_name"] = u.get("short_name")
    row["primary_email"] = u.get("primary_email") or u.get("email")
    row["login_id"] = u.get("login_id")
    row["sis_user_id"] = u.get("sis_user_id")
    row["avatar_url"] = u.get("avatar_url")
    row["html_url"] = u.get("html_url")
    row["title"] = u.get("title")
    row["bio"] = u.get("bio")
    row["locale"] = u.get("locale")
    row["time_zone"] = u.get("time_zone")
    row["created_at"] = u.get("created_at")
    # Enrollments is often a list; write JSON string
    enrollments = u.get("enrollments") or []
    try:
        row["enrollments"] = json.dumps(enrollments, ensure_ascii=False)
    except Exception:
        row["enrollments"] = str(enrollments)

    # Canvas typically doesn't expose GPA; attempt to read custom_data or other keys
    row["school"] = u.get("custom_data", {}).get("school") if isinstance(u.get("custom_data"), dict) else ""
    row["gpa"] = u.get("custom_data", {}).get("gpa") if isinstance(u.get("custom_data"), dict) else ""

    # Keep the raw JSON for debugging
    row["raw"] = json.dumps(u, ensure_ascii=False)
    return row


def write_csv(rows: List[Dict[str, Any]], out_path: Path):
    if not rows:
        print("No rows to write")
        return
    fieldnames = [
        "id",
        "name",
        "sortable_name",
        "short_name",
        "primary_email",
        "login_id",
        "sis_user_id",
        "avatar_url",
        "html_url",
        "title",
        "bio",
        "locale",
        "time_zone",
        "created_at",
        "enrollments",
        "school",
        "gpa",
        "raw",
    ]
    # Ensure destination directory exists
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    p = argparse.ArgumentParser(description="Export Canvas user profile info to CSV")
    p.add_argument("--course-id", help="Fetch users enrolled in this course")
    p.add_argument("--account-id", help="Fetch users in this account")
    p.add_argument("--user-ids-file", help="Path to a file with user ids (one per line)")
    p.add_argument("--out-csv", default="data/canvas_users.csv", help="Output CSV path (defaults to data/)")
    p.add_argument("--live", action="store_true", help="Perform live API calls (dry-run by default)")
    p.add_argument("--sleep", type=float, default=0.1, help="Sleep between per-user profile calls")
    args = p.parse_args()

    base_url = os.getenv("CANVAS_BASE_URL")
    if not base_url:
        print("ERROR: set CANVAS_BASE_URL environment variable to your Canvas base URL (e.g. https://canvas.example.edu)")
        return

    headers = {"Accept": "application/json"}
    params: Dict[str, str] = {}
    headers, params = get_auth(headers, params)

    session = requests.Session()

    users: List[Dict[str, Any]] = []

    # Resolve output path (if a plain filename is provided it will be placed under data by default via the argparse default)
    resolved_out = Path(args.out_csv)
    print("Output CSV:", resolved_out)

    if args.course_id:
        print("Fetching users from course", args.course_id)
        if args.live:
            try:
                users = fetch_users_from_course(session, base_url.rstrip('/'), args.course_id, headers, params)
            except Exception as exc:
                print("Error fetching users from course:", exc)
                return
        else:
            print("Dry-run: would fetch users from course", args.course_id)
            return

    elif args.account_id:
        print("Fetching users from account", args.account_id)
        if args.live:
            try:
                users = fetch_users_from_account(session, base_url.rstrip('/'), args.account_id, headers, params)
            except Exception as exc:
                print("Error fetching users from account:", exc)
                return
        else:
            print("Dry-run: would fetch users from account", args.account_id)
            return

    elif args.user_ids_file:
        path = Path(args.user_ids_file)
        if not path.exists():
            print("User ids file not found:", path)
            return
        ids = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        print(f"Will fetch {len(ids)} users from ids file")
        if not args.live:
            print("Dry-run: would fetch profiles for", len(ids), "users")
            return
        rows = []
        for uid in ids:
            try:
                u = fetch_user_profile(session, base_url.rstrip('/'), uid, headers, params)
                rows.append(normalize_user(u))
            except Exception as exc:
                print(f"SKIP/FAIL: user {uid} -> {exc}")
            time.sleep(args.sleep)
        write_csv(rows, resolved_out)
        print(f"Wrote {len(rows)} rows to {resolved_out}")
        return

    else:
        print("Nothing to do: provide --course-id or --account-id or --user-ids-file")
        return

    # When we have `users` (returned from course/account list), some entries may be partial.
    # For each user, try to fetch profile for complete info.
    if args.live:
        out_rows: List[Dict[str, Any]] = []
        ids_seen = set()
        for u in users:
            uid = u.get("id") or u.get("user_id")
            if not uid or uid in ids_seen:
                continue
            ids_seen.add(uid)
            try:
                profile = fetch_user_profile(session, base_url.rstrip('/'), str(uid), headers, params)
                out_rows.append(normalize_user(profile))
            except Exception as exc:
                print(f"SKIP/FAIL: user {uid} -> {exc}")
            time.sleep(args.sleep)
        write_csv(out_rows, resolved_out)
        print(f"Wrote {len(out_rows)} rows to {resolved_out}")
    else:
        print("Dry-run: would fetch profiles for users returned by the course/account listing. Use --live to perform requests.")


if __name__ == '__main__':
    main()
