#!/usr/bin/env python3
"""Run the Paper Trail questions through your own system and write a submission file.

Standard library only. You supply one of:

  --adapter my_adapter.py   a Python file that defines  answer(question) -> str | dict
  --command "./my-agent"    any program: one question as JSON on stdin, the answer on stdout

Either way your code receives one question:

  {"id": "M1", "question": "<as written>", "reference_date": "23 November 2026",
   "prompt": "Treat today as 23 November 2026. <as written>"}

and returns the answer as plain text, or as JSON:

  {"answer": "...", "sources": ["Agreements/Active/HQ/file.pdf"],
   "input_tokens": 47000, "output_tokens": 1800}

Every question runs once, in a fresh process, and is stopped at the time limit (600 s).
The run is checkpointed to runs/<system-id>.json after each question; running the same
command again skips what is done.

Examples:
    # the 25 open questions first
    python scripts/run_custom.py --system-id my-system --adapter scripts/adapters/example_adapter.py --split open

    # then everything, four at a time
    python scripts/run_custom.py --system-id my-system --adapter scripts/adapters/example_adapter.py --workers 4

    # any language
    python scripts/run_custom.py --system-id my-system --command "node my-agent.js" --system system.json
"""
import argparse
import concurrent.futures
import importlib.util
import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_QUESTIONS = os.path.join(ROOT, "docs", "data", "questions.json")
DEFAULT_TEMPLATE = os.path.join(ROOT, "submission-template.json")
DEFAULT_OUT_DIR = os.path.join(ROOT, "runs")
REFERENCE_DATE = "23 November 2026"
RESULT_FIELDS = ("answer", "sources", "input_tokens", "output_tokens")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_adapter(path):
    spec = importlib.util.spec_from_file_location("paper_trail_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "answer", None)):
        raise SystemExit(f"{path} must define a function answer(question).")
    return module


def worker_main(adapter_path):
    """Child process: read one question on stdin, call the adapter, print JSON on stdout."""
    question = json.load(sys.stdin)
    real_stdout = sys.stdout
    sys.stdout = sys.stderr  # keep the adapter's own prints out of the result
    result = load_adapter(adapter_path).answer(question)
    sys.stdout = real_stdout
    json.dump(result if isinstance(result, dict) else {"answer": "" if result is None else str(result)}, sys.stdout)


def parse_output(text):
    """Accept a JSON object with an "answer" key, or treat the whole output as the answer."""
    text = text.strip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "answer" in data:
                return data
        except ValueError:
            pass
    return {"answer": text}


def blank(qid):
    return {"id": qid, "answer": "", "sources": [], "seconds": None, "input_tokens": None, "output_tokens": None}


def is_done(item):
    return bool((item.get("answer") or "").strip()) or bool(item.get("hit_time_limit"))


def run_one(question, argv, time_limit):
    payload = {
        "id": question["id"],
        "question": question["question"],
        "reference_date": REFERENCE_DATE,
        "prompt": f"Treat today as {REFERENCE_DATE}. {question['question']}",
    }
    record = blank(question["id"])
    start = time.monotonic()
    try:
        # Own process group, so a timeout also stops anything the program started.
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
    except OSError as e:
        record.update(seconds=0.0, error=f"could not start: {e}")
        return record
    try:
        stdout, stderr = proc.communicate(json.dumps(payload), timeout=time_limit)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (AttributeError, ProcessLookupError, PermissionError):
            proc.kill()
        proc.communicate()
        record.update(seconds=float(time_limit), hit_time_limit=True)
        return record
    record["seconds"] = round(time.monotonic() - start, 1)
    if proc.returncode != 0:
        record["error"] = f"exit {proc.returncode}: {stderr.strip()[-300:]}"
        return record
    result = parse_output(stdout)
    record["answer"] = str(result.get("answer") or "").strip()
    sources = result.get("sources") or []
    record["sources"] = [s for s in sources if isinstance(s, str)] if isinstance(sources, list) else []
    for field in ("input_tokens", "output_tokens"):
        value = result.get(field)
        record[field] = value if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    return record


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        return worker_main(sys.argv[2])

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--system-id", required=True, help="Output file name: <out-dir>/<system-id>.json")
    how = ap.add_mutually_exclusive_group(required=True)
    how.add_argument("--adapter", help="Python file defining answer(question)")
    how.add_argument("--command", help="Program that reads one question as JSON on stdin and prints the answer")
    ap.add_argument("--system", help="JSON file with the submission's 'system' block (overrides the adapter's SYSTEM)")
    ap.add_argument("--split", choices=["open", "held-out"], help="Run one split only; 'open' is the 25 with published answers")
    ap.add_argument("--ids", help="Comma-separated question ids, e.g. P6,P7,P15")
    ap.add_argument("--workers", type=int, default=1, help="Questions to run at once (default: 1)")
    ap.add_argument("--time-limit", type=int, default=600, help="Seconds per question; the benchmark rule is 600")
    ap.add_argument("--questions", default=DEFAULT_QUESTIONS, help=argparse.SUPPRESS)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Output directory (default: ./runs, ignored by git)")
    args = ap.parse_args()

    questions = load_json(args.questions)
    selected = questions
    if args.split:
        selected = [q for q in selected if q["split"] == args.split]
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        unknown = wanted - {q["id"] for q in questions}
        if unknown:
            ap.error(f"unknown question id(s): {', '.join(sorted(unknown))}")
        selected = [q for q in selected if q["id"] in wanted]

    system = dict(load_json(DEFAULT_TEMPLATE)["system"])
    if args.adapter:
        adapter_path = os.path.abspath(args.adapter)
        system.update(getattr(load_adapter(adapter_path), "SYSTEM", None) or {})
        argv = [sys.executable, os.path.abspath(__file__), "--worker", adapter_path]
    else:
        argv = shlex.split(args.command)
    if args.system:
        system.update(load_json(args.system))
    system["run_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    os.makedirs(args.out_dir, exist_ok=True)
    out_path = os.path.join(args.out_dir, f"{args.system_id}.json")
    records = {}
    if os.path.exists(out_path):
        records = {a["id"]: a for a in load_json(out_path).get("answers", []) if isinstance(a, dict) and "id" in a}

    def save():
        payload = {"system": system, "answers": [records.get(q["id"]) or blank(q["id"]) for q in questions]}
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp, out_path)

    todo = [q for q in selected if not is_done(records.get(q["id"], {}))]
    total, finished = len(selected), len(selected) - len(todo)
    print(f"{args.system_id}: {finished}/{total} already done, {len(todo)} to run, {args.workers} at a time.", flush=True)
    save()

    lock = threading.Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(run_one, q, argv, args.time_limit): q for q in todo}
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            with lock:
                records[record["id"]] = record
                finished += 1
                save()
            state = "TIMEOUT" if record.get("hit_time_limit") else "ERROR" if record.get("error") else "ok" if record["answer"] else "empty"
            detail = f"  {record['error']}" if record.get("error") else ""
            print(f"[{finished:3d}/{total}] {record['id']:4s} {state:7s} {record['seconds']:6.1f}s{detail}", flush=True)

    failed = sum(1 for q in selected if records.get(q["id"], {}).get("error"))
    timeouts = sum(1 for q in selected if records.get(q["id"], {}).get("hit_time_limit"))
    print(f"Wrote {out_path}: {timeouts} hit the time limit, {failed} failed (rerun the same command to retry those).")
    print(f"Next: python scripts/validate_submission.py {os.path.relpath(out_path)}")
    print(f"      python scripts/grade_open.py {os.path.relpath(out_path)} --judge <provider>:<model>")


if __name__ == "__main__":
    main()
