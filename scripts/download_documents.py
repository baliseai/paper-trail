#!/usr/bin/env python3
"""Rebuild the Paper Trail library from NASA's own servers.

Reads the `documents` table (the Parquet shards in data/documents/), downloads every file from its nasa.gov source URL and writes
it under the same folder path, so the result can be loaded into SharePoint (or any system) exactly as listed.

    pip install pandas pyarrow          # or: pip install duckdb
    python scripts/download_documents.py --out ./library
    python scripts/download_documents.py --out ./library --folder Agreements --workers 2
    python scripts/download_documents.py --out ./library --match '/HQ/37860_' --dry-run

Checks: size for every file, sha256 where the table has one (all files outside Technical Reports). Files that
already exist with the right size/hash are skipped, so the script can be re-run after an interruption.

Derived files:
  * 131 "renamed copy" rows are byte-identical copies of another file: the same URL is fetched once and copied.
  * 168 "converted image" rows (Old shared drive/misc tiffs) are TIFF or JPEG renderings of an NTRS PDF. The script
    downloads the PDF and renders it again with poppler (pdftoppm) and libtiff (tiffcp), as the corpus builder did.
    The result has the same content but is not byte-identical, so its sha256 is not checked.

A report of every file that failed (for example a Space Act Agreement URL NASA has since retired) is written to
<out>/_download-report.json.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile, threading, time, urllib.error, urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = 'paper-trail-benchmark-downloader/1.0 (python urllib)'
COLS = ['path', 'source_url', 'bytes', 'sha256', 'derived', 'note', 'folder', 'ntrs_id']


def load_manifest(path):
    try:
        import pandas as pd
        df = pd.read_parquet(path, columns=COLS)
        return [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in df.to_dict('records')]
    except ImportError:
        import duckdb
        src = os.path.join(path, '*.parquet') if os.path.isdir(path) else path
        cur = duckdb.connect().execute(f"SELECT {', '.join(COLS)} FROM read_parquet(?)", [src])
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def is_nasa(url):
    host = urllib.parse.urlparse(url).hostname or ''
    return url.startswith('https://') and (host == 'nasa.gov' or host.endswith('.nasa.gov'))


def encode_url(url):
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parts.path), safe="/:@!$&'()*+,;=-._~%")
    query = urllib.parse.quote(urllib.parse.unquote(parts.query), safe="/?:@!$&'()*+,;=-._~%")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def fetch(url, dest, retries=4):
    if not is_nasa(url): raise ValueError('refusing a non-nasa.gov URL: ' + url)
    safe_url = encode_url(url)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + '.part'
    for attempt in range(retries):
        try:
            req = urllib.request.Request(safe_url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, 'wb') as f:
                if not is_nasa(r.geturl()): raise ValueError('redirected off nasa.gov: ' + r.geturl())
                shutil.copyfileobj(r, f, 1 << 20)
            os.replace(tmp, dest)
            return
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410): raise
            err = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            err = e
        time.sleep(2 ** attempt * 3)
    raise err


def render(pdf, dest, note):
    """Re-create a converted scan image from its source PDF (see the `note` column)."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        if note.startswith('TIFF'):
            subprocess.run(['pdftoppm', '-r', '200', '-mono', '-tiff', pdf, os.path.join(td, 'p')], check=True)
            pages = sorted(os.path.join(td, f) for f in os.listdir(td) if f.endswith('.tif'))
            subprocess.run(['tiffcp', '-c', 'g4', *pages, dest], check=True)
        else:
            n = re.search(r'page (\d+)', note).group(1)
            subprocess.run(['pdftoppm', '-r', '150', '-gray', '-jpeg', '-f', n, '-l', n, '-singlefile', pdf,
                            os.path.join(td, 'p')], check=True)
            shutil.move(os.path.join(td, 'p.jpg'), dest)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, help='folder to build the library in')
    ap.add_argument('--manifest', default=os.path.join(here, '..', 'data', 'documents.parquet'),
                    help='documents table: a Parquet file or a folder of shards')
    ap.add_argument('--folder', action='append', help='only these top-level folders (repeatable)')
    ap.add_argument('--match', help='only paths matching this regular expression')
    ap.add_argument('--workers', type=int, default=4, help='parallel downloads (be gentle with NASA servers)')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    rows = load_manifest(a.manifest)
    if a.folder: rows = [r for r in rows if r['folder'] in a.folder]
    if a.match: rows = [r for r in rows if re.search(a.match, r['path'])]
    print(f'{len(rows)} files, {sum(r["bytes"] or 0 for r in rows) / 1e9:.1f} GB')
    if a.dry_run:
        for r in rows[:20]: print(' ', r['source_url'], '->', r['path'])
        return
    if any(r['derived'] == 'converted image' for r in rows):
        missing = [t for t in ('pdftoppm', 'tiffcp') if not shutil.which(t)]
        if missing: print('warning: converted images need', ', '.join(missing), '(poppler-utils, libtiff-tools)')

    cache = os.path.join(a.out, '_sources')  # source PDFs of the converted images, deleted at the end
    locks, lock, fetched = {}, threading.Lock(), {}
    report = {'ok': 0, 'skipped': 0, 'failed': [], 'hash_mismatch': [], 'size_mismatch': []}

    def good(dest, r):
        if not os.path.exists(dest): return False
        if r['derived'] == 'converted image': return True
        if r['bytes'] is not None and os.path.getsize(dest) != r['bytes']: return False
        return not r['sha256'] or sha256(dest) == r['sha256']

    def one(r):
        dest = os.path.join(a.out, r['path'])
        url = r['source_url']
        if good(dest, r):
            if not r['derived']: fetched.setdefault(url, dest)
            return 'skipped', r
        with lock: ul = locks.setdefault(url, threading.Lock())
        with ul:  # one download per URL: renamed copies reuse the file already fetched
            if r['derived'] == 'converted image':
                src = os.path.join(cache, hashlib.sha1(url.encode()).hexdigest() + '.pdf')
                if not os.path.exists(src): fetch(url, src)
                render(src, dest, r['note'])
                return 'ok', r
            first = fetched.get(url)
            if first and os.path.exists(first):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copyfile(first, dest)
            else:
                fetch(url, dest)
                fetched[url] = dest
        if r['bytes'] is not None and os.path.getsize(dest) != r['bytes']: return 'size_mismatch', r
        if r['sha256'] and sha256(dest) != r['sha256']: return 'hash_mismatch', r
        return 'ok', r

    done = 0
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(one, r): r for r in rows}
        for f in as_completed(futs):
            r = futs[f]; done += 1
            try:
                status, _ = f.result()
            except Exception as e:  # noqa: BLE001 - report and keep going
                report['failed'].append({'path': r['path'], 'url': r['source_url'], 'error': str(e)[:200]})
            else:
                if status in ('ok', 'skipped'): report[status] += 1
                else: report[status].append({'path': r['path'], 'url': r['source_url']})
            if done % 200 == 0 or done == len(rows):
                print(f'{done}/{len(rows)}  ok {report["ok"]}  skipped {report["skipped"]}  failed {len(report["failed"])}',
                      flush=True)
    # source PDFs are only needed while rendering; keep them out of the library itself
    shutil.rmtree(cache, ignore_errors=True)
    with open(os.path.join(a.out, '_download-report.json'), 'w') as f: json.dump(report, f, indent=1)
    bad = len(report['failed']) + len(report['hash_mismatch']) + len(report['size_mismatch'])
    print('done;', bad, 'problems, see _download-report.json' if bad else 'no problems')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
