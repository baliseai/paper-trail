#!/usr/bin/env python3
"""Resumable Paper Trail benchmark runner for Vertesia Studio general agent (sys:GeneralAgent).

Reads all questions from docs/data/questions.json, runs each question verbatim with the
benchmark reference date (23 November 2026), enforces the 10-minute (600s) hard stop,
and checkpoints every completed answer to a submission-template-compatible JSON file.

Examples:
    # GPT 6.2 Sol (medium effort, default)
    python scripts/run_vertesia.py \\
        --system-id studio-gpt-6.2-sol-medium-v2 \\
        --name "Vertesia agent · GPT 6.2 Sol medium" \\
        --profile <PROFILE> \\
        --env <OPENAI_ENV_ID> --model gpt-6.2-sol --effort medium \\
        --workers 5

    # Claude Opus 5.5 (medium effort, default)
    python scripts/run_vertesia.py \\
        --system-id studio-claude-opus-5.5-medium-v2 \\
        --name "Vertesia agent · Claude Opus 5.5 medium" \\
        --profile <PROFILE> \\
        --env <BEDROCK_ENV_ID> \\
        --model arn:aws:bedrock:us-east-1:<ACCOUNT_ID>:inference-profile/global.anthropic.claude-opus-5-5 \\
        --effort medium --workers 4

    # Gemini 4 Neon (explicit medium inference profile)
    python scripts/run_vertesia.py \\
        --system-id studio-gemini-4-neon-medium-v2 \\
        --name "Vertesia agent · Gemini 4 Neon medium" \\
        --profile <PROFILE> \\
        --inference-profile <GEMINI_MEDIUM_PROFILE_ID> \\
        --model locations/global/publishers/google/models/gemini-4-neon \\
        --effort medium --workers 3
"""
import argparse
import concurrent.futures
import json
import os
import re
import statistics
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from trace_vertesia import extract_timing_breakdown, summarize_timings  # noqa: E402

DEFAULT_QUESTIONS = os.path.join(ROOT, "docs", "data", "questions.json")
DEFAULT_OUT_DIR = os.path.join(ROOT, "runs")


_TOKEN_CACHE = {"value": None, "fetched_at": 0.0, "profile": None}
_TOKEN_LOCK = threading.Lock()


