---
pretty_name: "Paper Trail: Benchmarking Models, Harnesses, and Content Systems on Enterprise Documents"
license: cc-by-4.0
language:
  - en
task_categories:
  - question-answering
  - text-retrieval
task_ids:
  - document-retrieval
  - open-domain-qa
size_categories:
  - 1K<n<10K
tags:
  - retrieval
  - rag
  - agents
  - enterprise-search
  - document-qa
  - sharepoint
  - agent-harness
  - ecm
  - enterprise-content-management
  - benchmark
  - nasa
configs:
  - config_name: questions
    default: true
    data_files:
      - split: test
        path: data/questions.parquet
  - config_name: documents
    data_files:
      - split: corpus
        path: data/documents.parquet
  - config_name: leaderboard
    data_files:
      - split: v1
        path: data/leaderboard.parquet
  - config_name: results
    data_files:
      - split: v1
        path: data/results.parquet
---

# Paper Trail: Benchmarking Models, Harnesses, and Content Systems on Enterprise Documents

Paper Trail asks **150 work questions over 9,832 enterprise documents**: partnership agreements, procurement
contracts, audits, directives, technical reports and old backups. Tasks range from finding a clause to listing all
agreements that meet a condition. The files are public NASA records, so anyone can rebuild the library, and the
reference answers come from the documents themselves.

Each result reports the model, the harness that ran it, and the content system it searched.

**Funding and conflicts.** Paper Trail is published by Balise Research (Eric Barroca and Balise). It was first built at
Vertesia, whose document index and agent appear in 21 of the 23 baseline rows. Vertesia pays for its own runs. All 23
rows were run by the benchmark's authors. Outside submissions are graded with the same rubric.

