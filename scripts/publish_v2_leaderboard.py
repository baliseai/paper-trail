#!/usr/bin/env python3
"""Build public docs/data/leaderboard-v2.json from private 150-question graded scorecards.

Prefers human-reviewed `*.reviewed.json` when available; falls back to `*.public.json`.
Never publishes held-out answers or per-question held-out grades—only aggregate scores,
5-kind breakdowns, latency/token stats, and anonymous aggregate difficulty counts.
"""
import glob
import json
import os
import statistics
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE = os.path.join(os.path.dirname(ROOT), "paper-trail-private")
QUESTIONS_PATH = os.path.join(ROOT, "docs", "data", "questions.json")
OUT_PATH = os.path.join(ROOT, "docs", "data", "leaderboard.json")

MODEL_LABELS = {
    "locations/global/publishers/xai/models/grok-4.7": "Grok 4.7",
    "mistralai/mistral-large-4-0": "Mistral Large 4.0",
    "gpt-6.2-sol": "GPT 6.2 Sol",
    "gpt-6.2-astra": "GPT 6.2 Astra",
    "GPT 6.2": "GPT 6.2",
    "gpt-6.2": "GPT 6.2",
    "arn:aws:bedrock:us-east-1:381492301031:inference-profile/global.anthropic.claude-opus-5-5": "Claude Opus 5.5",
    "arn:aws:bedrock:us-east-1:381492301031:inference-profile/global.anthropic.claude-sonnet-5-5": "Claude Sonnet 5.5",
    "locations/global/publishers/anthropic/models/claude-fable-5-2": "Claude Fable 5.2",
    "locations/global/publishers/google/models/gemini-4-neon": "Gemini 4 Neon",
    "locations/global/publishers/google/models/gemini-4-argon": "Gemini 4 Argon",
    "qwen/qwen4-max": "Qwen 4 Max",
    "moonshotai/kimi-k3": "Kimi K3",
    "deepseek/deepseek-v4.1-flash": "DeepSeek V4.1 Flash",
}

PTS = {"correct": 1.0, "partial": 0.5, "wrong": 0.0, "no_answer": 0.0, "none": 0.0}
STRICT_PTS = {"correct": 1.0, "partial": 0.5, "wrong": -1.0, "no_answer": 0.0, "none": 0.0}


def p90(vals):
    if not vals:
        return None
    s = sorted(vals)
    return round(s[min(len(s) - 1, int(0.9 * len(s)))], 1)


def _norm_meta(stem, sys_meta):
    raw_model = sys_meta.get("model") or ""
    model_label = MODEL_LABELS.get(raw_model, raw_model)
    effort = sys_meta.get("reasoning_effort") or "medium"
    harness_raw = sys_meta.get("harness") or ""
    if stem.startswith("chatgpt-"):
        harness_label = "ChatGPT"
        model_label = model_label or "GPT 6.2"
        cs = sys_meta.get("content_system") or ("SharePoint + Vertesia index" if "vertesia" in stem else "SharePoint")
    elif stem.startswith("claude-"):
        harness_label = "Claude.ai"
        model_label = model_label or "Claude Opus 5.5"
        cs = sys_meta.get("content_system") or ("SharePoint + Vertesia index" if "vertesia" in stem else "SharePoint")
    elif stem.startswith("copilot-"):
        harness_label = "Microsoft 365 Copilot"
        model_label = model_label or "GPT (Auto)"
        cs = sys_meta.get("content_system") or ("SharePoint + Vertesia index" if "vertesia" in stem else "SharePoint")
    else:
        harness_label = "Vertesia Agent System" if (not harness_raw or "vertesia" in harness_raw.lower()) else harness_raw
        cs = sys_meta.get("content_system") or "Vertesia"
    if "gpt-6.2" in model_label.lower() and "composer" in model_label.lower():
        model_label = "GPT 6.2"
    if cs.lower() in ("sharepoint + vertesia", "sharepoint + vertesia index"):
        cs = "SharePoint + Vertesia index"
    return harness_label, model_label, effort, cs