def _get_env_for_cli():
    tp = _TOKEN_CACHE["profile"]
    if not tp:
        return None
    with _TOKEN_LOCK:
        now = time.time()
        if not _TOKEN_CACHE["value"] or (now - _TOKEN_CACHE["fetched_at"]) > 1200:
            try:
                if _TOKEN_CACHE["value"]:
                    subprocess.run(["vertesia", "-p", tp, "auth", "refresh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                tok = subprocess.check_output(["vertesia", "-p", tp, "auth", "token"], text=True, stderr=subprocess.DEVNULL, timeout=20).strip()
                _TOKEN_CACHE["value"] = tok
                _TOKEN_CACHE["fetched_at"] = now
            except Exception:
                pass
        env = dict(os.environ)
        if _TOKEN_CACHE["value"]:
            env["VERTESIA_TOKEN"] = _TOKEN_CACHE["value"]
        return env


def run_cli(args, timeout=60):
    return subprocess.check_output(["vertesia"] + args, text=True, stderr=subprocess.STDOUT, timeout=timeout, env=_get_env_for_cli())


def extract_sources(text):
    srcs = []
    for m in re.findall(r"Shared%20Documents/([^\)\s#]+)", text or ""):
        srcs.append(urllib.parse.unquote(m))
    return sorted(set(srcs))


def run_one_question(q, profile, env_id, model, inference_profile, time_limit=600, ref_date="23 November 2026"):
    qid = q["id"]
    prompt = f"Treat today as {ref_date}. {q['question']}"
    start_cmd = ["-p", profile, "agents", "start", "sys:GeneralAgent", "--no-stream", "--json"]
    if inference_profile:
        start_cmd += ["--inference-profile", inference_profile]
    else:
        start_cmd += ["-e", env_id, "-m", model]

    try:
        started = json.loads(run_cli(start_cmd, timeout=45))
        rid = started["id"]
    except Exception as e:
        return {
            "id": qid, "answer": "", "sources": [], "seconds": 0,
            "input_tokens": None, "cached_input_tokens": None, "output_tokens": None,
            "tool_calls": None, "llm_calls": None, "hit_time_limit": False,
            "run_id": None, "error": f"start_failed: {str(e)[:200]}"
        }

    for _ in range(25):
        try:
            insp = json.loads(run_cli(["-p", profile, "agents", "inspect", rid, "--json"], timeout=30))
            if insp["run"].get("activity_state") == "idle":
                break
        except Exception:
            pass
        time.sleep(2)

    t0 = time.time()
    try:
        run_cli(["-p", profile, "agents", "message", rid, prompt], timeout=45)
    except Exception as e:
        return {
            "id": qid, "answer": "", "sources": [], "seconds": round(time.time() - t0, 1),
            "input_tokens": None, "cached_input_tokens": None, "output_tokens": None,
            "tool_calls": None, "llm_calls": None, "hit_time_limit": False,
            "run_id": rid, "error": f"message_failed: {str(e)[:200]}"
        }

    time.sleep(8)
    hit_limit = False
    final_d = None

    while True:
        if time.time() - t0 >= time_limit:
            hit_limit = True
            try:
                run_cli(["-p", profile, "agents", "cancel", rid], timeout=30)
            except Exception:
                pass
            try:
                final_d = json.loads(run_cli(["-p", profile, "agents", "inspect", rid, "--details", "--messages", "-l", "100", "--json"], timeout=45))
            except Exception:
                final_d = None
            break

        try:
            d = json.loads(run_cli(["-p", profile, "agents", "inspect", rid, "--messages", "-l", "300", "--json"], timeout=30))
            run = d["run"]
            msgs = d.get("messages") or []
            st = run.get("activity_state")
            status = run.get("status")
            turns = (run.get("evaluation") or {}).get("rollup", {}).get("turns", 0)
            ans_msgs = [
                m for m in msgs
                if m.get("type") == 7
                and len(m.get("message") or "") > 40
                and "I'm ready" not in (m.get("message") or "")
                and "Ready when you are" not in (m.get("message") or "")
            ]
            if (st == "idle" and (ans_msgs or turns >= 2)) or status in ("completed", "failed", "terminated", "canceled"):
                time.sleep(3)
                final_d = json.loads(run_cli(["-p", profile, "agents", "inspect", rid, "--details", "--messages", "-l", "300", "--json"], timeout=45))
                break
        except Exception:
            pass
        time.sleep(8)

    seconds = round(time.time() - t0, 1)
    answer = ""
    in_tok = cached_tok = out_tok = tools = llm_calls = timing = None
    if final_d:
        run = final_d.get("run", {})
        tot = (run.get("evaluation") or {}).get("rollup", {}).get("totals", {})
        in_tok = tot.get("prompt_tokens")
        cached_tok = tot.get("cached_tokens")
        out_tok = tot.get("completion_tokens")
        tools = tot.get("tool_calls")
        llm_calls = tot.get("llm_calls")
        timing = extract_timing_breakdown(final_d)
        if tot.get("active_ms") and not hit_limit:
            seconds = round(tot["active_ms"] / 1000.0, 1)
        msgs = final_d.get("messages") or []
        ans_msgs = [
            m for m in msgs
            if m.get("type") == 7 and len(m.get("message") or "") > 10 and "I'm ready" not in (m.get("message") or "")
        ]
        if ans_msgs and not hit_limit:
            answer = ans_msgs[-1]["message"].strip()
            # An agent sometimes posts a short follow-up after its answer (for example when a background task
            # completes). The reader of the conversation sees both, so keep the full answer and append the follow-up.
            longest = max((m["message"].strip() for m in ans_msgs[:-1]), key=len, default="")
            if len(answer) < 400 and len(longest) >= 3 * len(answer):
                answer = longest + "\n\n" + answer

    return {
        "id": qid,
        "answer": answer,
        "sources": extract_sources(answer),
        "seconds": seconds,
        "input_tokens": in_tok,
        "cached_input_tokens": cached_tok,
        "output_tokens": out_tok,
        "tool_calls": tools,
        "llm_calls": llm_calls,
        "hit_time_limit": hit_limit,
        "run_id": rid,
        "timing": timing,
    }


def _summarize_trials(trials_by_qid):
    summary = {}
    for qid, runs in trials_by_qid.items():
        done = [r for r in runs if r.get("seconds") is not None]
        if not done:
            continue
        secs = [r["seconds"] for r in done]
        toks = [r["input_tokens"] for r in done if r.get("input_tokens") is not None]
        tims = [r["timing"] for r in done if r.get("timing")]
        rec = {
            "n_trials": len(done),
            "timeouts": sum(1 for r in done if r.get("hit_time_limit")),
            "seconds_min": round(min(secs), 1),
            "seconds_median": round(statistics.median(secs), 1),
            "seconds_mean": round(statistics.mean(secs), 1),
            "seconds_max": round(max(secs), 1),
            "seconds_stdev": round(statistics.stdev(secs), 1) if len(secs) > 1 else 0.0,
            "input_tokens_mean": round(statistics.mean(toks)) if toks else None,
            "input_tokens_stdev": round(statistics.stdev(toks)) if len(toks) > 1 else 0,
        }
        if tims:
            rec["llm_mean_s"] = round(statistics.mean(t["llm_s"] for t in tims), 1)
            rec["tool_wall_mean_s"] = round(statistics.mean(t["tool_wall_s"] for t in tims), 1)
            rec["system_wait_mean_s"] = round(statistics.mean(t["system_wait_s"] for t in tims), 1)
            rec["system_wait_pct_mean"] = round(statistics.mean(t["system_wait_pct"] for t in tims), 1)
        summary[qid] = rec
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--system-id", required=True, help="Output filename stem (saved to <out-dir>/<system-id>.json)")
    ap.add_argument("--name", required=True, help="Display name in system metadata")
    ap.add_argument("--profile", required=True, help="Vertesia CLI profile name (see `vertesia profiles`)")
    ap.add_argument("--token-profile", default=None, help="Optional CLI profile whose auth token is auto-refreshed into VERTESIA_TOKEN")
    ap.add_argument("--env", default=None, help="Vertesia model environment ID (omit if using --inference-profile)")
    ap.add_argument("--model", required=True, help="Model ID recorded in metadata (and passed to CLI if no profile)")
    ap.add_argument("--effort", default="medium", help="Reasoning effort label (e.g. low, medium, high)")
    ap.add_argument("--inference-profile", default=None, help="Vertesia inference profile ID override")
    ap.add_argument("--questions", default=DEFAULT_QUESTIONS, help="Path to questions JSON (default: docs/data/questions.json)")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Output directory (gitignored ./runs by default)")
    ap.add_argument("--workers", type=int, default=4, help="Concurrent questions (default: 4)")
    ap.add_argument("--time-limit", type=int, default=600, help="Hard timeout in seconds per question (default: 600)")
    ap.add_argument("--ids", default=None, help="Optional comma-separated subset of question IDs (e.g. P6,P7,P15)")
    ap.add_argument("--split", default=None, choices=["open", "held_out"], help="Run only one split (e.g. --split open for the 25-question qualification round)")
    ap.add_argument("--trials", type=int, default=1, help="Independent trials per question for latency variance & consistency (default: 1)")
    ap.add_argument("--schema-mode", default="human_authored", choices=["auto", "human_authored"])
    ap.add_argument("--no-human-cat", dest="no_human_cat", action="store_true", default=True)
    ap.add_argument("--human-cat", dest="no_human_cat", action="store_false")
    ap.add_argument("--ingestion-desc", default="Library synced into Vertesia project; automatic intake classification and extraction.")
    args = ap.parse_args()

    if args.token_profile:
        _TOKEN_CACHE["profile"] = args.token_profile
    if not args.inference_profile and not args.env:
        ap.error("Provide either --inference-profile or --env.")

    os.makedirs(args.out_dir, exist_ok=True)
    out_path = os.path.join(args.out_dir, f"{args.system_id}.json")

    questions = json.load(open(args.questions, "r", encoding="utf-8"))
    if args.split:
        questions = [q for q in questions if q.get("split") == args.split]
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        questions = [q for q in questions if q["id"] in wanted]

    done_by_key = {}
    if os.path.exists(out_path):
        existing = json.load(open(out_path, "r", encoding="utf-8"))
        for a in existing.get("trials" if args.trials > 1 else "answers", []):
            if a.get("answer") or a.get("hit_time_limit"):
                key = (a["id"], a.get("trial", 1))
                done_by_key[key] = a
        print(f"Resuming {args.system_id}: {len(done_by_key)}/{len(questions) * args.trials} already done.", flush=True)

    tasks = [(q, t) for q in questions for t in range(1, args.trials + 1)]
    todo = [(q, t) for (q, t) in tasks if (q["id"], t) not in done_by_key]
    print(
        f"Running {len(todo)} remaining tasks ({len(questions)} questions x {args.trials} trial(s)) "
        f"for {args.system_id} ({args.model}, effort={args.effort}, workers={args.workers})...",
        flush=True,
    )

    lock = threading.Lock()

    def save_checkpoint():
        all_done = [done_by_key[(q["id"], t)] for (q, t) in tasks if (q["id"], t) in done_by_key]
        traced = [a["timing"] for a in all_done if a.get("timing")]
        payload = {
            "system": {
                "name": args.name,
                "harness": "Vertesia Agent System",
                "harness_version": "sys:GeneralAgent",
                "model": args.model,
                "reasoning_effort": args.effort,
                "content_system": "Vertesia",
                "retrieval": "Vertesia index (built in)",
                "run_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "trials_per_question": args.trials,
                "ingestion": {
                    "no_human_categorization": args.no_human_cat,
                    "schema_mode": args.schema_mode,
                    "description": args.ingestion_desc,
                },
            },
            "answers": [
                done_by_key.get(
                    (q["id"], 1),
                    {"id": q["id"], "answer": "", "sources": [], "seconds": None, "input_tokens": None, "output_tokens": None},
                )
                for q in questions
            ],
        }
        if args.trials > 1:
            trials_list = [done_by_key[(q["id"], t)] for (q, t) in tasks if (q["id"], t) in done_by_key]
            by_q = {q["id"]: [done_by_key[(q["id"], t)] for t in range(1, args.trials + 1) if (q["id"], t) in done_by_key] for q in questions}
            payload["trials"] = trials_list
            payload["variance_summary"] = _summarize_trials(by_q)
        if traced:
            payload["timing_summary"] = {
                "n_traced": len(traced),
                "active_median_s": round(statistics.median(t["active_s"] for t in traced), 2),
                "llm_share_pct": round(100.0 * sum(t["llm_s"] for t in traced) / sum(t["active_s"] for t in traced), 1),
                "tool_share_pct": round(100.0 * sum(t["tool_wall_s"] for t in traced) / sum(t["active_s"] for t in traced), 1),
                "system_wait_share_pct": round(100.0 * sum(t["system_wait_s"] for t in traced) / sum(t["active_s"] for t in traced), 1),
            }
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, out_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {
            ex.submit(run_one_question, q, args.profile, args.env, args.model, args.inference_profile, args.time_limit): (q, t)
            for (q, t) in todo
        }
        completed = len(done_by_key)
        timeouts = sum(1 for v in done_by_key.values() if v.get("hit_time_limit"))
        total_tasks = len(tasks)
        for fut in concurrent.futures.as_completed(futs):
            q, trial = futs[fut]
            res = fut.result()
            if args.trials > 1:
                res["trial"] = trial
            with lock:
                done_by_key[(q["id"], trial)] = res
                completed += 1
                if res.get("hit_time_limit"):
                    timeouts += 1
                save_checkpoint()
                tag = "TIMEOUT" if res.get("hit_time_limit") else ("ERR" if res.get("error") else "OK")
                tm = res.get("timing") or {}
                tstr = f" llm={tm['llm_s']}s tool={tm['tool_wall_s']}s sys={tm['system_wait_s']}s({tm['system_wait_pct']}%)" if tm else ""
                trl = f"#t{trial}" if args.trials > 1 else ""
                print(
                    f"[{completed:3d}/{total_tasks}] {q['id']:4s}{trl:3s} {tag:7s} "
                    f"{res.get('seconds', 0):5.1f}s tools={str(res.get('tool_calls')):>3s} "
                    f"in={str(res.get('input_tokens')):>7s}{tstr}",
                    flush=True,
                )

    print(f"FINISHED {args.system_id}: {completed}/{total_tasks} done, {timeouts} timeouts -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