For the submission format and run rules, see
[Submitting results](#submitting-results-for-the-held-out-set).

- **Version:** v2.1 (150 questions over 9,832 public NASA documents).
- **Changes in v2.1:** P48–P58 replace M2, M33, M37, M44, M52, M53, Q8, Q10, N3, N7, and P1.
  These prompts had answers in previously published material. The [eight former open examples](https://github.com/baliseai/paper-trail/blob/main/docs/data/archived-open-examples.json) remain available for practice.
  Existing runs need fresh answers for P48–P58. The 103-question leaderboard reports the earlier baseline.
- **Reference date:** questions use relative dates. **Treat today as 23 November 2026**: "next quarter" is
  January–March 2027, "this year" is 2026.
- **Held-out set:** 25 open questions (5 per kind) publish their answer and source files; the other 125 keep their
  answers private so scores stay comparable. See [Submitting results](#submitting-results-for-the-held-out-set).
- **Built by:** Eric Barroca and Balise, from an evaluation of assistants, agents, and content systems over this library.

## What is in this repository

| Config | Split | Rows | What it holds |
|---|---|--:|---|
| `questions` (default) | `test` | 150 | Every question, its kind, open/held-out flag, difficulty, and the answer and source files for the 25 open ones |
| `documents` | `corpus` | 9,832 | Raw library manifest: path, folder, subfolder, title, source collection, nasa.gov source URL, size, pages, sha256 (no extracted text or pre-assigned types) |
| `leaderboard` | `v1` | 23 | One row per measured system (v1 103-question runs): scores overall, by kind, on the hardest 11 and on the held-out 83; times; tokens |
| `results` | `v1` | 2,369 | One row per system and question (23 × 103 v1 runs): grade, points, time, input and output tokens |

Other files:

- `scripts/download_documents.py` rebuilds the library, file by file, from NASA's servers (see
  [The document files](#the-document-files)).
- `scripts/run_custom.py` runs the questions through your own system and writes the submission file;
  `scripts/grade_open.py` scores your 25 open answers against the published ones.
- `submission-template.json` is the file to fill in to submit results.

```python
from datasets import load_dataset

questions = load_dataset("baliseai/paper-trail", "questions", split="test")
documents = load_dataset("baliseai/paper-trail", "documents", split="corpus")
leaderboard = load_dataset("baliseai/paper-trail", "leaderboard", split="v1")
```

## The library

One document library in a single folder tree, filed the way real teams file things. In the measured runs it was a
SharePoint library, also synced into Vertesia; any store your system reads from works. The measured runs used 9,834 files; the
public list leaves out the two copies of one agreement with a private individual (no question depends on it).

| Top-level folder | Files | Source | Notes |
|---|--:|---|---|
| `Agreements/` | 2,015 | NASA Space Act Agreements and international agreements (nasa.gov) | `Active/<center>`, `Expired`, `Umbrella and annexes`, `Interagency`, `International`, and a `_To file` folder of unfiled and misfiled agreements |
| `Audit/` | 799 | NASA Office of Inspector General (oig.nasa.gov) | Audit and inspection reports |
| `Policy and guidance/` | 350 | NASA directives (nodis3.gsfc.nasa.gov) | NPD, NPR and OPD directives; one saved HTML page |
| `Procurement/` | 477 | NASA FOIA reading room (nasa.gov) | Redacted contracts and modifications |
| `Technical Reports/` | 5,500 | NASA Technical Reports Server (ntrs.nasa.gov) | By center and decade, 1958–2005 |
| `Old shared drive/` | 691 | NTRS and Space Act Agreements | Backups of agreements under other names (131 byte-identical renamed copies), old scans, and 168 TIFF/JPEG page images made from NTRS PDFs |
| **Total** | **9,832** | | about 11.2 GB and 178,937 pages |

How it was assembled:

- **Agreements** are NASA's published Space Act Agreements (domestic and international) and interagency
  agreements, placed in folders by status and center, including deliberately realistic filing errors (agreements in
  another center's folder, annexes away from their umbrella, a `_To file` folder).
- **Technical reports** come from the NTRS API, filtered to distribution `PUBLIC`, copyright
  `GOV_PUBLIC_USE_PERMITTED`, with no third-party, contractor or publisher material and no contractor reports.
- **Old shared drive** holds renamed backups of agreements (`agreements_backup_2019`, `Desktop backup`) and NTRS
  scans, some converted to bilevel TIFF (200 dpi, Group 4) or greyscale JPEG page images (150 dpi) so that
  reading them needs text recognition.
- **Agreements with private individuals** (for example Soyuz travel documents and agreements naming a person as the
  partner) were left out when the library was built; the one that remained in the measured library is left out
  of this list, with its backup copy.

## The questions

The current set has 150 questions in five kinds. The hardest eleven ("hardcore") are the questions that at most 40% of the first 13
measured systems answered correctly; the subset is frozen so it does not move as systems are added. All eleven are
held out.

| Kind | Name | Questions | Open | Hardcore (v1) |
|--:|---|--:|--:|--:|
| 1 | Find a document or a fact | 25 | 5 | 0 |
| 2 | Read a clause | 25 | 5 | 1 |
| 3 | Count, list or total | 40 | 5 | 6 |
| 4 | Across libraries | 27 | 5 | 1 |
| 5 | Find, then act | 33 | 5 | 3 |
| | **Total** | **150** | **25** | **11** |

The 25 open questions (five per kind) include answers and source paths for checking a submission.

`questions` columns: `id`, `kind`, `kind_name`, `question` (exactly as typed, typos included), `split`
(`open` / `held-out`), `difficulty` (`hardcore` / `standard`), `hardcore`, `solved_by` (how many of the 23 measured
systems answered it correctly) and `solved_of` (23); for open questions only, `answer`, `source_files` (library paths)
and `answer_note` (an ambiguity the grader allowed for, when there is one). These three are empty for every held-out
question.

## How to run it

1. **Build the library.** Load the 9,832 files with the folder structure as listed. Leave out nothing and add
   nothing.
2. **Ask each question exactly as written**, typos included. One run per question, no follow-up, no human help.
3. **Answer from the library.** Web search and general knowledge do not count as sources.
4. **Treat today as 23 November 2026.**
5. **Stop each run at 10 minutes.** Record the time, and the input and output tokens if your system reports them.

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

## How answers are graded

| Grade | Points | Meaning |
|---|--:|---|
| Correct | 1 | Says what the documents say. Counts and totals within about 10% count as correct; the documents' printed amounts are the reference. |
| Partial | 0.5 | Finds the right documents and points the right way, but leaves something out or gives a key figure more than 10% off. |
| Wrong | 0 | States something the documents contradict, or names the wrong document. |
| No answer | 0 | Gives up, asks a clarifying question, or says nothing is there when something is. |

The **score** is the points as a share of the questions in view, out of 100. The **strict score**
(`score_wrong_minus1`) also takes a point off for every wrong answer. Every answer is graded against the documents
by one grader, then by a blind second grader on any answer that is not obvious; disagreements are settled with the
reasons written down.

The answer key was rebuilt from the documents actually loaded in the library, not from NASA's public registers: where
the register and the files disagree, the files win.

## Leaderboard

Baseline scores out of 100 on all 103 original questions. C / P / W / N = correct / partial / wrong / no answer. Ranks follow the
score; the two systems at 96.6 are listed in the published order.

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

**Tokens.** We report tokens, not prices: what a token costs depends on how each customer pays for it. Tokens are
measured for the Vertesia agent from the platform's records of each run. Input tokens include the part read from the
prompt cache (`cached_input_tokens_per_question`), which is most of it: the conversation so far is read again at
each step. Output includes thinking. Small side calls to a lighter model (conversation notes, titles) are not counted.
Copilot does not expose its token use and Claude.ai's can only be estimated from the conversation text, so neither is
listed. The leaderboard's per-question means are taken over the runs with a complete token record (`token_runs`);
the per-question rows in `results` come from the graded run records, so a mean computed from them can differ slightly.

**Time limits.** Muse Wonder's provider slowed down when 16 questions ran at once, so the questions that hit the
10-minute limit then were run again three at a time; its 22 and 24 questions without an answer still timed out or
failed at the provider. `hit_time_limit` in `results` marks runs stopped at the limit.

`leaderboard` columns: `rank`, `system_id`, `name`, `harness`, `model`, `reasoning_effort`, `content_system` (the
content system the harness read), `retrieval` (how it searched it), `score`,
`score_wrong_minus1`, `correct`, `partial`, `wrong`, `no_answer`, `score_kind1_find` … `score_kind5_act`,
`score_hardcore`, `score_open`, `score_held_out`, `median_seconds`, `p90_seconds`, `input_tokens_per_question`,
`cached_input_tokens_per_question`, `output_tokens_per_question`, `input_tokens_median`, `token_runs`,
`model_calls_mean`, `tool_calls_mean`, `time_limit_hits`.

`results` columns: `system_id`, `harness`, `model`, `reasoning_effort`, `content_system`, `question_id`, `split`, `hardcore`, `kind`, `grade` (`correct`, `partial`, `wrong`,
`no answer`), `points`, `seconds`, `hit_time_limit`, `input_tokens` (cached part included), `cached_input_tokens`,
`output_tokens`, `model_calls`, `tool_calls`. Times are missing for Copilot, tokens for Copilot and Claude.ai, and
tokens for a few Vertesia agent runs that failed before any model call. The grades are published; the answers the
systems gave and the graders' reasons are not, because they would reveal the held-out answers.

## Submitting results for the held-out set

1. Build the library and run the 150 questions under the rules above. Check your setup on the 25 open questions
   first.
2. Fill in `submission-template.json`: one entry per question with your answer, the library paths you cited
   (`sources`), the time taken in seconds and, if your system reports them, input and output tokens. Describe your
   system in the `system` block (harness and version, exact model and effort setting, the content system and how
   the harness searches it, run date),
   and in `system.ingestion` how it ingested the library and whether any human categorization was used.
3. Send the file to:

   > **[benchmarks@baliseresearch.com](mailto:benchmarks@baliseresearch.com)**

   Please do not open a pull request or an issue with your answers: they would make the held-out answers public.
   Questions about the benchmark are welcome as GitHub issues.

We grade the held-out answers with the same rubric and graders' process, and add your system to the leaderboard with
its scores for the same question-set version and its reported token use.

Your answers stay private; only the grades are published. Code, website and the latest leaderboard:
[github.com/baliseai/paper-trail](https://github.com/baliseai/paper-trail) and
[baliseresearch.com/paper-trail](https://baliseresearch.com/paper-trail/).

```json
{
  "system": {"name": "…", "harness": "…", "harness_version": "…", "model": "…", "reasoning_effort": "…",
             "content_system": "…", "retrieval": "…", "run_date": "2026-11-23",
             "ingestion": {"no_human_categorization": true, "description": "…"}},
  "answers": [
    {"id": "P42", "answer": "…", "sources": ["Agreements/Active/HQ/38787_38787_UmbrellaPWW_7_18_23_FINAL_FOR_SIGNATURE.pdf"],
     "seconds": 54, "input_tokens": 47000, "output_tokens": 1800}
  ]
}
```

## The document files

**This repository ships the document list, not the files.** Each row of `documents` gives the library path, the
public nasa.gov URL the file came from, its size, page count and, for every file outside `Technical Reports/`, its
sha256. `scripts/download_documents.py` downloads every file from NASA, writes it under the same path, checks size
and hash, and renders the 168 converted scan images again from their NTRS PDFs:

```bash
pip install pandas pyarrow
python scripts/download_documents.py --out ./library
```

Why the files are not included:

- **Size.** The library is about 11.2 GB (5.9 GB of it technical reports), compared with about 1.1 MB for its manifest.
- **Provenance.** NASA stays the publisher of record, and anyone can check each file against its source.
- **Third-party material.** Works of the US federal government are generally not subject to copyright in the United
  States (17 U.S.C. § 105), but several collections carry material NASA did not write: agreements are signed with
  partners and show their names, logos and signatures; Inspector General reports attach company and agency response
  letters; FOIA contracts contain contractor text. Linking to NASA's own copies avoids redistributing that material
  in bulk. (The technical reports were filtered to NTRS's `GOV_PUBLIC_USE_PERMITTED` with no third-party or
  contractor material.)

The catch is link rot: NASA retires older Space Act Agreement links in batches, so some URLs may stop resolving. The
script lists every failure in `_download-report.json`; the sha256 values let anyone confirm that a copy found
elsewhere is the same file.

**No pre-extracted text or types.** `data/documents.parquet` (~1.1 MB) intentionally ships only raw file metadata and
`nasa.gov` source URLs—no extracted text and no automatic content-type classification. Every tested system must
download and ingest the raw files (PDFs, HTML, TIFFs, JPEGs) on its own.

`documents` columns: `id`, `path`, `folder`, `subfolder`, `name`, `title` (the NTRS title for NTRS documents,
otherwise the file name), `title_from`, `source`, `source_url`, `ntrs_id`, `bytes`, `pages`, `sha256`, `derived`
(`renamed copy` / `converted image`), `note`.

## Limitations

- **One run per question.** No system was run twice, so run-to-run variation is not measured; read differences of a
  point or two as ties (the two systems at 96.6 are tied).
- **One library, one domain.** US government agreements, contracts, audits, directives and technical reports, in
  English. Results may not transfer to other document collections or languages.
- **Graded by people, with judgement.** "Within about 10%" and "partial" call for judgement; the blind second grade
  and written adjudication reduce, but do not remove, grader variance. The held-out answers cannot be checked
  publicly.
- **Fixed date.** Answers about what is active, expiring or due depend on the reference date of 23 November 2026.
- **Not every system is measured the same way.** Claude.ai's times come from its conversation records and Copilot's
  are given only as a median and 90th percentile; neither reports tokens. The Vertesia agent's times and tokens come
  from the platform's run records. Copilot and Claude.ai
  were run through their consumer products, whose behaviour can change without notice.
- **Conflict of interest.** The benchmark was first built at Vertesia, which sells the index and the agent used in 21
  of the 23 baseline rows, and its authors ran every row. The questions, rubric and per-question grades are published
  so others can judge, and outside submissions are graded the same way.
- **Link rot.** Some source URLs may stop resolving over time (see above).

## Licence

The question set, rubric, grades, leaderboard and this card are released under CC BY 4.0. The documents are public
records published by NASA; see [The document files](#the-document-files) for their status. NASA does not endorse
this benchmark, and the use of NASA documents here implies no endorsement by NASA of any system measured.

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
