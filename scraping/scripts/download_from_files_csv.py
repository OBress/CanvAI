#!/usr/bin/env python3
"""
Download files listed in data/files_*.csv by reading the 'url' column.

Saves into files/<csv_basename>/ using 'filename' or 'display_name' columns when available.
Supports CANVAS_KEY or ACCESS_TOKEN in env/.env. Set CANVAS_USE_QUERY_TOKEN=1 to force access_token query param.
"""
import os
import csv
import sys
import time
from urllib.parse import urlparse, unquote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables from csv
import load_user_settings


def session_with_retries(token=None, use_query=False):
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=(500,502,503,504))
    s.mount('https://', HTTPAdapter(max_retries=retries))
    s.mount('http://', HTTPAdapter(max_retries=retries))
    if token and not use_query:
        s.headers.update({'Authorization': f'Bearer {token}'})
    return s


def get_fname(row):
    # prefer filename, then display_name, then filename from URL
    for key in ('filename', 'display_name', 'name', 'title'):
        if key in row and row[key]:
            return row[key]
    return None


def fname_from_url(url):
    p = urlparse(url).path
    base = os.path.basename(p)
    if base:
        return unquote(base)
    return f'download_{int(time.time())}'


def get_url_from_row(row):
    # common column names: url, thumbnail_url
    for key in ('url', 'html_url', 'thumbnail_url', 'link'):
        if key in row and row[key]:
            return row[key]
    # fallback: look for any cell that looks like http
    for v in row.values():
        if isinstance(v, str) and v.startswith('http'):
            return v
    return None


def download_one(session, url, dest_path, token=None, use_query=False, timeout=(5, 20)):
    params = None
    if use_query and token and 'canvas.instructure.com' in url:
        params = {'access_token': token}
    try:
        resp = session.get(url, stream=True, timeout=timeout, params=params)
    except Exception as e:
        return False, f'request failed: {e}'
    if resp.status_code >= 400:
        return False, f'HTTP {resp.status_code}: {resp.text[:200]}'
    ctype = resp.headers.get('Content-Type','')
    if 'html' in ctype.lower():
        return False, 'skipped HTML response'

    # filename from content-disposition
    cd = resp.headers.get('Content-Disposition')
    fname = None
    if cd:
        import re
        m = re.search(r"filename\*=UTF-8''(?P<f>[^;]+)", cd)
        if m:
            fname = unquote(m.group('f'))
        else:
            m = re.search(r'filename="?(?P<f>[^";]+)"?', cd)
            if m:
                fname = m.group('f')

    if not fname:
        fname = fname_from_url(url)

    target = os.path.join(dest_path, fname)
    if os.path.exists(target):
        return True, f'exists ({target})'

    try:
        with open(target, 'wb') as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
    except Exception as e:
        try:
            os.remove(target)
        except Exception:
            pass
        return False, f'write failed: {e}'

    return True, target


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    csv_dir = os.path.join(root, 'data')
    if not os.path.isdir(csv_dir):
        print('data/ not found. Run export_via_http.py first.')
        sys.exit(1)

    token = os.getenv('ACCESS_TOKEN') or os.getenv('CANVAS_KEY')
    use_query = False
    if os.getenv('ACCESS_TOKEN'):
        use_query = True
    if os.getenv('CANVAS_USE_QUERY_TOKEN','0') in ('1','true','True'):
        use_query = True

    session = session_with_retries(token=token, use_query=use_query)

    files = [f for f in os.listdir(csv_dir) if f.startswith('files_') and f.lower().endswith('.csv')]
    if not files:
        print('No files_*.csv files found in data/')
        return

    out_root = os.path.join(root, 'files')
    os.makedirs(out_root, exist_ok=True)

    total = 0
    ok = 0
    failed = 0

    for fname in files:
        path = os.path.join(csv_dir, fname)
        base = os.path.splitext(fname)[0]
        dest = os.path.join(out_root, base)
        os.makedirs(dest, exist_ok=True)
        print(f'Processing {path} -> {dest}')
        with open(path, newline='', encoding='utf-8') as fh:
            rdr = csv.DictReader(fh)
            for row in rdr:
                url = get_url_from_row(row)
                if not url:
                    continue
                total += 1
                preferred_name = get_fname(row)
                # download
                success, info = download_one(session, url, dest, token=token, use_query=use_query)
                if success:
                    ok += 1
                    print(f'  OK: {info}')
                else:
                    failed += 1
                    print(f'  FAIL: {url} -> {info}')

    print(f'Done. total={total} ok={ok} failed={failed}')


if __name__ == '__main__':
    main()
