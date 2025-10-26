#!/usr/bin/env python3
"""
Export course resources by calling Canvas REST API directly (HTTP) and writing per-course CSVs.

Resources exported per course:
 - assignments (/courses/{id}/assignments)
 - modules (/courses/{id}/modules) and module items (/courses/{id}/modules/{module_id}/items)
 - pages (/courses/{id}/pages)
 - files (/courses/{id}/files)
 - quizzes (/courses/{id}/quizzes)
 - discussion_topics (/courses/{id}/discussion_topics)

The script reads `data/courses.json` for a list of courses. It requires an API key in env var
`CANVAS_KEY` or in a `.env` file in the project root.

Usage:
    python scripts/export_via_http.py

Output: CSV files under `data/` named like
    assignments_<courseid>_<slug>.csv
    modules_<courseid>_<slug>.csv
    module_items_<courseid>_<slug>.csv
    pages_<courseid>_<slug>.csv
    files_<courseid>_<slug>.csv
    quizzes_<courseid>_<slug>.csv
    discussions_<courseid>_<slug>.csv

Pagination: uses the Link header 'next' rel returned by Canvas via requests' response.links
"""

import os
import json
import csv
import re
import sys
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv


CANVAS_BASE = "https://canvas.instructure.com/api/v1"


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


def json_friendly(v):
    try:
        return json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        return str(v)


def flatten(item):
    out = {}
    if not isinstance(item, dict):
        return {"value": json_friendly(item)}
    for k, v in item.items():
        if isinstance(v, (str, int, float)) or v is None or isinstance(v, bool):
            out[k] = v
        else:
            out[k] = json_friendly(v)
    return out


def collect_fieldnames(rows):
    fields = set()
    for r in rows:
        fields.update(r.keys())
    preferred = ["id", "name", "title", "body", "due_at", "created_at", "updated_at", "html_url"]
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


class CanvasHTTP:
    def __init__(self, base, token):
        self.base = base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.token = token
        # default: don't force query param; caller can set True to force access_token query param
        self.use_query_token = False

    def _get_all(self, url, params=None):
        items = []
        cur = url
        while cur:
            # If using query-token mode, include access_token param on each request
            req_params = dict(params or {})
            if self.use_query_token:
                req_params.update({"access_token": self.token})

            resp = self.session.get(cur, params=req_params)
            # if response empty or not JSON, try fallback using access_token query param
            if (not resp.text or not resp.text.strip()):
                # retry with access_token query param (some Canvas installs accept this)
                resp = requests.get(cur, params=(req_params or {}) | {"access_token": self.token})

            if resp.status_code >= 400:
                # include a short excerpt for debugging
                body = resp.text[:1000]
                raise RuntimeError(f"HTTP {resp.status_code}: {body}")

            try:
                data = resp.json()
            except ValueError:
                # non-JSON response; surface debugging info and stop
                raise RuntimeError(f"Non-JSON response for {cur}: status={resp.status_code}, text={resp.text[:1000]}")
            if isinstance(data, list):
                items.extend(data)
            elif isinstance(data, dict):
                # some endpoints return a dict with 'modules' or similar
                items.extend(data.get("modules") or data.get("items") or [])
            else:
                # unexpected
                pass
            # pagination: requests populates resp.links
            nxt = resp.links.get("next", {}).get("url")
            cur = nxt
            params = None
        return items

    def get_course_resource(self, course_id, path):
        # Build the API path without a leading slash so we keep the base (which already contains /api/v1)
        url = f"{self.base}/courses/{course_id}/{path}"
        return self._get_all(url)


def export_for_course(api, course, out_dir):
    course_id = course.get("id")
    course_name = course.get("name") or f"course_{course_id}"
    slug = slugify(course_name)
    created = []

    resources = [
        ("assignments", "assignments"),
        ("modules", "modules"),
        ("pages", "pages"),
        ("files", "files"),
        ("quizzes", "quizzes"),
        ("discussion_topics", "discussion_topics"),
    ]

    for res_name, endpoint in resources:
        try:
            items = api.get_course_resource(course_id, endpoint)
        except Exception as e:
            print(f"Failed to fetch {endpoint} for course {course_id}: {e}")
            continue

        if not items:
            # no items
            # special-case: modules may exist but modules endpoint may return module objects; we'll still write modules file
            print(f"No {res_name} for course {course_id} ({course_name}); skipping.")
            continue

        rows = [flatten(i) for i in items]
        fieldnames = collect_fieldnames(rows)
        fname = f"{res_name}_{course_id}_{slug}.csv"
        path = os.path.join(out_dir, fname)
        write_csv(path, fieldnames, rows)
        created.append(path)

        # For modules, also fetch module items per module
        if res_name == "modules":
            all_module_items = []
            for m in items:
                mid = m.get("id")
                if not mid:
                    continue
                try:
                    mod_items = api.get_course_resource(course_id, f"modules/{mid}/items")
                except Exception as e:
                    print(f"Failed to fetch module items for module {mid} in course {course_id}: {e}")
                    mod_items = []
                for mi in mod_items:
                    # annotate module id/name
                    if isinstance(mi, dict):
                        mi.setdefault("module_id", mid)
                        mi.setdefault("module_name", m.get("name"))
                all_module_items.extend(mod_items)

            if all_module_items:
                rows = [flatten(i) for i in all_module_items]
                fieldnames = collect_fieldnames(rows)
                fname = f"module_items_{course_id}_{slug}.csv"
                path = os.path.join(out_dir, fname)
                write_csv(path, fieldnames, rows)
                created.append(path)

    return created


def main():
    load_dotenv()
    token = os.getenv("CANVAS_KEY") or os.getenv("ACCESS_TOKEN")
    if not token:
        print("CANVAS_KEY or ACCESS_TOKEN not set in environment or .env. Set one and re-run.")
        sys.exit(1)

    # If ACCESS_TOKEN env var was provided or user explicitly requests it, use query param auth
    use_query = False
    if os.getenv("ACCESS_TOKEN"):
        use_query = True
    # allow forcing via CANVAS_USE_QUERY_TOKEN=1
    if os.getenv("CANVAS_USE_QUERY_TOKEN", "0") in ("1", "true", "TRUE", "yes"):
        use_query = True

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_path = os.path.join(root, "data/courses.json")
    if not os.path.exists(data_path):
        print("data/courses.json not found in project root.")
        sys.exit(1)

    out_dir = os.path.join(root, "data")
    ensure_dir(out_dir)

    courses = load_json(data_path)

    api = CanvasHTTP(CANVAS_BASE, token)
    api.use_query_token = use_query

    created_files = []
    for course in courses:
        cid = course.get("id")
        if cid is None:
            continue
        print(f"Exporting resources for course {cid} - {course.get('name')}")
        try:
            created = export_for_course(api, course, out_dir)
            created_files.extend(created)
        except Exception as e:
            print(f"Error exporting course {cid}: {e}")

    if created_files:
        print("Created files:")
        for p in created_files:
            print(" - ", p)
    else:
        print("No resource CSVs created.")


if __name__ == "__main__":
    main()
