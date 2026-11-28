# Paper Trail: Benchmarking Models, Harnesses, and Content Systems on Enterprise Documents

**[Website](https://baliseresearch.com/paper-trail/) · [Dataset on Hugging Face](https://huggingface.co/datasets/baliseai/paper-trail) · [Leaderboard](#leaderboard) · [Submit a system](#submitting-results)**

Paper Trail asks **150 work questions over 9,832 enterprise documents**: partnership agreements, procurement
contracts, audits, directives, technical reports and old backups. Tasks range from finding a clause to listing all
agreements that meet a condition. The files are public NASA records, so anyone can rebuild the library, and the
reference answers come from the documents themselves.

Each result reports the model, the harness that ran it, and the content system it searched.

**Funding and conflicts.** Paper Trail is built and published by Balise, Inc. Vertesia's document index or agent
appears in every row except the assistants running alone on SharePoint, and Vertesia pays for its own runs. All rows
were run by Balise. Outside submissions are graded with the same rubric grader.

For the submission format and run rules, see
[Submitting results](#submitting-results).

- **Version:** v2.1 (150 questions over 9,832 public NASA documents).
- **Changes in v2.1:** P48–P58 replace M2, M33, M37, M44, M52, M53, Q8, Q10, N3, N7, and P1.
  These prompts had answers in previously published material. The [eight former open examples](docs/data/archived-open-examples.json) remain available for practice.
  Existing runs need fresh answers for P48–P58. The leaderboard below is on all 150 v2.1 questions.
- **Reference date:** treat today as **23 November 2026** ("next quarter" is January–March 2027).
- **Held-out set:** 25 open questions (5 per kind) publish their answer and source files; the other 125 keep their
  answers private so scores stay comparable.
- **Raw manifest only:** `data/documents.parquet` ships only raw file metadata and `nasa.gov` URLs (no extracted text
  and no pre-assigned document types); every system under test must ingest and process the raw files itself.

## Leaderboard

Scores out of 100 on all 150 questions of v2.1 (correct = 1, partial = 0.5, wrong and no answer = 0), graded with the
rubric grader described in [GRADING.md](GRADING.md). Strict also takes a point off for each wrong answer.
C / P / W / N = correct / partial / wrong / no answer. Tokens are means per question; we report tokens, not prices.

<!-- leaderboard:start -->
| # | Harness | Model | Effort | Content system | Score | Strict | Hardest 11 | Held-out 125 | C / P / W / N | Median s | Input tokens / q | Output tokens / q |
|--:|---|---|:-:|---|--:|--:|--:|--:|:-:|--:|--:|--:|
| 1 | Vertesia Agent System | Gemini 4 Neon | medium | Vertesia | 97.3 | 97.3 | 86.4 | 96.8 | 143 / 6 / 0 / 1 | 175 | 493K | 13K |
| 2 | Vertesia Agent System | Claude Opus 5.5 | medium | Vertesia | 97.0 | 96.3 | 86.4 | 96.8 | 142 / 7 / 1 / 0 | 69 | 430K | 5.7K |
| 3 | Vertesia Agent System | Claude Fable 5.2 | medium | Vertesia | 96.7 | 96.7 | 86.4 | 96.4 | 140 / 10 / 0 / 0 | 94 | 434K | 9.4K |
| 4 | Vertesia Agent System | Mistral Large 4.0 | medium | Vertesia | 95.0 | 94.3 | 81.8 | 94.4 | 136 / 13 / 1 / 0 | 170 | 852K | 14K |
| 4 | Claude.ai | Claude Opus 5.5 | medium | SharePoint + Vertesia index | 95.0 | 94.3 | 86.4 | 95.6 | 136 / 13 / 1 / 0 | 68 | — | — |
| 6 | Vertesia Agent System | Gemini 4 Argon | medium | Vertesia | 93.7 | 89.7 | 81.8 | 93.6 | 137 / 7 / 6 / 0 | 255 | 1752K | 14K |
| 7 | Vertesia Agent System | GPT 6.2 Astra | medium | Vertesia | 93.3 | 91.3 | 77.3 | 93.2 | 133 / 14 / 3 / 0 | 67 | 262K | 2.0K |
| 8 | Vertesia Agent System | Grok 4.7 | medium | Vertesia | 91.7 | 88.3 | 77.3 | 92.0 | 130 / 15 / 5 / 0 | 94 | 733K | 5.9K |
| 9 | Vertesia Agent System | GPT 6.2 Sol | medium | Vertesia | 91.3 | 87.3 | 77.3 | 90.0 | 130 / 14 / 6 / 0 | 83 | 412K | 3.5K |
| 10 | Vertesia Agent System | Claude Sonnet 5.5 | medium | Vertesia | 91.0 | 89.0 | 77.3 | 90.4 | 128 / 17 / 3 / 2 | 44 | 324K | 4.1K |
| 11 | ChatGPT | GPT 6.2 | medium | SharePoint + Vertesia index | 89.0 | 85.7 | 77.3 | 88.4 | 122 / 23 / 5 / 0 | 29 | — | — |
| 12 | Microsoft 365 Copilot Cowork | Auto | — | SharePoint + Vertesia index | 83.0 | 76.3 | 63.6 | 84.0 | 115 / 19 / 10 / 6 | 76 | — | — |
| 13 | Microsoft 365 Copilot Chat | Auto | — | SharePoint + Vertesia index | 75.3 | 60.7 | 45.5 | 76.8 | 100 / 26 / 22 / 2 | 50 | — | — |
| 14 | Claude.ai | Claude Opus 5.5 | medium | SharePoint | 59.7 | 40.3 | 40.9 | 58.0 | 76 / 27 / 29 / 18 | 56 | — | — |
| 15 | ChatGPT | GPT 6.2 | medium | SharePoint | 56.7 | 30.7 | 45.5 | 56.4 | 70 / 30 / 39 / 11 | 35 | — | — |
| 16 | Microsoft 365 Copilot Chat | Auto | — | SharePoint | 51.7 | 21.7 | 31.8 | 52.4 | 64 / 27 / 45 / 14 | 32 | — | — |
| 17 | Microsoft 365 Copilot Cowork | Auto | — | SharePoint | 13.7 | -6.3 | 9.1 | 11.6 | 11 / 19 / 30 / 90 | 23 | — | — |
<!-- leaderboard:end -->

**How to read the rows.** Each row is one harness running one model over one content system:

- **Vertesia Agent System** (content system: Vertesia): Vertesia's general-purpose agent with read-only tools. The
  documents are stored in Vertesia, which converts, types and indexes them, and the agent searches them there. Only
  the model changes between these rows, all at medium effort.
- **+ Vertesia index** (content system: SharePoint + Vertesia index): the harness is an assistant (Claude.ai, ChatGPT
  or Microsoft 365 Copilot) and the documents stay in a SharePoint library. The assistant keeps its own SharePoint
  search and also gets a search tool over Vertesia's index of the same library, the index the agent rows use.
- **Alone** (content system: SharePoint): the same assistants with only their own SharePoint search.

**Run conditions.**

- One run per question for every system.
- Time limit per question: one hour for the Vertesia agent rows, 600 seconds for the assistants. Two Copilot Cowork
  answers without the index ran past 600 seconds (724 and 858) and were kept.
- Copilot's model is `Auto`: Copilot picks the model and does not say which one answered.
- Copilot Chat + Vertesia: the Vertesia search skill was attached by hand in every chat; without it Copilot did not
  call Vertesia. Copilot used Vertesia in 133 of the 150 answers. Copilot Cowork + Vertesia used Vertesia in 140 of
  the 150.
- Copilot Cowork alone gave no answer on 112 of the 150 questions because its file search found nothing.
- In the Claude.ai and ChatGPT rows, at most nine answers per row are second attempts: the first attempt had read an
  output file an earlier run left in the library, or stopped at a connector sign-in.
- A configuration is listed once all 150 of its answers are graded; the others are added when their grading ends.

The assistants do not report token use, so their rows show none. Per-question grades are published for the 25 open
questions only; for the 125 held-out questions only aggregates are. `data/leaderboard.parquet` and
`data/results.parquet` hold the earlier 103-question baseline (v1, earlier grader) and are not comparable with this
table.

## Quick start

```bash
pip install pandas pyarrow
python scripts/download_documents.py --out ./library      # about 11 GB from nasa.gov, checks sha256
```

```python
import pandas as pd
questions = pd.read_parquet("data/questions.parquet")      # 150 questions; answers for the 25 open ones
documents = pd.read_parquet("data/documents.parquet")      # raw library manifest (9,832 files, no text/types)
```

Or with the Hugging Face `datasets` library:

```python
from datasets import load_dataset
questions = load_dataset("baliseai/paper-trail", "questions", split="test")
```

## Run your own system

```bash
cp scripts/adapters/example_adapter.py scripts/adapters/my_adapter.py    # fill in answer()
python scripts/run_custom.py --system-id my-system --adapter scripts/adapters/my_adapter.py --split open
python scripts/grade_open.py runs/my-system.json --judge anthropic:claude-opus-5-5
```

`run_custom.py` sends each question to your code once, in a fresh process, stops it at 10 minutes, and checkpoints to
`runs/my-system.json`; rerun the command to resume. Not in Python? Use `--command "./my-agent"`: the question arrives
as JSON on stdin and the answer goes to stdout.

`grade_open.py` scores your 25 open answers against the published ones with a language-model judge (`anthropic:<model>`,
`openai:<model>` for any OpenAI-compatible service, or `command:<program>`). Repeat `--judge` to use several. It is your
own estimate; leaderboard scores come from the held-out questions.

When the open questions look right, drop `--split open` to run all 150, then check the file with
`python scripts/validate_submission.py runs/my-system.json`.

## Rules

1. **Build the library.** Load the 9,832 files with the folder structure as listed, into whatever your system reads
   from. Leave out nothing and add nothing.
2. **Ask each question exactly as written**, typos included. One run per question, no follow-up, no human help.
3. **Answer from the library.** Web search and general knowledge do not count as sources.
4. **Treat today as 23 November 2026.**
5. **Stop each run at 10 minutes.** Record the time, and the input and output tokens if your system reports them.
   (On the current leaderboard the assistants ran with a 600-second limit and the Vertesia agent rows with one hour;
   each row states its limit.)

Each question has a private rubric of atomic criteria, and the grade is computed from the criteria by a fixed rule
(details and the exact judge prompt in [GRADING.md](GRADING.md)):

| Grade | Points | Rule |
|---|--:|---|
| Correct | 1 | Every core and every required criterion met, and no statement that makes it wrong. Counts and totals within about 10% of an accepted figure are accepted. |
| Partial | 0.5 | Anything between correct and wrong: at least half the core facts, but something required missing or off. |
| Wrong | 0 (−1 strict) | States something that makes the answer wrong, or meets fewer than half of the core facts. |
| No answer | 0 | Empty, timed out, or only says it could not find or do it, with no criterion met. |

## Ingestion rules

Every system starts from the raw library: the 9,832 files and their folder paths, as `scripts/download_documents.py`
fetches them. Classifying documents, running OCR, extracting metadata values, and indexing must be done automatically
by the system—never set or corrected on documents by hand.

**Not allowed**

- Setting, editing, or correcting metadata values on any document by hand.
- A person typing, retyping, labelling, or tagging documents—one at a time or in bulk (for example by folder or by a
  list of files).
- Using the questions, the published answers, or any knowledge of the answers to tune schemas, extraction, or prompts.

**Allowed**

- Defining or editing **document types and schemas** (content types, fields, field types, and extraction instructions),
  either via a setup agent or authored by a person—just as an enterprise ECM administrator defines content types for a
  library—provided the schemas are not tuned on the benchmark questions or answers.
- Product settings that are not about individual documents: choosing models, connecting the store, turning on OCR.

Declare how you ingested the library—including whether schemas were auto-generated or human-authored (`schema_mode`)
and confirming zero manual document categorization or metadata edits—in the `ingestion` block of your submission.

## Submitting results

1. Run the 150 questions under the rules above. Check your setup on the 25 open questions first.
2. Fill in `submission-template.json`: one entry per question with your answer, the library paths you cited
   (`sources`), the time in seconds and, if your system reports them, input and output tokens. Describe your system
   in the `system` block: the harness and its version, the exact model and its effort setting, the content system
   that holds the library and how the harness searches it. Say how the library was ingested in `system.ingestion`,
   including whether any human categorization was used.
3. Send the file to:

   > **[benchmarks@baliseresearch.com](mailto:benchmarks@baliseresearch.com)**

   Please do not open a pull request or an issue with your answers: they would make the held-out answers public.
   Questions about the benchmark are welcome as GitHub issues.

We grade the held-out answers with the same rubric grader and add your system to the leaderboard with its scores and
tokens. Your answers stay private; only the grades are published.

## Repository layout

| Path | What it is |
|---|---|
| `data/questions.parquet` | 150 questions; answer, source files and note for the 25 open ones only |
| `data/documents.parquet` | 9,832 library files: raw path, nasa.gov URL, size, pages, sha256 (no extracted text or pre-assigned types) |
| `data/leaderboard.parquet` | One row per system (v1 103-question runs): scores, times, tokens |
| `data/results.parquet` | One row per system and question (v1): grade, points, time, tokens |
| `data/previously-published.json` | Every question whose answer has been published; none may be held out |
| `submission-template.json` | The 150-question file to fill in and send |
| `scripts/download_documents.py` | Rebuilds the library from nasa.gov and checks every file |
| `scripts/run_custom.py` | Runs the questions through your own code or program and writes the submission file |
| `scripts/grade_open.py` | Scores your 25 open answers against the published ones with a language-model judge |
| `scripts/validate_submission.py` | Validates submission JSON schema, IDs and open questions locally |
| `docs/` | The website, served at baliseresearch.com/paper-trail/ |
| `huggingface/README.md` | The Hugging Face dataset card, with the full description of the library, questions and columns |

The document files themselves are not in this repository: they stay on nasa.gov, where NASA publishes them. The
download script fetches each one and checks its size and sha256.

## Licence

The question set, rubric, grades, leaderboard and code are released under CC BY 4.0. The documents are public records
published by NASA. NASA does not endorse this benchmark, and the use of NASA documents here implies no endorsement by
NASA of any system measured.

## Citation

```bibtex
@misc{papertrail2026,
  title  = {Paper Trail: Benchmarking Models, Harnesses, and Content Systems on Enterprise Documents},
  author = {{Balise Research}},
  year   = {2026},
  note   = {v2.1, 150 questions over 9,832 public NASA documents},
  url    = {https://github.com/baliseai/paper-trail}
}
```
