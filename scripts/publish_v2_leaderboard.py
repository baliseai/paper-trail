#!/usr/bin/env python3
"""Build the public v2.1 leaderboard data from the rubric grades.

Reads, from the private grading repository (default ../paper-trail-private):
  grades/<system-id>.rubric.public.json    aggregate scores of one system
  grades/<system-id>.rubric.private.json   per-question grades (used here only to count, never copied)
  runs/<system-id>.json                    the run (times, tokens); ./runs/ in this repository is read too

Writes, in this repository:
  docs/data/leaderboard.json   one row per shown system: scores, kinds, latency, tokens, run conditions
  docs/data/tokens.json        per Vertesia agent model: token means per question (fresh / cached / output)
  docs/data/questions.json     `solved_by` refreshed for the 25 open questions, removed from the held-out ones
  README.md, huggingface/README.md
                               the leaderboard table between <!-- leaderboard:start --> and <!-- leaderboard:end -->

Public output only: no answers, rubrics, judge reasons, run ids, model identifiers of the serving cloud, or
per-question grades of held-out questions. Every public field is built here from numbers, never copied from the
input files, and the output is scanned before anything is written (see FORBIDDEN).

Safe to rerun. A system whose run or rubric grade file is missing, or whose grade file holds fewer graded answers
than its run, is skipped with a warning.

  python3 scripts/publish_v2_leaderboard.py --studio-suffix v21h
  python3 scripts/publish_v2_leaderboard.py --studio-suffix v21r4 --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT.parent / "paper-trail-private"

KINDS = {"1": "Find a document or a fact", "2": "Read a clause", "3": "Count, list or total",
         "4": "Across libraries", "5": "Find, then act"}

# Vertesia agent rows: model key (as in the system id) -> display name. Order is the token chart's family order.
STUDIO_MODELS = [
    ("claude-opus-5.5", "Claude Opus 5.5"),
    ("claude-fable-5.2", "Claude Fable 5.2"),
    ("claude-sonnet-5.5", "Claude Sonnet 5.5"),
    ("gemini-4-neon", "Gemini 4 Neon"),
    ("gemini-4-argon", "Gemini 4 Argon"),
    ("gpt-6.2-sol", "GPT 6.2 Sol"),
    ("gpt-6.2-astra", "GPT 6.2 Astra"),
    ("grok-4.7", "Grok 4.7"),
    ("mistral-large-4.0", "Mistral Large 4.0"),
    ("kimi-k3", "Kimi K3"),
    ("qwen4-max", "Qwen 4 Max"),
    ("deepseek-v4.1-flash", "DeepSeek V4.1 Flash"),
]
STUDIO_TIME_LIMIT_S = 3600
ASSISTANT_TIME_LIMIT_S = 600
MAX_RERUNS = 9  # stated on the page for the Claude.ai and ChatGPT rows

ALONE_SP = "SharePoint"
WITH_IDX = "SharePoint + Vertesia index"
RERUN_NOTE = ("{n} of the 150 answers are second attempts: the first had read an output file an earlier run left in "
              "the library, or stopped at a connector sign-in.")

# Assistant rows. `expect` holds stated facts checked against the data; `conditions` may name row fields in braces.
ASSISTANTS = [
    dict(run="claude-opus-5.5-medium-vertesia-v21", id="claude-vertesia", name="Claude.ai + Vertesia",
         harness_label="Claude.ai", harness_detail="Project chat, web search off",
         model_label="Claude Opus 5.5", model_detail="medium effort", reasoning_effort="medium",
         content_system=WITH_IDX, retrieval="Microsoft 365 connector + Vertesia connector"),
    dict(run="claude-opus-5.5-medium-sharepoint-v21", id="claude-alone", name="Claude.ai alone",
         harness_label="Claude.ai", harness_detail="Project chat, web search off",
         model_label="Claude Opus 5.5", model_detail="medium effort", reasoning_effort="medium",
         content_system=ALONE_SP, retrieval="Microsoft 365 connector (SharePoint search, open files)"),
    dict(run="chatgpt-6.2-medium-vertesia-v21", id="chatgpt-vertesia", name="ChatGPT + Vertesia",
         harness_label="ChatGPT", harness_detail="Project chat, web search off",
         model_label="GPT 6.2", model_detail="medium (“6.2 Medium”)", reasoning_effort="medium",
         content_system=WITH_IDX, retrieval="SharePoint connector + Vertesia app"),
    dict(run="chatgpt-6.2-medium-sharepoint-v21", id="chatgpt-alone", name="ChatGPT alone",
         harness_label="ChatGPT", harness_detail="Project chat, web search off",
         model_label="GPT 6.2", model_detail="medium (“6.2 Medium”)", reasoning_effort="medium",
         content_system=ALONE_SP, retrieval="SharePoint connector"),
    dict(run="copilot-chat-vertesia-v21", id="copilot-chat-vertesia", name="Microsoft 365 Copilot Chat + Vertesia",
         harness_label="Microsoft 365 Copilot Chat", harness_detail="Temporary chat, Work IQ on, web search off",
         model_label="Auto", model_detail="Copilot picks the model", reasoning_effort=None,
         content_system=WITH_IDX, retrieval="Work IQ search + Vertesia search skill, attached by hand in each chat",
         conditions="The Vertesia search skill was attached by hand in every chat; without it Copilot did not call "
                    "Vertesia. Copilot used Vertesia in 133 of the 150 answers."),
    dict(run="copilot-chat-alone-v21", id="copilot-chat-alone", name="Microsoft 365 Copilot Chat alone",
         harness_label="Microsoft 365 Copilot Chat", harness_detail="Temporary chat, Work IQ on, web search off",
         model_label="Auto", model_detail="Copilot picks the model", reasoning_effort=None,
         content_system=ALONE_SP, retrieval="Work IQ / SharePoint search (built in)"),
    dict(run="copilot-cowork-vertesia-v21", id="copilot-cowork-vertesia",
         name="Microsoft 365 Copilot Cowork + Vertesia",
         harness_label="Microsoft 365 Copilot Cowork", harness_detail="Work IQ on, web search off",
         model_label="Auto", model_detail="Copilot picks the model", reasoning_effort=None,
         content_system=WITH_IDX, retrieval="Work IQ search + Vertesia plugin",
         conditions="Copilot used Vertesia in 140 of the 150 answers."),
    dict(run="copilot-cowork-alone-v21", id="copilot-cowork-alone", name="Microsoft 365 Copilot Cowork alone",
         harness_label="Microsoft 365 Copilot Cowork", harness_detail="Work IQ on, web search off, Vertesia plugin off",
         model_label="Auto", model_detail="Copilot picks the model", reasoning_effort=None,
         content_system=ALONE_SP, retrieval="Work IQ / SharePoint search (built in)",
         conditions="Its file search found nothing on 112 of the 150 questions, and it gave no answer to them. "
                    "The rubric counts {no_answer} of them as no answer: an answer that also states something "
                    "the rubric checks (for example that a document does not exist) is graded on that. Two "
                    "answers ran past 600 seconds (724 and 858) and were kept.",
         expect={"over_limit": 2}),
]

# Anything matching these must never reach the public files.
FORBIDDEN = [
    (re.compile(r"arn:aws", re.I), "cloud model identifier"),
    (re.compile(r"publishers/|locations/", re.I), "cloud model path"),
    (re.compile(r"\b[0-9a-f]{24}\b"), "object or run id"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "uuid"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "email address"),
    (re.compile(r"https?://", re.I), "URL"),
    (re.compile(r"vertesia\.io|dev-main|dev1|localhost|sharepoint\.com", re.I), "internal hostname"),
    (re.compile(r"\b\d{12}\b"), "cloud account number"),
    (re.compile(r"tenant|partnerships-saa", re.I), "tenant name"),
    (re.compile(r"price|cost|\$\d|usd", re.I), "price"),
]


def warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


def load_json(p: Path):
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def answered(a: dict) -> bool:
    """A run entry counts once the question was asked (placeholders of a run in progress do not)."""
    return bool((a.get("answer") or "").strip()) or a.get("seconds") is not None or bool(a.get("hit_time_limit"))


def find_run(run_id: str, private: Path) -> tuple[Path, dict] | None:
    """The copy with the most answers among ./runs and <private>/runs."""
    best = None
    for d in (ROOT / "runs", private / "runs"):
        p = d / f"{run_id}.json"
        if not p.exists():
            continue
        try:
            r = load_json(p)
        except (OSError, json.JSONDecodeError) as e:
            warn(f"{p}: unreadable ({e})")
            continue
        n = sum(1 for a in r.get("answers", []) if answered(a))
        if best is None or n > best[2]:
            best = (p, r, n)
    return (best[0], best[1]) if best else None


def pct(sorted_vals: list[float], q: float) -> float | None:
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def mean(vals: list[float]) -> float | None:
    return statistics.fmean(vals) if vals else None


def run_metrics(answers: list[dict], time_limit_s: int) -> dict:
    done = [a for a in answers if answered(a)]
    secs = sorted(float(a["seconds"]) for a in done if a.get("seconds") is not None)
    tok = [a for a in done if a.get("input_tokens")]
    m = {
        "median_s": round(pct(secs, 0.5)) if secs else None,
        "p90_s": round(pct(secs, 0.9)) if secs else None,
        "time_limit_s": time_limit_s,
        "over_600s": sum(1 for s in secs if s > 600),
        "over_limit": sum(1 for s in secs if s > time_limit_s * 1.01),
        "timeouts": sum(1 for a in done if a.get("hit_time_limit")),
        "reruns": sum(1 for a in done if a.get("rerun_reason")),
        "input_tokens_per_q": None, "cached_input_per_q": None, "output_tokens_per_q": None,
        "tool_calls_mean": None, "steps_mean": None,
    }
    if tok:
        ins = [float(a["input_tokens"]) for a in tok]
        m.update({
            "input_tokens_per_q": round(mean(ins)),
            "cached_input_per_q": round(mean([float(a.get("cached_input_tokens") or 0) for a in tok])),
            "output_tokens_per_q": round(mean([float(a.get("output_tokens") or 0) for a in tok])),
            "input_tokens_median": round(statistics.median(ins)),
            "token_records": len(tok),
        })
    tc = [float(a["tool_calls"]) for a in done if a.get("tool_calls") is not None]
    lc = [float(a["llm_calls"]) for a in done if a.get("llm_calls") is not None]
    if tc:
        m["tool_calls_mean"] = round(mean(tc), 1)
    if lc:
        m["steps_mean"] = round(mean(lc), 1)
    return m


def token_set(answers: list[dict], grades_by_id: dict[str, str]) -> dict | None:
    tok = [a for a in answers if answered(a) and a.get("input_tokens")]
    if not tok:
        return None
    ins = sorted(float(a["input_tokens"]) for a in tok)
    return {
        "n": len(tok),
        "correct": sum(1 for a in tok if grades_by_id.get(a["id"]) == "correct"),
        "tokens_per_q": {
            "new": round(mean([float(a["input_tokens"]) - float(a.get("cached_input_tokens") or 0) for a in tok])),
            "write": 0,
            "read": round(mean([float(a.get("cached_input_tokens") or 0) for a in tok])),
            "out": round(mean([float(a.get("output_tokens") or 0) for a in tok])),
        },
        "steps": round(mean([float(a["llm_calls"]) for a in tok if a.get("llm_calls") is not None]) or 0, 1),
        "tool_calls": round(mean([float(a["tool_calls"]) for a in tok if a.get("tool_calls") is not None]) or 0, 1),
        "input_p50": round(pct(ins, 0.5)),
        "input_p90": round(pct(ins, 0.9)),
    }


def load_grades(private: Path, run_id: str, n_run: int) -> tuple[dict, dict] | None:
    gdir = private / "grades"
    pub_p, priv_p = gdir / f"{run_id}.rubric.public.json", gdir / f"{run_id}.rubric.private.json"
    for p in (pub_p, priv_p):
        if not p.exists():
            warn(f"{run_id}: rubric grade file missing ({p.name}); skipped")
            return None
    pub, priv = load_json(pub_p), load_json(priv_p)
    n_graded = (pub.get("summary") or {}).get("n_graded", 0)
    n_priv = len(priv.get("grades") or [])
    if n_graded < n_run or n_priv < n_run:
        warn(f"{run_id}: {min(n_graded, n_priv)} graded answers for {n_run} in the run; skipped")
        return None
    if pub["summary"].get("needs_human_review"):
        warn(f"{run_id}: {pub['summary']['needs_human_review']} grade(s) flagged by the grader for a look "
             f"(a criterion with too few valid judge votes, or a tie); shown as graded")
    return pub, priv


def row_from(meta: dict, s: dict, metrics: dict, n_questions: int) -> dict:
    eff = meta.get("reasoning_effort")
    row = {
        "id": meta["id"],
        "name": meta["name"],
        "assistant": meta["harness_label"],
        "harness": meta["harness_label"],
        "harness_label": meta["harness_label"],
        "harness_detail": meta["harness_detail"],
        "content_system": meta["content_system"],
        "retrieval": meta["retrieval"],
        "model": f"{meta['model_label']}, {eff} effort" if eff else meta["model_label"],
        "model_name": meta["model_label"],
        "model_label": meta["model_label"],
        "reasoning_effort": eff,
        "model_detail": meta["model_detail"],
        "n_questions": n_questions,
        "correct": int(s["correct"]), "partial": int(s["partial"]), "wrong": int(s["wrong"]),
        "no_answer": int(s["no_answer"]),
        "score": round(float(s["score"]), 1),
        "score_wrong_minus1": round(float(s["strict"]), 1),
        "by_kind": {k: round(float(s["by_kind"][k]), 1) for k in KINDS},
        "hardcore": round(float(s["hardcore_score"]), 1),
        "open_split": round(float(s["open_score"]), 1),
        "held_out": round(float(s["held_out_score"]), 1),
        "criterion_unanimity_pct": round(float(s["criterion_unanimity_pct"]), 1)
        if s.get("criterion_unanimity_pct") is not None else None,
        **{k: v for k, v in metrics.items() if k not in ("token_records", "over_limit")},
    }
    notes = []
    if meta.get("conditions"):
        notes.append(meta["conditions"].format(**row))
    if metrics.get("reruns"):
        notes.append(RERUN_NOTE.format(n=metrics["reruns"]))
    if notes:
        row["conditions"] = " ".join(notes)
    if metrics.get("token_records") is not None:
        row["token_records"] = metrics["token_records"]
    return row


def scan_public(text: str, where: str) -> None:
    for rx, what in FORBIDDEN:
        m = rx.search(text)
        if m:
            sys.exit(f"ABORT: {where} would contain a {what} ({m.group(0)!r}); nothing written")


def table(systems: list[dict]) -> str:
    def k(v):
        return "—" if v is None else f"{v / 1000:.0f}K" if v >= 10000 else f"{v / 1000:.1f}K"
    lines = ["| # | Harness | Model | Effort | Content system | Score | Strict | Hardest 11 | Held-out 125 | "
             "C / P / W / N | Median s | Input tokens / q | Output tokens / q |",
             "|--:|---|---|:-:|---|--:|--:|--:|--:|:-:|--:|--:|--:|"]
    rank, prev = 0, None
    for i, s in enumerate(systems, 1):
        if f"{s['score']:.1f}" != prev:
            rank, prev = i, f"{s['score']:.1f}"
        lines.append(
            f"| {rank} | {s['harness_label']} | {s['model_label']} | {s['reasoning_effort'] or '—'} | "
            f"{s['content_system']} | {s['score']:.1f} | {s['score_wrong_minus1']:.1f} | {s['hardcore']:.1f} | "
            f"{s['held_out']:.1f} | {s['correct']} / {s['partial']} / {s['wrong']} / {s['no_answer']} | "
            f"{s['median_s'] if s['median_s'] is not None else '—'} | {k(s.get('input_tokens_per_q'))} | "
            f"{k(s.get('output_tokens_per_q'))} |")
    return "\n".join(lines)


def write_table(path: Path, tbl: str) -> None:
    start, end = "<!-- leaderboard:start -->", "<!-- leaderboard:end -->"
    text = path.read_text(encoding="utf-8")
    if start not in text or end not in text:
        warn(f"{path.relative_to(ROOT)} has no leaderboard markers; table not written")
        return
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    path.write_text(f"{head}{start}\n{tbl}\n{end}{tail}", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--studio-suffix", required=True,
                    help="suffix of the Vertesia agent system ids: studio-<model>-medium-<suffix> (e.g. v21h, v21r4)")
    ap.add_argument("--private-repo", type=Path, default=DEFAULT_PRIVATE, help="path to the private grading repo")
    ap.add_argument("--as-of", default=dt.date.today().isoformat(), help="results date shown on the site")
    ap.add_argument("--dry-run", action="store_true", help="print the rows, write nothing")
    args = ap.parse_args()

    private: Path = args.private_repo
    data_dir = ROOT / "docs" / "data"
    questions = load_json(data_dir / "questions.json")
    qids = {q["id"] for q in questions}
    n_q = len(questions)

    candidates = [dict(run=f"studio-{slug}-medium-{args.studio_suffix}", id=f"studio-{slug}-medium",
                       name=f"Vertesia Agent System · {label} medium", harness_label="Vertesia Agent System",
                       harness_detail="Vertesia general agent, read-only tools", model_label=label,
                       model_detail="medium effort", reasoning_effort="medium", content_system="Vertesia",
                       retrieval="Vertesia index (built in)", slug=slug, time_limit_s=STUDIO_TIME_LIMIT_S)
                  for slug, label in STUDIO_MODELS]
    candidates += [dict(a, time_limit_s=ASSISTANT_TIME_LIMIT_S) for a in ASSISTANTS]

    systems, tokens, per_q, skipped = [], {}, {}, []
    for meta in candidates:
        found = find_run(meta["run"], private)
        if not found:
            warn(f"{meta['run']}: run file missing; skipped")
            skipped.append(meta["run"])
            continue
        run_path, run = found
        answers = run.get("answers", [])
        n_run = sum(1 for a in answers if answered(a))
        if n_run < n_q:
            warn(f"{meta['run']}: run has {n_run} of {n_q} answers; skipped")
            skipped.append(meta["run"])
            continue
        g = load_grades(private, meta["run"], n_run)
        if not g:
            skipped.append(meta["run"])
            continue
        pub, priv = g
        grades_by_id = {x["id"]: x["grade"] for x in priv["grades"]}
        if set(grades_by_id) != qids:
            warn(f"{meta['run']}: graded question ids differ from questions.json; skipped")
            skipped.append(meta["run"])
            continue
        metrics = run_metrics(answers, meta["time_limit_s"])
        if metrics["over_limit"] and not meta.get("expect", {}).get("over_limit"):
            warn(f"{meta['run']}: {metrics['over_limit']} answers ran past the {meta['time_limit_s']} s limit")
        if meta["harness_label"] in ("Claude.ai", "ChatGPT") and metrics["reruns"] > MAX_RERUNS:
            warn(f"{meta['run']}: {metrics['reruns']} second attempts; the page says at most {MAX_RERUNS}")
        row = row_from(meta, pub["summary"], metrics, n_q)
        for key, want in (meta.get("expect") or {}).items():
            got = metrics.get(key, row.get(key))
            if got != want:
                warn(f"{meta['run']}: the stated condition says {key}={want}, the data give {got}; fix the text")
        systems.append(row)
        per_q[row["id"]] = grades_by_id
        if meta.get("slug"):
            ts = token_set(answers, grades_by_id)
            if ts:
                tokens[f"{meta['slug']}|medium"] = ts
        print(f"ok   {row['id']:<26} {row['score']:5.1f}  C/P/W/N {row['correct']}/{row['partial']}/"
              f"{row['wrong']}/{row['no_answer']}  run {run_path.parent.parent.name}/runs/{run_path.name}")

    if not systems:
        warn("no system has both a complete run and a complete rubric grade file; nothing written")
        return 1

    systems.sort(key=lambda s: (-s["score"], -s["correct"], s["wrong"]))
    n_sys = len(systems)
    solved = {qid: sum(1 for g in per_q.values() if g.get(qid) == "correct") for qid in qids}
    hist = [0] * (n_sys + 1)
    for v in solved.values():
        hist[v] += 1

    lb = {
        "version": "v2.1",
        "grader": "rubric",
        "n_questions": n_q,
        "as_of": args.as_of,
        "n_systems": n_sys,
        "hardcore_ids": [q["id"] for q in questions if q.get("hardcore")],
        "open_ids": [q["id"] for q in questions if q.get("split") == "open"],
        "kinds": KINDS,
        "kind_counts": {k: sum(1 for q in questions if str(q["kind"]) == k) for k in KINDS},
        "time_limits_s": {"vertesia_agent": STUDIO_TIME_LIMIT_S, "assistants": ASSISTANT_TIME_LIMIT_S},
        "systems": systems,
        "difficulty_histogram": hist,
    }
    order = [m for m, _ in STUDIO_MODELS]
    tok_out = dict(sorted(tokens.items(), key=lambda kv: order.index(kv[0].split("|")[0])))

    # Per-question detail only for open questions: refresh solved_by there, drop it from held-out ones.
    new_q = []
    for q in questions:
        q = dict(q)
        if q.get("split") == "open":
            q["solved_by"] = solved[q["id"]]
        else:
            q.pop("solved_by", None)
        new_q.append(q)

    lb_text, tok_text, tbl = json.dumps(lb, indent=1), json.dumps(tok_out, indent=1), table(systems)
    scan_public(lb_text, "leaderboard.json")
    scan_public(tok_text, "tokens.json")
    scan_public(tbl, "the README table")

    print(f"\n{n_sys} systems shown, as of {args.as_of}; {len(skipped)} skipped: {', '.join(skipped) or 'none'}")
    if args.dry_run:
        print(tbl)
        return 0

    # Same encoding as the files already in the repository (ASCII escapes, no final newline).
    (data_dir / "leaderboard.json").write_text(lb_text, encoding="utf-8")
    (data_dir / "tokens.json").write_text(tok_text, encoding="utf-8")
    (data_dir / "questions.json").write_text(json.dumps(new_q, indent=1), encoding="utf-8")
    write_table(ROOT / "README.md", tbl)
    write_table(ROOT / "huggingface" / "README.md", tbl)
    print("wrote docs/data/leaderboard.json, tokens.json, questions.json and the README tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
