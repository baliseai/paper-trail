# Paper Trail Benchmark Runbook (Self-Contained Launch Guide)

Use this runbook from any fresh terminal or OpenCode session in this repository to run, resume, and validate the full **150-question** Paper Trail v2.1 matrix.

> **Never commit `runs/` or any private gold-key files.** Both `runs/` and `*PRIVATE*` are in `.gitignore` so held-out answers cannot leak into git.

---

## 1. Benchmark Rules & Standard Settings

- **Questions:** 150 questions in `docs/data/questions.json` (`25` open, `125` held-out). Ask every question **verbatim** (typos included).
- **Updating a v2 run:** P48–P58 require fresh answers. Reuse answers for the 139 surviving IDs when the configuration and run conditions match. Preserve the original submission and use the current template for the updated run.
- **Reference date:** `Treat today as 23 November 2026.`
- **Standard effort:** **`medium`** across all models/harnesses for apples-to-apples comparison.
- **Web search:** **OFF** everywhere. Answer strictly from the 9,832-file library.
- **Hard timeout:** **600 seconds (10 minutes)** per question. One shot, no follow-up.
- **Ingestion rules:** Defining/editing document schemas ahead of evaluation (without tuning on questions/answers) is **allowed** (`schema_mode: "auto" | "human_authored"`). Setting/editing per-document metadata or manually categorizing/retyping documents by hand or in bulk is **not allowed** (`no_human_categorization: true`).

---

## 2. Track A · Vertesia Studio General Agent (`sys:GeneralAgent` via CLI)

`scripts/run_vertesia.py` is fully resumable: it checkpoints after every completed question into `./runs/<system-id>.json`. Re-running the same command automatically skips completed IDs.

Discover available environments and inference profiles first:

```bash
vertesia -p <PROFILE> envs
vertesia -p <PROFILE> inference-profiles list
```

### Standard `medium`-effort 150-question runs

```bash
# 1. GPT 6.2 Sol (medium is default)
python3 scripts/run_vertesia.py \
  --system-id studio-gpt-6.2-sol-medium-v2 \
  --name "Vertesia agent · GPT 6.2 Sol medium" \
  --profile <PROFILE> \
  --env <OPENAI_ENV_ID> --model gpt-6.2-sol --effort medium \
  --workers 5

# 2. Claude Opus 5.5 (medium is default)
python3 scripts/run_vertesia.py \
  --system-id studio-claude-opus-5.5-medium-v2 \
  --name "Vertesia agent · Claude Opus 5.5 medium" \
  --profile <PROFILE> \
  --env <BEDROCK_ENV_ID> \
  --model arn:aws:bedrock:us-east-1:<ACCOUNT_ID>:inference-profile/global.anthropic.claude-opus-5-5 \
  --effort medium --workers 4

# 3. Gemini 4 Neon (create an explicit medium-effort inference profile first!)
vertesia -p <PROFILE> inference-profiles create \
  '{"name":"Paper Trail Gemini 4 Neon Medium","environment":"<VERTEX_ENV_ID>","model":"locations/global/publishers/google/models/gemini-4-neon","model_options":{"effort":"medium"}}'

python3 scripts/run_vertesia.py \
  --system-id studio-gemini-4-neon-medium-v2 \
  --name "Vertesia agent · Gemini 4 Neon medium" \
  --profile <PROFILE> \
  --inference-profile <GEMINI_MEDIUM_PROFILE_ID> \
  --model locations/global/publishers/google/models/gemini-4-neon \
  --effort medium --workers 3
```

Quick smoke test on 6 representative v2 tasks (`--ids`):

```bash
python3 scripts/run_vertesia.py \
  --system-id smoke-test \
  --name "Smoke test" \
  --profile <PROFILE> --env <OPENAI_ENV_ID> --model gpt-6.2-sol --effort medium \
  --ids P6,P7,P15,P18,P38,P42 --workers 4
```

---

## 3. Track B & C · Web Assistants (Browser Automation)

