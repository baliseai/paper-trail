#!/usr/bin/env python3
"""Validate a Paper Trail submission JSON before sending it for held-out grading.

Zero external dependencies (Python standard library only).

Usage:
    python scripts/validate_submission.py path/to/submission.json
    python scripts/validate_submission.py path/to/submission.json --check-open
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
QUESTIONS_PATH = os.path.join(ROOT, "docs", "data", "questions.json")
DOCUMENTS_PATH = os.path.join(ROOT, "docs", "data", "documents.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission", help="Path to filled submission JSON file")
    ap.add_argument("--check-open", action="store_true", help="Print side-by-side comparison on the open questions")
    args = ap.parse_args()

    errors = []
    warnings = []

    try:
        sub = load_json(args.submission)
    except Exception as e:
        print(f"ERROR: Could not parse JSON: {e}", file=sys.stderr)
        sys.exit(2)

    questions = load_json(QUESTIONS_PATH)
    q_by_id = {q["id"]: q for q in questions}
    expected_ids = [q["id"] for q in questions]

    valid_paths = set()
    if os.path.exists(DOCUMENTS_PATH):
        docs = load_json(DOCUMENTS_PATH)
        valid_paths = {d["path"] for d in docs}

    # 1. Validate system metadata
    sys_block = sub.get("system")
    if not isinstance(sys_block, dict):
        errors.append("Missing or invalid top-level 'system' object.")
    else:
        for field in ("name", "harness", "model", "content_system", "retrieval", "run_date"):
            val = sys_block.get(field)
            if not isinstance(val, str) or not val.strip() or val.strip().startswith("Your ") or "The agent or assistant" in val:
                errors.append(f"system.{field} must be filled in with your actual system metadata.")
        ing = sys_block.get("ingestion")
        if not isinstance(ing, dict):
            errors.append("Missing system.ingestion object.")
        else:
            if not isinstance(ing.get("no_human_categorization"), bool):
                errors.append("system.ingestion.no_human_categorization must be true or false (boolean).")
            desc = ing.get("description")
            if not isinstance(desc, str) or not desc.strip() or desc.startswith("How the library was ingested"):
                errors.append("system.ingestion.description must describe how the library was ingested.")

    # 2. Validate answers
    answers = sub.get("answers")
    if not isinstance(answers, list):
        errors.append("Missing or invalid top-level 'answers' list.")
        answers = []

    seen = set()
    ans_by_id = {}
    empty_answers = 0
    bad_source_paths = []
    over_limit = []

    for i, item in enumerate(answers):
        if not isinstance(item, dict):
            errors.append(f"answers[{i}] is not an object.")
            continue
        qid = item.get("id")
        if qid not in q_by_id:
            errors.append(f"answers[{i}] has unknown question id: {qid!r}")
            continue
        if qid in seen:
            errors.append(f"Duplicate answer for question id: {qid}")
            continue
        seen.add(qid)
        ans_by_id[qid] = item

        ans_text = item.get("answer")
        if not isinstance(ans_text, str):
            errors.append(f"{qid}: 'answer' must be a string.")
        elif not ans_text.strip():
            empty_answers += 1

        srcs = item.get("sources")
        if not isinstance(srcs, list) or not all(isinstance(s, str) for s in srcs):
            errors.append(f"{qid}: 'sources' must be a list of strings (library paths).")
        elif valid_paths:
            for s in srcs:
                if s not in valid_paths:
                    bad_source_paths.append((qid, s))

        secs = item.get("seconds")
        if secs is not None:
            if not isinstance(secs, (int, float)) or secs < 0:
                errors.append(f"{qid}: 'seconds' must be a non-negative number or null.")
            elif secs > 600:
                over_limit.append((qid, secs))

        for tok_field in ("input_tokens", "output_tokens"):
            tv = item.get(tok_field)
            if tv is not None and (not isinstance(tv, (int, float)) or tv < 0):
                errors.append(f"{qid}: '{tok_field}' must be a non-negative number or null.")

    missing = [qid for qid in expected_ids if qid not in seen]
    if missing:
        errors.append(f"Missing {len(missing)} question(s): {', '.join(missing[:10])}" + (" ..." if len(missing) > 10 else ""))

    if empty_answers:
        warnings.append(f"{empty_answers} question(s) have an empty answer string (will be graded 'No answer').")
    if over_limit:
        warnings.append(f"{len(over_limit)} run(s) exceeded the 600s (10-minute) time limit: " +
                        ", ".join(f"{q} ({s}s)" for q, s in over_limit[:5]))
    if bad_source_paths:
        warnings.append(f"{len(bad_source_paths)} cited source(s) do not match exact library paths in documents.json "
                        f"(e.g. {bad_source_paths[0][0]}: {bad_source_paths[0][1]!r}).")

    # Summary
    print(f"Validated {len(seen)}/{len(expected_ids)} questions.")
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("OK: submission format is valid.")

    if args.check_open:
        print(f"\n=== Open Questions Check ({sum(q['split'] == 'open' for q in questions)}) ===")
        for q in questions:
            if q["split"] != "open":
                continue
            item = ans_by_id.get(q["id"], {})
            ans_preview = (item.get("answer") or "").replace("\n", " ").strip()[:240]
            print(f"\n[{q['id']} · {q['kind_name']}] {q['question']}")
            print(f"  Gold  : {q['answer']}")
            print(f"  Yours : {ans_preview}")


if __name__ == "__main__":
    main()
