#!/usr/bin/env python3
"""Grade your answers to the 25 open Paper Trail questions against their published answers.

The 25 open questions ship with reference answers, so you can score a run yourself before
sending anything. A language model does the grading, with the benchmark's rubric. It is
your own estimate: leaderboard scores come from the 125 held-out questions, graded by the
maintainers.

Pick one or more judges with --judge:

  anthropic:<model>   Anthropic API      pip install anthropic   ANTHROPIC_API_KEY
  openai:<model>      OpenAI-compatible  pip install openai      OPENAI_API_KEY, OPENAI_BASE_URL
  command:<program>   anything else: the grading request as JSON on stdin, the grade as JSON on stdout

The judge is not told which system produced the answer. With two judges, a disagreement
takes the lower grade; with three or more, the majority.

Examples:
    python scripts/grade_open.py runs/my-system.json --judge anthropic:claude-opus-5-5
    python scripts/grade_open.py runs/my-system.json --judge anthropic:claude-opus-5-5 --judge openai:gpt-6.2-sol
"""
import argparse
import collections
import concurrent.futures
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
QUESTIONS_PATH = os.path.join(ROOT, "docs", "data", "questions.json")
REFERENCE_DATE = "23 November 2026"

GRADES = ("correct", "partial", "no answer", "wrong")  # best to worst; a wrong answer also costs a point in the strict score
POINTS = {"correct": 1.0, "partial": 0.5, "no answer": 0.0, "wrong": 0.0}

RUBRIC = """You grade one answer for the Paper Trail benchmark. A system was asked a question about a library of public NASA documents. Compare its answer with the reference answer, which was built from the documents, and give one grade.

Grades:
- correct: says what the documents say. Counts and totals within about 10% of the reference count as correct. Extra detail that does not contradict the reference is fine.
- partial: finds the right documents and points the right way, but leaves something out, or gives a key figure more than 10% off.
- wrong: states something the reference contradicts, or names the wrong document.
- no answer: gives up, asks a clarifying question, or says nothing is there when something is.

Judge only against the reference answer and the grader's note. Do not use outside knowledge. Wording, order and format do not matter.

Reply with JSON only: {"grade": "correct" | "partial" | "wrong" | "no answer", "reason": "<one sentence>"}"""

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "grade": {"type": "string", "enum": ["correct", "partial", "wrong", "no answer"]},
        "reason": {"type": "string"},
    },
    "required": ["grade", "reason"],
    "additionalProperties": False,
}


class JudgeError(Exception):
    pass


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(question, item):
    sources = "\n".join(f"- {s}" for s in question.get("source_files") or []) or "(none listed)"
    cited = "\n".join(f"- {s}" for s in item.get("sources") or []) or "(none cited)"
    return (
        f"Question, exactly as asked (today is {REFERENCE_DATE}):\n{question['question']}\n\n"
        f"Reference answer:\n{question['answer']}\n\n"
        f"Files the reference answer rests on:\n{sources}\n\n"
        f"Grader's note:\n{question.get('note') or '(none)'}\n\n"
        f"The system's answer:\n{item.get('answer') or ''}\n\n"
        f"Files the system cited:\n{cited}"
    )


def parse_grade(text):
    """Read {"grade": ..., "reason": ...} out of a judge's reply, tolerating prose or a code fence around it."""
    text = text or ""
    for candidate in [text] + re.findall(r"\{.*\}", text, flags=re.S) + re.findall(r"\{.*?\}", text, flags=re.S):
        try:
            data = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(data, dict) and "grade" in data:
            grade = str(data["grade"]).strip().lower().replace("_", " ").replace("-", " ")
            if grade in POINTS:
                return {"grade": grade, "reason": str(data.get("reason") or "").strip()}
    raise JudgeError(f"no grade in the judge's reply: {(text or '').strip()[:200]!r}")


def judge_anthropic(model):
    try:
        import anthropic
    except ImportError:
        raise SystemExit("The anthropic judge needs the SDK: pip install anthropic")
    client = anthropic.Anthropic()

    def judge(question, item):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=16000,
                system=RUBRIC,
                messages=[{"role": "user", "content": build_prompt(question, item)}],
                output_config={"effort": "high", "format": {"type": "json_schema", "schema": GRADE_SCHEMA}},
            )
        except anthropic.APIConnectionError as e:
            raise JudgeError(f"could not reach the API: {e}")
        except anthropic.APIStatusError as e:
            raise JudgeError(f"API error {e.status_code}: {e.message}")
        # No fallback model on purpose: the grade has to come from the judge that was named.
        if response.stop_reason == "refusal":
            raise JudgeError("the judge declined to grade this answer")
        return parse_grade(next((b.text for b in response.content if b.type == "text"), ""))

    return judge


def judge_openai(model):
    try:
        from openai import OpenAI, OpenAIError
    except ImportError:
        raise SystemExit("The openai judge needs the SDK: pip install openai")
    client = OpenAI()  # reads OPENAI_API_KEY and, for other compatible services, OPENAI_BASE_URL

    def judge(question, item):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": RUBRIC}, {"role": "user", "content": build_prompt(question, item)}],
            )
        except OpenAIError as e:
            raise JudgeError(f"API error: {e}")
        return parse_grade(response.choices[0].message.content or "")

    return judge