def main():
    qs = json.load(open(QUESTIONS_PATH, "r", encoding="utf-8"))
    n_q = len(qs)
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
    solved_counts = {q["id"]: 0 for q in qs}

    for pub_path in sorted(glob.glob(os.path.join(PRIVATE, "grades", "*.public.json"))):
        stem = os.path.basename(pub_path).replace(".public.json", "")
        pub = json.load(open(pub_path, "r", encoding="utf-8"))
        rev_path = pub_path.replace(".public.json", ".reviewed.json")
        priv_path = pub_path.replace(".public.json", ".private.json")

        has_rev = os.path.exists(rev_path)
        if has_rev:
            rev = json.load(open(rev_path, "r", encoding="utf-8"))
            if rev.get("n") != n_q:
                continue
            grades_list = rev.get("grades") or []
            c = sum(1 for x in grades_list if x.get("final") == "correct")
            pa = sum(1 for x in grades_list if x.get("final") == "partial")
            w = sum(1 for x in grades_list if x.get("final") == "wrong")
            na = sum(1 for x in grades_list if x.get("final") in ("no_answer", "none"))
            score = round(100.0 * sum(PTS.get(x.get("final"), 0.0) for x in grades_list) / n_q, 1)
            strict = round(100.0 * sum(STRICT_PTS.get(x.get("final"), 0.0) for x in grades_list) / n_q, 1)
            by_kind = rev.get("by_kind") or {}
            hardcore = rev.get("hardcore_score") or 0.0
            open_items = [x for x in grades_list if x.get("split") == "open"]
            held_items = [x for x in grades_list if x.get("split") != "open"]
            open_score = round(100.0 * sum(PTS.get(x.get("final"), 0.0) for x in open_items) / len(open_items), 1) if open_items else 0.0
            held_score = round(100.0 * sum(PTS.get(x.get("final"), 0.0) for x in held_items) / len(held_items), 1) if held_items else 0.0
            for x in grades_list:
                if x.get("final") == "correct" and x.get("id") in solved_counts:
                    solved_counts[x["id"]] += 1
        else:
            summ = pub.get("summary") or {}
            if summ.get("n_graded") != n_q:
                continue
            c, pa, w, na = summ["correct"], summ["partial"], summ["wrong"], summ["no_answer"]
            score, strict = summ["score"], summ["strict"]
            by_kind = summ["by_kind"]
            hardcore = summ.get("hardcore_score") or 0.0
            open_score = summ.get("open_score") or 0.0
            held_score = summ.get("held_out_score") or 0.0
            if os.path.exists(priv_path):
                gp = json.load(open(priv_path, "r", encoding="utf-8"))
                for x in gp.get("grades", []):
                    if x.get("grade") == "correct" and x.get("id") in solved_counts:
                        solved_counts[x["id"]] += 1

        rpath = os.path.join(PRIVATE, "runs", f"{stem}.json")
        run = json.load(open(rpath, "r", encoding="utf-8")) if os.path.exists(rpath) else {}
        sys_meta = pub.get("system") or run.get("system") or {}
        answers = run.get("answers", [])

        secs = [a["seconds"] for a in answers if a.get("seconds") is not None and not a.get("hit_time_limit")]
        in_toks = [a["input_tokens"] for a in answers if a.get("input_tokens") is not None]
        ca_toks = [a["cached_input_tokens"] for a in answers if a.get("cached_input_tokens") is not None]
        out_toks = [a["output_tokens"] for a in answers if a.get("output_tokens") is not None]
        tools = [a["tool_calls"] for a in answers if a.get("tool_calls") is not None]
        steps = [a["llm_calls"] for a in answers if a.get("llm_calls") is not None]
        timeouts = sum(1 for a in answers if a.get("hit_time_limit"))

        harness_label, model_label, effort, cs = _norm_meta(stem, sys_meta)

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
            "correct": c,
            "partial": pa,
            "wrong": w,
            "no_answer": na,
            "score": score,
            "score_wrong_minus1": strict,
            "by_kind": by_kind,
            "hardcore": hardcore,
            "open_split": open_score,
            "held_out": held_score,
            "median_s": round(statistics.median(secs)) if secs else None,
            "p90_s": round(p90(secs)) if secs else None,
            "input_tokens_per_q": round(statistics.mean(in_toks)) if in_toks else None,
            "cached_input_per_q": round(statistics.mean(ca_toks)) if ca_toks else None,
            "output_tokens_per_q": round(statistics.mean(out_toks)) if out_toks else None,
            "tool_calls_mean": round(statistics.mean(tools), 1) if tools else None,
            "steps_mean": round(statistics.mean(steps), 1) if steps else None,
            "timeouts": timeouts,
            "reviewed": has_rev,
        })

    hist = [0] * (len(systems) + 1)
    for cnt in solved_counts.values():
        if 0 <= cnt <= len(systems):
            hist[cnt] += 1

    systems.sort(key=lambda s: (-s["score"], -s["correct"], s["wrong"]))
    payload = {
        "version": "v2.1",
        "n_questions": n_q,
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
        tag = "REV" if s["reviewed"] else "RAW"
        print(f"  [{tag}] {s['harness_label']:21s} | {s['content_system']:27s} | {s['model_label']:18s} | {s['score']:5.1f} (strict {s['score_wrong_minus1']:5.1f}) | {s['correct']:3d}/{s['partial']:2d}/{s['wrong']:2d}/{s['no_answer']:2d} | med={str(s['median_s']):>4s}s")


if __name__ == "__main__":
    main()