Always isolate each run in a **dedicated Project folder** (or `Temporary chat` in Copilot Chat) so all 150 chats can be archived or deleted in one click.

Standard project instructions for ChatGPT & Claude.ai:

> `Web search is turned off for this organization. Do not use web search or web fetch, and do not download anything from the internet. Treat today as 23 November 2026. Answer from the organization's content available through the connected tools.`

### Matrix to run (`medium` effort everywhere)
1. **ChatGPT (`6.2 Medium`)**
   - `SharePoint alone`: Project `Paper Trail v2 – ChatGPT (SharePoint)` — prefix prompts with the SharePoint connector mention (or select SharePoint app). Pace at **1–2 concurrent tabs** so SharePoint Graph API is not artificially HTTP 429 rate-limited.
   - `SharePoint + Vertesia`: Project `Paper Trail v2 – ChatGPT (+Vertesia)` — connect Vertesia MCP/app.
   - *Metrics to capture:* `answer`, `Worked for Xs` (`seconds`), model label (`6.2 Medium`), cited SharePoint links, any HTTP 429 errors.
2. **Claude.ai (`Opus 5.5 Medium`)**
   - `SharePoint alone`: Project `Paper Trail v2 – Claude (SharePoint)` — Microsoft 365 connector ON, Vertesia connector OFF, Web search OFF.
   - `SharePoint + Vertesia`: Project `Paper Trail v2 – Claude (+Vertesia)` — Vertesia connector ON, Web search OFF.
   - *Metrics to capture:* `answer`, elapsed `seconds`, model/effort (`Opus 5.5 Medium`), cited sources.
3. **Microsoft 365 Copilot** *(run on a **clean dedicated M365 test account** with only the 9,832 library files and zero personal emails/unrelated SharePoint demos)*
   - `Copilot (Chat) alone` (`Work IQ` ON, `Auto`, Web search OFF): use **`Temporary chat`** (zero sidebar clutter; 4–6 parallel tabs). **Important:** delete any `.xlsx` spreadsheets generated into OneDrive by spreadsheet tasks (`T1`, `T6`) immediately so they cannot contaminate later questions!
   - `Copilot (Cowork) alone` (`Auto` or `GPT 6.2 Sol`, `Medium`): ensure the Vertesia plugin is **disconnected/removed** so tasks don't fail on a stale plugin card.
   - `Copilot (Cowork) + Vertesia` (and `Chat + Vertesia` if enabled): reconnect the Vertesia plugin.

---

## 4. Track D · Any other system (`run_custom.py`)

Write an adapter (`scripts/adapters/example_adapter.py` is the starting point) or point `--command` at any program
that reads one question as JSON on stdin and prints the answer. Same rules: one fresh process per question, 600 s cap,
checkpoint after each answer, rerun to resume.

```bash
python3 scripts/run_custom.py --system-id my-system --adapter scripts/adapters/my_adapter.py --split open
python3 scripts/grade_open.py runs/my-system.json --judge anthropic:claude-opus-5-5 --judge openai:gpt-6.2-sol
python3 scripts/run_custom.py --system-id my-system --adapter scripts/adapters/my_adapter.py --workers 4
```

`grade_open.py` grades only the 25 open questions, as an estimate. It does not replace held-out grading.

---

## 5. Validate, Grade & Rebuild Artifacts

1. **Validate every run JSON** (checks schema, all 150 IDs, 600s limit, source paths, and prints the 25 open questions side-by-side with gold answers):

   ```bash
   python3 scripts/validate_submission.py runs/<system-id>.json --check-open
   ```

2. **Rebuild raw-only `data/documents.parquet`** (only needed if the corpus manifest changes; ships raw metadata & `nasa.gov` URLs with no extracted text or pre-assigned types):

   ```bash
   python3 scripts/build_raw_documents_manifest.py
   ```

3. **Download & verify the raw 9,832-file library** (from `nasa.gov`, with percent-encoding and SHA-256 checks):

   ```bash
   python3 scripts/download_documents.py --out ./library
   ```
