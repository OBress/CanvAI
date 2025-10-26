#!/usr/bin/env python3
"""
Generate ~300-character dense summaries for each extracted text file using Gemini (Google GenAI).

Behavior:
- Walks `extracted_text/` for .txt files (produced by the extractor).
- For each file, calls the Gemini model via the `google.genai` client to request a concise ~300-character summary.
- Writes a sidecar `<original>.summary.txt` containing the model output.
- Appends/updates a CSV manifest at `extracted_text/summaries.csv` with source, summary_path, chars, status, notes.

Notes:
- This script will not attempt to install the GenAI client. If you see ImportError, run:
    pip install google-genai
- Authentication: the GenAI client typically reads credentials from env vars (e.g., `GOOGLE_API_KEY` or other
  Google auth mechanisms). The script does not embed keys; set them in your environment before running.
"""

from __future__ import annotations
import os
import csv
import time
import argparse
from pathlib import Path
from typing import Optional

try:
    from google import genai
except Exception:  # ImportError or similar
    genai = None

# Load .env early so GEMINI_KEY (if present) is available to set env vars used by the client
import load_user_settings

GEMINI_KEY = os.getenv("GEMINI_KEY")
if GEMINI_KEY:
    # Many GenAI clients accept GOOGLE_API_KEY or custom vars; set a couple of env vars
    os.environ.setdefault("GOOGLE_API_KEY", GEMINI_KEY)
    os.environ.setdefault("GENAI_API_KEY", GEMINI_KEY)



def summarize_with_gemini(client, text: str, target_chars: int = 300) -> str:
    # Keep prompt short and explicit
    prompt = (
        f"Create a single-paragraph, dense summary of the following content in about {target_chars} characters. "
        "Keep it factual, concise, and avoid bullet points or headings. If the content is short, summarize it directly.\n\n"
        f"Content:\n{text}"
    )

    # Use the same call shape as your sample; responses normally have `.text`.
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return getattr(resp, "text", str(resp)).strip()


def load_existing_manifest(manifest_path: Path) -> set:
    seen = set()
    if not manifest_path.exists():
        return seen
    try:
        with manifest_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for r in reader:
                seen.add(r.get("source", ""))
    except Exception:
        # If manifest can't be read, ignore and rewrite later
        pass
    return seen


def append_manifest_row(manifest_path: Path, row: dict):
    write_header = not manifest_path.exists()
    with manifest_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["source", "summary_path", "ext", "chars", "status", "notes"])
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main():
    p = argparse.ArgumentParser(description="Generate Gemini summaries for extracted text files")
    p.add_argument("--input-root", default="extracted_text", help="Root folder with extracted text files")
    p.add_argument("--out-csv", default="extracted_text/summaries.csv", help="CSV manifest path to append summaries")
    p.add_argument("--sleep", type=float, default=0.25, help="Seconds to sleep between API calls (rate limiting)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing sidecar summaries and manifest entries")
    p.add_argument("--max-chars", type=int, default=300, help="Target summary length in characters (approx)")
    p.add_argument("--dry-run", action="store_true", help="Do not call the API; just report files that would be processed")
    args = p.parse_args()

    input_root = Path(args.input_root)
    manifest_path = Path(args.out_csv)

    if not input_root.exists():
        print(f"Input root not found: {input_root}")
        return

    if genai is None and not args.dry_run:
        print("ERROR: Google GenAI client (`google.genai`) not installed or failed to import.")
        print("Install via: pip install google-genai")
        return

    client = None
    if not args.dry_run:
        # instantiate client
        try:
            # If GEMINI_KEY was provided in .env, try to pass it directly if the client supports it.
            if GEMINI_KEY:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                except TypeError:
                    # client may not accept api_key kwarg; fall back to default
                    client = genai.Client()
            else:
                client = genai.Client()
        except Exception as exc:
            print("ERROR: Failed to create genai.Client():", exc)
            return

    seen = set()
    if not args.overwrite:
        seen = load_existing_manifest(manifest_path)

    total = 0
    ok = 0
    failed = 0

    for root, _dirs, files in os.walk(input_root):
        for fn in files:
            if not fn.lower().endswith('.txt'):
                continue
            total += 1
            src = Path(root) / fn
            rel = str(src.relative_to(input_root))

            if not args.overwrite and str(src) in seen:
                print(f"SKIP (manifest): {src}")
                continue

            # Skip files that are already sidecar summaries
            if src.name.endswith('.summary.txt'):
                continue

            try:
                with src.open('r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
            except Exception as exc:
                print(f"SKIP/FAIL: {src} -> read error: {exc}")
                failed += 1
                append_manifest_row(manifest_path, {"source": str(src), "summary_path": "", "ext": src.suffix, "chars": 0, "status": "read-error", "notes": str(exc)})
                continue

            if args.dry_run:
                print(f"DRY: would summarize {src} (len={len(content)} chars)")
                continue

            # Optionally truncate long content to keep token usage reasonable
            max_input_chars = 100_000
            if len(content) > max_input_chars:
                content = content[:max_input_chars]

            try:
                summary_text = summarize_with_gemini(client, content, target_chars=args.max_chars)
            except Exception as exc:
                print(f"SKIP/FAIL: {src} -> API error: {exc}")
                failed += 1
                append_manifest_row(manifest_path, {"source": str(src), "summary_path": "", "ext": src.suffix, "chars": 0, "status": "api-error", "notes": str(exc)})
                # small backoff
                time.sleep(max(0.5, args.sleep))
                continue

            # Save sidecar summary
            summary_path = src.with_name(src.name + ".summary.txt")
            try:
                summary_path.parent.mkdir(parents=True, exist_ok=True)
                with summary_path.open('w', encoding='utf-8') as fh:
                    fh.write(summary_text)
            except Exception as exc:
                print(f"ERROR writing summary for {src}: {exc}")
                failed += 1
                append_manifest_row(manifest_path, {"source": str(src), "summary_path": str(summary_path), "ext": src.suffix, "chars": 0, "status": "write-error", "notes": str(exc)})
                continue

            chars = len(summary_text)
            append_manifest_row(manifest_path, {"source": str(src), "summary_path": str(summary_path), "ext": src.suffix, "chars": chars, "status": "ok", "notes": ""})
            print(f"OK: {summary_path}")
            ok += 1
            time.sleep(args.sleep)

    print(f"Done. total={total} ok={ok} failed={failed}")


if __name__ == '__main__':
    main()