def judge_command(command):
    argv = shlex.split(command)

    def judge(question, item):
        request = {
            "system": RUBRIC,
            "prompt": build_prompt(question, item),
            "id": question["id"],
            "question": question["question"],
            "reference_answer": question["answer"],
            "answer": item.get("answer") or "",
        }
        try:
            done = subprocess.run(argv, input=json.dumps(request), capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise JudgeError(f"judge command failed: {e}")
        if done.returncode != 0:
            raise JudgeError(f"judge command exit {done.returncode}: {done.stderr.strip()[-200:]}")
        return parse_grade(done.stdout)

    return judge


JUDGES = {"anthropic": judge_anthropic, "openai": judge_openai, "command": judge_command}


def make_judge(spec):
    kind, _, rest = spec.partition(":")
    if kind not in JUDGES or not rest.strip():
        raise SystemExit(f"--judge {spec!r}: use anthropic:<model>, openai:<model> or command:<program>")
    return JUDGES[kind](rest.strip())


def settle(grades):
    """One grade from several judges: unanimous, else the majority of three or more, else the lowest."""
    if len(set(grades)) == 1:
        return grades[0], True
    top, count = collections.Counter(grades).most_common(1)[0]
    if len(grades) >= 3 and count > len(grades) / 2:
        return top, False
    return max(grades, key=GRADES.index), False


def grade_question(question, item, judges):
    if not (item.get("answer") or "").strip():
        why = "stopped at the time limit" if item.get("hit_time_limit") else "empty answer"
        return {"grade": "no answer", "agreed": True, "judges": {}, "reason": why}
    verdicts, errors = {}, {}
    for spec, judge in judges.items():
        for attempt in (1, 2):
            try:
                verdicts[spec] = judge(question, item)
                errors.pop(spec, None)
                break
            except JudgeError as e:
                errors[spec] = str(e)
    if errors:
        return {"grade": None, "agreed": False, "judges": verdicts, "errors": errors}
    grade, agreed = settle([v["grade"] for v in verdicts.values()])
    return {"grade": grade, "agreed": agreed, "judges": verdicts}


def summarize(rows):
    n = len(rows)
    counts = collections.Counter(r["grade"] for r in rows)
    points = sum(POINTS[r["grade"]] for r in rows)
    by_kind = {}
    for r in rows:
        by_kind.setdefault(r["kind_name"], []).append(POINTS[r["grade"]])
    return {
        "questions": n,
        "score": round(100 * points / n, 1),
        "strict": round(100 * (points - counts["wrong"]) / n, 1),
        "correct": counts["correct"],
        "partial": counts["partial"],
        "wrong": counts["wrong"],
        "no_answer": counts["no answer"],
        "by_kind": {k: round(100 * sum(v) / len(v), 1) for k, v in by_kind.items()},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission", help="Submission JSON, for example runs/my-system.json")
    ap.add_argument("--judge", action="append", required=True, metavar="KIND:NAME",
                    help="anthropic:<model>, openai:<model> or command:<program>; repeat for several judges")
    ap.add_argument("--workers", type=int, default=4, help="Questions graded at once (default: 4)")
    ap.add_argument("--out", help="Where to write the grades (default: next to the submission, .open-grades.json)")
    args = ap.parse_args()

    submission = load_json(args.submission)
    answers = {a["id"]: a for a in submission.get("answers", []) if isinstance(a, dict) and "id" in a}
    open_questions = [q for q in load_json(QUESTIONS_PATH) if q["split"] == "open"]
    judges = {spec: make_judge(spec) for spec in args.judge}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(lambda q: grade_question(q, answers.get(q["id"], {}), judges), open_questions))

    rows = []
    for q, r in zip(open_questions, results):
        rows.append({"id": q["id"], "kind": q["kind"], "kind_name": q["kind_name"], **r})
        mark = "" if r["agreed"] else "  (judges disagreed)" if r["grade"] else f"  NOT GRADED: {'; '.join(r['errors'].values())}"
        print(f"{q['id']:4s} {q['kind_name']:26s} {r['grade'] or '-':10s}{mark}")

    out_path = args.out or re.sub(r"\.json$", "", args.submission) + ".open-grades.json"
    ungraded = [r["id"] for r in rows if not r["grade"]]
    report = {"submission": os.path.basename(args.submission), "judges": args.judge, "questions": rows}
    if not ungraded:
        report["summary"] = summarize(rows)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    if ungraded:
        print(f"\nNo score: {len(ungraded)} question(s) could not be graded ({', '.join(ungraded)}). Details in {out_path}.")
        sys.exit(1)

    s = report["summary"]
    print(f"\nScore {s['score']}  (strict {s['strict']})  on the {s['questions']} open questions")
    print(f"{s['correct']} correct, {s['partial']} partial, {s['wrong']} wrong, {s['no_answer']} no answer")
    for kind, value in s["by_kind"].items():
        print(f"  {kind:26s} {value}")
    split = sum(1 for r in rows if not r["agreed"])
    if split:
        print(f"Judges disagreed on {split} question(s).")
    print(f"Your own estimate, graded by {', '.join(args.judge)}. Details in {out_path}.")


if __name__ == "__main__":
    main()
