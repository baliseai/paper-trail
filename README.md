# Paper Trail: Benchmarking Models, Harnesses, and Content Systems on Enterprise Documents

**[Website](https://baliseresearch.com/paper-trail/) · [Dataset on Hugging Face](https://huggingface.co/datasets/baliseai/paper-trail) · [Leaderboard](#leaderboard) · [Submit a system](#submitting-results)**

Paper Trail asks **150 questions about 9,832 public NASA files**. The library includes partnership agreements,
procurement records, audits, directives, technical reports, and backups. Tasks range from finding a clause to listing
all agreements that meet a condition. The reference answers are based on the documents in the library.

Each result reports the model, the harness that ran it, and the content system it searched.

**Funding and conflicts.** Paper Trail is published by Balise Research (Eric Barroca and Balise). It was first built at
Vertesia, whose document index and agent appear in 21 of the 23 baseline rows. Vertesia pays for its own runs. All 23
rows were run by the benchmark's authors. Outside submissions are graded with the same rubric.

For the submission format and run rules, see
[Submitting results](#submitting-results).

- **Version:** v2.1 (150 questions over 9,832 public NASA documents).
- **Changes in v2.1:** P48–P58 replace M2, M33, M37, M44, M52, M53, Q8, Q10, N3, N7, and P1.
  These prompts had answers in previously published material. The [eight former open examples](docs/data/archived-open-examples.json) remain available for practice.
  Existing runs need fresh answers for P48–P58. The 103-question leaderboard reports the earlier baseline.
- **Reference date:** treat today as **23 November 2026** ("next quarter" is January–March 2027).
- **Held-out set:** 25 open questions (5 per kind) publish their answer and source files; the other 125 keep their
  answers private so scores stay comparable.
- **Raw manifest only:** `data/documents.parquet` ships only raw file metadata and `nasa.gov` URLs (no extracted text
  and no pre-assigned document types); every system under test must ingest and process the raw files itself.

## Leaderboard

Baseline scores out of 100 on all 103 original questions (correct = 1, partial = 0.5, wrong and no answer = 0). Strict also takes a
point off for each wrong answer. C / P / W / N = correct / partial / wrong / no answer. Tokens are means per
question; we report tokens, not prices.

| # | Harness | Model | Effort | Content system | Score | Strict | Hardest 11 | Held-out 83 | C / P / W / N | Median s | Input tokens / q | Output tokens / q |
|--:|---|---|:-:|---|--:|--:|--:|--:|:-:|--:|--:|--:|
| 1 | Claude.ai | Claude Opus 5.5 | high | SharePoint + Vertesia index | 96.6 | 96.6 | 68.2 | 95.8 | 96 / 7 / 0 / 0 | 46 | — | — |
| 2 | Vertesia Agent System | Gemini 4 Neon | medium | Vertesia | 96.6 | 96.6 | 77.3 | 95.8 | 97 / 5 / 0 / 1 | 168 | 347K | 8.3K |
| 3 | Vertesia Agent System | Claude Opus 5.5 | high | Vertesia | 95.1 | 95.1 | 54.5 | 94.0 | 93 / 10 / 0 / 0 | 116 | 327K | 4.1K |
| 4 | Vertesia Agent System | Gemini 4 Neon | low | Vertesia | 94.7 | 94.7 | 54.5 | 93.4 | 92 / 11 / 0 / 0 | 126 | 154K | 3.5K |
| 5 | Microsoft 365 Copilot (Cowork) | GPT (Auto) | medium | SharePoint + Vertesia index | 94.2 | 94.2 | 68.2 | 92.8 | 91 / 12 / 0 / 0 | 57 | — | — |
| 6 | Vertesia Agent System | GPT 6.2 Sol | high | Vertesia | 91.7 | 90.8 | 45.5 | 89.8 | 90 / 9 / 1 / 3 | 152 | 374K | 3.2K |
| 7 | Vertesia Agent System | GPT 6.2 Sol | medium | Vertesia | 91.3 | 89.3 | 45.5 | 89.2 | 89 / 10 / 2 / 2 | 125 | 238K | 1.8K |
| 8 | Vertesia Agent System | Claude Opus 5.5 | medium | Vertesia | 90.8 | 88.8 | 45.5 | 89.8 | 87 / 13 / 2 / 1 | 114 | 260K | 3.3K |
| 9 | Vertesia Agent System | GPT 6.2 Astra | low | Vertesia | 89.3 | 88.3 | 45.5 | 88.0 | 85 / 14 / 1 / 3 | 99 | 97K | 0.7K |
| 10 | Vertesia Agent System | GPT 6.2 Astra | medium | Vertesia | 88.8 | 87.9 | 50.0 | 86.1 | 85 / 13 / 1 / 4 | 105 | 143K | 1.1K |
| 11 | Vertesia Agent System | Gemini 4 Argon | low | Vertesia | 86.9 | 86.9 | 50.0 | 83.7 | 87 / 5 / 0 / 11 | 244 | 569K | 4.9K |
| 12 | Vertesia Agent System | Claude Fable 5 | medium | Vertesia | 85.0 | 84.0 | 54.5 | 83.7 | 76 / 23 / 1 / 3 | 87 | 268K | 3.3K |
| 13 | Vertesia Agent System | GPT 6.2 Sol | low | Vertesia | 83.0 | 83.0 | 54.5 | 83.7 | 72 / 27 / 0 / 4 | 106 | 97K | 0.7K |
| 14 | Vertesia Agent System | Gemini 4 Neon | high | Vertesia | 82.5 | 81.6 | 45.5 | 78.3 | 83 / 4 / 1 / 15 | 267 | 760K | 16K |
| 15 | Vertesia Agent System | Claude Opus 5.5 | low | Vertesia | 81.6 | 78.6 | 50.0 | 78.9 | 69 / 30 / 3 / 1 | 102 | 171K | 2.0K |
| 16 | Vertesia Agent System | Claude Fable 5 | low | Vertesia | 80.6 | 76.7 | 40.9 | 77.7 | 71 / 24 / 4 / 4 | 77 | 221K | 2.2K |
| 17 | Vertesia Agent System | Gemini 4 Argon | medium | Vertesia | 78.2 | 78.2 | 36.4 | 72.9 | 78 / 5 / 0 / 20 | 278 | 547K | 8.2K |
| 18 | Vertesia Agent System | Claude Sonnet 5.5 | medium | Vertesia | 76.2 | 74.3 | 50.0 | 75.3 | 63 / 31 / 2 / 7 | 73 | 176K | 1.9K |
| 19 | Vertesia Agent System | Muse Wonder 1.0 | low | Vertesia | 73.3 | 72.3 | 27.3 | 72.3 | 71 / 9 / 1 / 22 | 350 | 245K | 2.8K |
| 20 | Claude.ai | Claude Opus 5.5 | high | SharePoint | 70.9 | 66.0 | 59.1 | 68.1 | 58 / 30 / 5 / 10 | 71 | — | — |
| 21 | Vertesia Agent System | Muse Wonder 1.0 | medium | Vertesia | 69.4 | 68.4 | 36.4 | 65.1 | 65 / 13 / 1 / 24 | 407 | 276K | 3.3K |
| 22 | Vertesia Agent System | Claude Sonnet 5.5 | low | Vertesia | 54.9 | 52.9 | 31.8 | 54.2 | 41 / 31 / 2 / 29 | 53 | 105K | 1.2K |
| 23 | Microsoft 365 Copilot (Cowork) | GPT (Auto) | medium | SharePoint | 10.7 | 6.8 | 9.1 | 12.0 | 5 / 12 / 4 / 82 | 20 | — | — |

**How to read the rows.** Each row is one harness running one model over one content system. The current table covers three setups:

- **Vertesia Agent System** (Content system: Vertesia): Vertesia's general-purpose agent with read-only tools. The documents are stored
  in Vertesia, which converts, types and indexes them, and the agent searches them there. Only the model and its
  effort setting change between these rows.
- **+ Vertesia** (Content system: SharePoint + Vertesia index): the harness is an assistant, Microsoft 365 Copilot (Cowork) or Claude.ai, and the documents stay in
  a SharePoint library. The assistant keeps its own SharePoint search and also gets a search tool over Vertesia's
  index of the same library (the Vertesia plugin in Copilot, the Vertesia connector in Claude.ai). It is the index
  Vertesia Agent System rows use.
- **Alone** (Content system: SharePoint): the same assistants with only their own SharePoint search: Copilot's built-in search, or Claude.ai's
  Microsoft 365 connector (search and open files).

Copilot Cowork runs OpenAI GPT models in `Auto` mode at `medium` effort (choosing between variants such as Astra and Sol per task), so it is listed as `GPT (Auto)`. One run per question for every system.

Copilot does not expose its token use, and Claude.ai's can only be estimated, so neither is listed. Per-question grades for every system are in `data/results.parquet`; the
[website](https://baliseresearch.com/paper-trail/) breaks the scores down by kind of question.

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

| Grade | Points | Meaning |
|---|--:|---|
| Correct | 1 | Says what the documents say. Counts and totals within about 10% count as correct; the documents' printed amounts are the reference. |
| Partial | 0.5 | Finds the right documents and points the right way, but leaves something out or gives a key figure more than 10% off. |
| Wrong | 0 | States something the documents contradict, or names the wrong document. |
| No answer | 0 | Gives up, asks a clarifying question, or says nothing is there when something is. |

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

We grade the held-out answers with the same rubric and add your system to the leaderboard with its scores and
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
  author = {Barroca, Eric and {Balise}},
  year   = {2026},
  note   = {v2.1, 150 questions over 9,832 public NASA documents},
  url    = {https://github.com/baliseai/paper-trail}
}
```
