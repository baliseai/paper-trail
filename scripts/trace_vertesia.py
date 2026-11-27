#!/usr/bin/env python3
"""Extract inference, tool execution, queue wait, and workflow gap timings from Vertesia agent runs.

Can be used either as a library (imported by scripts/run_vertesia.py) or as a CLI tool to
retroactively enrich and summarize any existing Paper Trail run JSON (`runs/studio-*.json`).

Example:
    python scripts/trace_vertesia.py --profile <PROFILE> runs/studio-gpt-6.2-sol-medium-v2.json
    python scripts/trace_vertesia.py --profile <PROFILE> --save runs/studio-gemini-4-neon-medium-v2.json
"""
import argparse
import concurrent.futures
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime


def _ts(iso_str):
    if not iso_str:
        return None
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()


def _merge_intervals(intervals):
    if not intervals:
        return 0.0
    iv = sorted(intervals)
    merged = [list(iv[0])]
    for start, end in iv[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum(end - start for start, end in merged)


def extract_timing_breakdown(inspect_json):
    """Compute millisecond-level timing breakdown from `vertesia agents inspect --details --json`.

    Returns a dict with:
      - startup_s: workflow start -> user prompt delivered
      - active_s: user prompt delivered -> last completed LLM/tool task
      - llm_s: merged wall time in LLM inference activities (`taskType == "llm_call"`)
      - llm_calls_traced: count of completed LLM inference activities
      - tool_wall_s: merged wall time in tool activities (`taskType == "tool_call"`, accounts for parallelism)
      - tool_sum_s: raw sum of tool activity durations
      - tool_calls_traced: count of completed tool activities
      - queue_wait_s: sum of Temporal activity queue wait (`started_at - scheduled_at`)
      - orchestration_gap_s: residual inter-turn gap (`active_s - busy_s - queue_wait_s`)
      - system_wait_s: `queue_wait_s + orchestration_gap_s` (total non-LLM, non-tool wait during active turn)
      - system_wait_pct: percentage of `active_s` spent in system wait
      - per_tool_s: {tool_name: {"calls": n, "sum_s": x, "max_s": y}}
    """
    if not inspect_json:
        return None
    details = inspect_json.get("details") or {}
    history = details.get("history") or {}
    tasks = history.get("agentTasks") or []
    if not tasks:
        return None

    u_idx = next((i for i, t in enumerate(tasks) if t.get("taskType") == "input"), None)
    if u_idx is None:
        return None

    u_t = _ts(tasks[u_idx].get("started_at"))
    wf_start = _ts(details.get("started_at"))
    startup_s = round(max(0.0, u_t - wf_start), 2) if (u_t and wf_start) else None

    active_tasks = [
        t for t in tasks[u_idx + 1 :]
        if t.get("taskType") in ("llm_call", "tool_call") and t.get("started_at") and t.get("completed_at")
    ]
    if not active_tasks or u_t is None:
        return None

    end_t = max(_ts(t["completed_at"]) for t in active_tasks)
    active_s = max(0.001, end_t - u_t)

    llm_iv = [(_ts(t["started_at"]), _ts(t["completed_at"])) for t in active_tasks if t["taskType"] == "llm_call"]
    tool_iv = [(_ts(t["started_at"]), _ts(t["completed_at"])) for t in active_tasks if t["taskType"] == "tool_call"]

    llm_s = _merge_intervals(llm_iv)
    tool_wall_s = _merge_intervals(tool_iv)
    tool_sum_s = sum(b - a for a, b in tool_iv)
    busy_s = _merge_intervals(llm_iv + tool_iv)

    queue_wait_s = 0.0
    for t in active_tasks:
        sc, st = _ts(t.get("scheduled_at")), _ts(t.get("started_at"))
        if sc is not None and st is not None and st > sc:
            queue_wait_s += st - sc

    orchestration_gap_s = max(0.0, active_s - busy_s - queue_wait_s)
    system_wait_s = queue_wait_s + orchestration_gap_s

    per_tool = defaultdict(lambda: {"calls": 0, "sum_s": 0.0, "max_s": 0.0})
    for t in active_tasks:
        if t["taskType"] == "tool_call":
            name = t.get("toolName") or "unknown"
            dur = max(0.0, _ts(t["completed_at"]) - _ts(t["started_at"]))
            rec = per_tool[name]
            rec["calls"] += 1
            rec["sum_s"] += dur
            rec["max_s"] = max(rec["max_s"], dur)

    per_tool_clean = {
        k: {"calls": v["calls"], "sum_s": round(v["sum_s"], 2), "max_s": round(v["max_s"], 2)}
        for k, v in sorted(per_tool.items(), key=lambda kv: -kv[1]["sum_s"])
    }

    return {
        "startup_s": startup_s,
        "active_s": round(active_s, 2),
        "llm_s": round(llm_s, 2),
        "llm_pct": round(100.0 * llm_s / active_s, 1),
        "llm_calls_traced": len(llm_iv),
        "tool_wall_s": round(tool_wall_s, 2),
        "tool_sum_s": round(tool_sum_s, 2),
        "tool_pct": round(100.0 * tool_wall_s / active_s, 1),
        "tool_calls_traced": len(tool_iv),
        "queue_wait_s": round(queue_wait_s, 2),
        "orchestration_gap_s": round(orchestration_gap_s, 2),
        "system_wait_s": round(system_wait_s, 2),
        "system_wait_pct": round(100.0 * system_wait_s / active_s, 1),
        "per_tool_s": per_tool_clean,
    }


def fetch_timing(profile, run_id, timeout=45):
    out = subprocess.check_output(
        ["vertesia", "-p", profile, "agents", "inspect", run_id, "--details", "--json"],
        text=True,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return extract_timing_breakdown(json.loads(out))


def summarize_timings(timings, label=""):
    if not timings:
        print(f"{label}: no traced runs")
        return {}
    def med(k): return round(statistics.median([t[k] for t in timings if t.get(k) is not None]), 2)
    def mean(k): return round(statistics.mean([t[k] for t in timings if t.get(k) is not None]), 2)
    def p90(k):
        vals = sorted(t[k] for t in timings if t.get(k) is not None)
        return round(vals[min(len(vals) - 1, int(0.9 * len(vals)))], 2)

    tot_active = sum(t["active_s"] for t in timings)
    tot_llm = sum(t["llm_s"] for t in timings)
    tot_tool = sum(t["tool_wall_s"] for t in timings)
    tot_queue = sum(t["queue_wait_s"] for t in timings)
    tot_gap = sum(t["orchestration_gap_s"] for t in timings)
    tot_sys = tot_queue + tot_gap

    summary = {
        "n_traced": len(timings),
        "active_median_s": med("active_s"),
        "active_mean_s": mean("active_s"),
        "active_p90_s": p90("active_s"),
        "startup_median_s": med("startup_s"),
        "llm_share_pct": round(100.0 * tot_llm / tot_active, 1),
        "tool_share_pct": round(100.0 * tot_tool / tot_active, 1),
        "queue_share_pct": round(100.0 * tot_queue / tot_active, 1),
        "gap_share_pct": round(100.0 * tot_gap / tot_active, 1),
        "system_wait_share_pct": round(100.0 * tot_sys / tot_active, 1),
        "llm_median_s": med("llm_s"),
        "tool_median_s": med("tool_wall_s"),
        "queue_p90_s": p90("queue_wait_s"),
        "gap_p90_s": p90("orchestration_gap_s"),
        "system_wait_median_s": med("system_wait_s"),
        "system_wait_p90_s": p90("system_wait_s"),
    }
    print(
        f"{label} (n={len(timings)}): "
        f"active med={summary['active_median_s']}s p90={summary['active_p90_s']}s | "
        f"LLM={summary['llm_share_pct']}% | Tool={summary['tool_share_pct']}% | "
        f"SystemWait={summary['system_wait_share_pct']}% "
        f"(queue={summary['queue_share_pct']}% p90={summary['queue_p90_s']}s, "
        f"gap={summary['gap_share_pct']}% p90={summary['gap_p90_s']}s) | "
        f"startup med={summary['startup_median_s']}s"
    )
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="One or more Paper Trail run JSON files")
    ap.add_argument("--profile", required=True, help="Vertesia CLI profile name")
    ap.add_argument("--workers", type=int, default=6, help="Concurrent inspect requests (default: 6)")
    ap.add_argument("--limit", type=int, default=None, help="Optional limit on number of runs to trace per file")
    ap.add_argument("--save", action="store_true", help="Write `timing` fields back into the JSON files")
    ap.add_argument("--force", action="store_true", help="Re-fetch timing even if already present")
    args = ap.parse_args()

    for path in args.files:
        data = json.load(open(path, "r", encoding="utf-8"))
        answers = data.get("answers", [])
        targets = [a for a in answers if a.get("run_id") and (args.force or not a.get("timing"))]
        if args.limit is not None:
            targets = targets[: args.limit]

        if targets:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
                futs = {ex.submit(fetch_timing, args.profile, a["run_id"]): a for a in targets}
                for fut in concurrent.futures.as_completed(futs):
                    a = futs[fut]
                    try:
                        t = fut.result()
                        if t:
                            a["timing"] = t
                    except Exception as e:
                        print(f"  WARN {a['id']} ({a['run_id']}): {e}", file=sys.stderr)

        traced = [a["timing"] for a in answers if a.get("timing")]
        summary = summarize_timings(traced, label=path)
        if args.save:
            data["timing_summary"] = summary
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            import os
            os.replace(tmp, path)


if __name__ == "__main__":
    main()
