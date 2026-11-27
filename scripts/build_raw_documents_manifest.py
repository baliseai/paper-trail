#!/usr/bin/env python3
"""Strip extracted text (and optional Vertesia type classification) from data/documents/
so the published corpus manifest ships only raw file metadata and nasa.gov source URLs.

Every tested system must download and ingest the raw files (PDFs, HTML, TIFFs, JPEGs) itself.

Usage:
    python scripts/build_raw_documents_manifest.py --drop-type
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IN_DIR = os.path.join(ROOT, "data", "documents")
OUT_FILE = os.path.join(ROOT, "data", "documents.parquet")

RAW_COLS = [
    "id",
    "path",
    "folder",
    "subfolder",
    "name",
    "title",
    "title_from",
    "source",
    "source_url",
    "ntrs_id",
    "bytes",
    "pages",
    "sha256",
    "derived",
    "note",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="src", default=IN_DIR, help="Input Parquet directory or file")
    ap.add_argument("--out", dest="dst", default=OUT_FILE, help="Output single Parquet file (no text)")
    ap.add_argument("--keep-type", action="store_true", help="Keep automatic Vertesia 'type' column (dropped by default)")
    args = ap.parse_args()

    cols = list(RAW_COLS)
    if args.keep_type:
        cols.insert(7, "type")

    try:
        import pandas as pd
        df = pd.read_parquet(args.src)
        keep = [c for c in cols if c in df.columns]
        out = df[keep]
        out.to_parquet(args.dst, index=False)
        size_mb = os.path.getsize(args.dst) / (1024 * 1024)
        print(f"Wrote {len(out)} rows, {len(keep)} columns ({', '.join(keep)}) -> {args.dst} ({size_mb:.2f} MB)")
    except ImportError:
        try:
            import duckdb
        except ImportError:
            print("ERROR: install pandas+pyarrow or duckdb to rebuild Parquet files.", file=sys.stderr)
            sys.exit(2)
        src_glob = os.path.join(args.src, "*.parquet") if os.path.isdir(args.src) else args.src
        con = duckdb.connect()
        avail = [r[0] for r in con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [src_glob]).fetchall()]
        keep = [c for c in cols if c in avail]
        col_sql = ", ".join(keep)
        con.execute(f"COPY (SELECT {col_sql} FROM read_parquet(?)) TO ? (FORMAT PARQUET)", [src_glob, args.dst])
        cnt = con.execute("SELECT COUNT(*) FROM read_parquet(?)", [args.dst]).fetchone()[0]
        size_mb = os.path.getsize(args.dst) / (1024 * 1024)
        print(f"Wrote {cnt} rows, {len(keep)} columns ({', '.join(keep)}) -> {args.dst} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
