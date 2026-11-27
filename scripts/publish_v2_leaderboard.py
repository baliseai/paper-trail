#!/usr/bin/env python3
"""Build public docs/data/leaderboard-v2.json from private 150-question graded scorecards.

Never reads or publishes held-out answers or per-question held-out grades—only aggregate metrics
from `<private>/grades/*.public.json` and latency/token summaries from `<private>/runs/*.json`.
"""
import glob
import json
import os
import statistics
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE = os.path.join(os.path.dirname(ROOT), "paper-trail-private")
QUESTIONS_PATH = os.path.join(ROOT, "docs", "data", "questions.json")
OUT_PATH = os.path.join(ROOT, "docs", "data", "leaderboard-v2.json")

MODEL_LABELS = {
    "locations/global/publishers/xai/models/grok-4.7": "Grok 4.7",
    "mistralai/mistral-large-4-0": "Mistral Large 4.0",
    "gpt-6.2-sol": "GPT 6.2 Sol",
    "gpt-6.2-astra": "GPT 6.2 Astra",
    "arn:aws:bedrock:us-east-1:381492301031:inference-profile/global.anthropic.claude-opus-5-5": "Claude Opus 5.5",
    "arn:aws:bedrock:us-east-1:381492301031:inference-profile/global.anthropic.claude-sonnet-5-5": "Claude Sonnet 5.5",
    "locations/global/publishers/anthropic/models/claude-fable-5-2": "Claude Fable 5.2",
    "locations/global/publishers/google/models/gemini-4-neon": "Gemini 4 Neon",
    "qwen/qwen4-max": "Qwen 4 Max",
    "moonshotai/kimi-k3": "Kimi K3",
    "deepseek/deepseek-v4.1-flash": "DeepSeek V4.1 Flash",
}


def p90(vals):
    if not vals:
        return None
    s = sorted(vals)
    return round(s[min(len(s) - 1, int(0.9 * len(s)))], 1)


def main():
    qs = json.load(open(QUESTIONS_PATH, "r", encoding="utf-8"))
    kinds = {
        "1": "Find a document or a fact",
        "2": "Read a clause",
        "3": "Count, list or total",
        "4": "Across libraries",
        "5": "Find, then act",
    }
    open_ids = [q["id"] for q in qs if q.get("split") == "open"]
    hardcore_ids = [q["id"] for q in qs if q.get("hardcore")]

    systems = []
    for gpath in sorted(glob.glob(os.path.join(PRIVATE, "grades", "*.public.json"))):
        g = json.load(open(gpath, "r", encoding="utf-8"))
        summ = g.get("summary") or {}
        if summ.get("n_graded") != len(qs):
            continue  # only full 150-question runs enter the v2.1 leaderboard

        stem = os.path.basename(gpath).replace(".public.json", "")
        rpath = os.path.join(PRIVATE, "runs", f"{stem}.json")
        run = json.load(open(rpath, "r", encoding="utf-8")) if os.path.exists(rpath) else {}
        sys_meta = g.get("system") or run.get("system") or {}
        answers = run.get("answers", [])

        secs = [a["seconds"] for a in answers if a.get("seconds") is not None and not a.get("hit_time_limit")]
        in_toks = [a["input_tokens"] for a in answers if a.get("input_tokens") is not None]
        ca_toks = [a["cached_input_tokens"] for a in answers if a.get("cached_input_tokens") is not None]
        out_toks = [a["output_tokens"] for a in answers if a.get("output_tokens") is not None]
        tools = [a["tool_calls"] for a in answers if a.get("tool_calls") is not None]
        steps = [a["llm_calls"] for a in answers if a.get("llm_calls") is not None]
        timeouts = sum(1 for a in answers if a.get("hit_time_limit"))

        raw_model = sys_meta.get("model") or ""
        model_label = MODEL_LABELS.get(raw_model, raw_model)
        effort = sys_meta.get("reasoning_effort") or "medium"
        harness_raw = sys_meta.get("harness") or "Vertesia Agent System"
        harness_label = "Vertesia Agent System" if "vertesia" in harness_raw.lower() else harness_raw
        cs = sys_meta.get("content_system") or "Vertesia"

        systems.append({
            "id": stem,
            "name": f"{harness_label} · {model_label} {effort}".strip(),
            "assistant": harness_label,
            "harness": harness_label,
            "harness_label": harness_label,
            "harness_detail": "",
            "content_system": cs,
            "retrieval": sys_meta.get("retrieval") or cs,
            "model": f"{model_label}, {effort}" if effort else model_label,
            "model_name": model_label,
            "model_label": model_label,
            "reasoning_effort": effort,
            "model_detail": f"{effort} effort" if effort else "",
            "correct": summ["correct"],
            "partial": summ["partial"],
            "wrong": summ["wrong"],
            "no_answer": summ["no_answer"],
            "score": summ["score"],
            "score_wrong_minus1": summ["strict"],
            "by_kind": summ["by_kind"],
            "hardcore": summ.get("hardcore_score") or 0.0,
            "open_split": summ.get("open_score") or 0.0,
            "held_out": summ.get("held_out_score") or 0.0,
            "median_s": round(statistics.median(secs)) if secs else None,
            "p90_s": round(p90(secs)) if secs else None,
            "input_tokens_per_q": round(statistics.mean(in_toks)) if in_toks else None,
            "cached_input_per_q": round(statistics.mean(ca_toks)) if ca_toks else None,
            "output_tokens_per_q": round(statistics.mean(out_toks)) if out_toks else None,
            "tool_calls_mean": round(statistics.mean(tools), 1) if tools else None,
            "steps_mean": round(statistics.mean(steps), 1) if steps else None,
            "timeouts": timeouts,
        })

    # Compute aggregate difficulty histogram (number of questions solved by k of N systems) without exposing held-out IDs
    solved_counts = {q["id"]: 0 for q in qs}
    for gpath in sorted(glob.glob(os.path.join(PRIVATE, "grades", "*.private.json"))):
        gp = json.load(open(gpath, "r", encoding="utf-8"))
        if (gp.get("summary") or {}).get("n_graded") != len(qs):
            continue
        for item in gp.get("grades", []):
            if item.get("grade") == "correct" and item.get("id") in solved_counts:
                solved_counts[item["id"]] += 1
    hist = [0] * (len(systems) + 1)
    for c in solved_counts.values():
        if 0 <= c <= len(systems):
            hist[c] += 1

    systems.sort(key=lambda s: (-s["score"], -s["correct"], s["wrong"]))
    payload = {
        "version": "v2.1",
        "n_questions": len(qs),
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "n_systems": len(systems),
        "hardcore_ids": hardcore_ids,
        "open_ids": open_ids,
        "kinds": kinds,
        "kind_counts": {str(k): sum(1 for q in qs if q.get("kind") == k) for k in range(1, 6)},
        "systems": systems,
        "difficulty_histogram": hist,
    }
    json.dump(payload, open(OUT_PATH, "w", encoding="utf-8"), indent=1)
    print(f"Wrote {OUT_PATH}: {len(systems)} full 150-question systems")
    for s in systems:
        print(f"  {s['name']:44s} | score={s['score']:5.1f} strict={s['score_wrong_minus1']:5.1f} | {s['correct']}/{s['partial']}/{s['wrong']}/{s['no_answer']} | med={s['median_s']}s")


if __name__ == "__main__":
    main()
