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

**Funding and conflicts.** Paper Trail is built and published by Balise, Inc. Vertesia's document index or agent
appears in every row except the assistants running alone on SharePoint, and Vertesia pays for its own runs. All rows
were run by Balise. Outside submissions are graded with the same rubric grader.

For the submission format and run rules, see
[Submitting results](#submitting-results-for-the-held-out-set).

- **Version:** v2.1 (150 questions over 9,832 public NASA documents).
- **Changes in v2.1:** P48–P58 replace M2, M33, M37, M44, M52, M53, Q8, Q10, N3, N7, and P1.
  These prompts had answers in previously published material. The [eight former open examples](https://github.com/baliseai/paper-trail/blob/main/docs/data/archived-open-examples.json) remain available for practice.
  Existing runs need fresh answers for P48–P58. The leaderboard below is on all 150 v2.1 questions; the `leaderboard`
  and `results` configs hold the earlier 103-question baseline.
- **Reference date:** questions use relative dates. **Treat today as 23 November 2026**: "next quarter" is
  January–March 2027, "this year" is 2026.
- **Held-out set:** 25 open questions (5 per kind) publish their answer and source files; the other 125 keep their
  answers private so scores stay comparable. See [Submitting results](#submitting-results-for-the-held-out-set).
- **Built by:** Balise, Inc., from an evaluation of assistants, agents, and content systems over this library.

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
(`open` / `held-out`), `difficulty` (`hardcore` / `standard`), `hardcore`, `solved_by` (how many of the 23 baseline v1
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
   (On the current leaderboard the assistants ran with a 600-second limit and the Vertesia agent rows with one hour.)

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

Each question has a private rubric of atomic criteria: the core facts that make an answer right, what a complete
answer must also contain, the statements that make it wrong, and the things that are explicitly not required. Three
judges from three labs (Claude Opus 5.5, GPT 6.2 Sol and Gemini 4 Neon) check every criterion on every answer; no
judge gives an overall grade. Numbers and list counts are checked in code against accepted ranges. The grade is then
computed by a fixed rule:

| Grade | Points | Rule |
|---|--:|---|
| Correct | 1 | Every core and every required criterion met, and no statement that makes it wrong. Counts and totals within about 10% of an accepted figure are accepted. |
| Partial | 0.5 | Anything between correct and wrong. |
| Wrong | 0 | A statement that makes it wrong is present, or fewer than half of the core facts are met. |
| No answer | 0 | Empty, timed out, or only says it could not find or do it, with no criterion met. |

The **score** is the points as a share of the questions in view, out of 100. The **strict score**
(`score_wrong_minus1`) also takes a point off for every wrong answer. The full protocol, the measured stability and
the exact judge prompt are in
[GRADING.md](https://github.com/baliseai/paper-trail/blob/main/GRADING.md). The rubrics, the gold answers of the
held-out questions and the grader notes stay private.

The answer key was rebuilt from the documents actually loaded in the library, not from NASA's public registers: where
the register and the files disagree, the files win.

## Leaderboard

Scores out of 100 on all 150 questions of v2.1, rubric grader. C / P / W / N = correct / partial / wrong / no answer.

<!-- leaderboard:start -->
| # | Harness | Model | Effort | Content system | Score | Strict | Hardest 11 | Held-out 125 | C / P / W / N | Median s | Input tokens / q | Output tokens / q |
|--:|---|---|:-:|---|--:|--:|--:|--:|:-:|--:|--:|--:|
| 1 | Vertesia Agent System | Gemini 4 Neon | medium | Vertesia | 97.3 | 97.3 | 86.4 | 96.8 | 143 / 6 / 0 / 1 | 175 | 493K | 13K |
| 2 | Vertesia Agent System | Claude Opus 5.5 | medium | Vertesia | 97.0 | 96.3 | 86.4 | 96.8 | 142 / 7 / 1 / 0 | 69 | 430K | 5.7K |
| 3 | Vertesia Agent System | Claude Fable 5.2 | medium | Vertesia | 96.7 | 96.7 | 86.4 | 96.4 | 140 / 10 / 0 / 0 | 94 | 434K | 9.4K |
| 4 | Vertesia Agent System | Mistral Large 4.0 | medium | Vertesia | 95.0 | 94.3 | 81.8 | 94.4 | 136 / 13 / 1 / 0 | 170 | 852K | 14K |
| 4 | Claude.ai | Claude Opus 5.5 | medium | SharePoint + Vertesia index | 95.0 | 94.3 | 86.4 | 95.6 | 136 / 13 / 1 / 0 | 68 | — | — |
| 6 | Vertesia Agent System | GPT 6.2 Astra | medium | Vertesia | 93.3 | 91.3 | 77.3 | 93.2 | 133 / 14 / 3 / 0 | 67 | 262K | 2.0K |
| 7 | Vertesia Agent System | GPT 6.2 Sol | medium | Vertesia | 91.3 | 87.3 | 77.3 | 90.0 | 130 / 14 / 6 / 0 | 83 | 412K | 3.5K |
| 8 | Vertesia Agent System | Claude Sonnet 5.5 | medium | Vertesia | 91.0 | 89.0 | 77.3 | 90.4 | 128 / 17 / 3 / 2 | 44 | 324K | 4.1K |
| 9 | ChatGPT | GPT 6.2 | medium | SharePoint + Vertesia index | 89.0 | 85.7 | 77.3 | 88.4 | 122 / 23 / 5 / 0 | 29 | — | — |
| 10 | Microsoft 365 Copilot Chat | Auto | — | SharePoint + Vertesia index | 75.3 | 60.7 | 45.5 | 76.8 | 100 / 26 / 22 / 2 | 50 | — | — |
| 11 | Claude.ai | Claude Opus 5.5 | medium | SharePoint | 59.7 | 40.3 | 40.9 | 58.0 | 76 / 27 / 29 / 18 | 56 | — | — |
| 12 | ChatGPT | GPT 6.2 | medium | SharePoint | 56.7 | 30.7 | 45.5 | 56.4 | 70 / 30 / 39 / 11 | 35 | — | — |
| 13 | Microsoft 365 Copilot Cowork | Auto | — | SharePoint | 13.7 | -6.3 | 9.1 | 11.6 | 11 / 19 / 30 / 90 | 23 | — | — |
<!-- leaderboard:end -->

**How to read the rows.** Each row is one harness running one model over one content system:

- **Vertesia Agent System** (content system: Vertesia): Vertesia's general-purpose agent with read-only tools. The
  documents are stored in Vertesia, which converts, types and indexes them, and the agent searches them there. Only
  the model changes between these rows, all at medium effort.
- **+ Vertesia index** (content system: SharePoint + Vertesia index): the harness is an assistant (Claude.ai, ChatGPT
  or Microsoft 365 Copilot) and the documents stay in a SharePoint library. The assistant keeps its own SharePoint
  search and also gets a search tool over Vertesia's index of the same library, the index the agent rows use.
- **Alone** (content system: SharePoint): the same assistants with only their own SharePoint search.

**Run conditions.** One run per question for every system. Time limit per question: one hour for the Vertesia agent
rows, 600 seconds for the assistants; two Copilot Cowork answers without the index ran past 600 seconds (724 and 858)
and were kept. Copilot's model is `Auto`: Copilot picks it and does not say which one answered. Copilot Chat +
Vertesia was run with the Vertesia search skill attached by hand in every chat (without it Copilot did not call
Vertesia), and Copilot used Vertesia in 133 of the 150 answers; Copilot Cowork + Vertesia used it in 140 of the 150.
Copilot Cowork alone gave no answer on 112 of the 150 questions because its file search found nothing. In the
Claude.ai and ChatGPT rows, at most nine answers per row are second attempts: the first attempt had read an output
file an earlier run left in the library, or stopped at a connector sign-in. A configuration is listed once all 150 of
its answers are graded.

**Tokens.** We report tokens, not prices: what a token costs depends on how each customer pays for it. Tokens are
measured for the Vertesia agent from the platform's records of each run. Input tokens include the part read from the
prompt cache (`cached_input_tokens_per_question`), which is most of it: the conversation so far is read again at
each step. Output includes thinking. Small side calls to a lighter model (conversation notes, titles) are not counted.
Claude.ai, ChatGPT and Copilot do not report token use, so their rows show none. Means are taken over the runs
with a token record.

## Baseline files (v1)

The `leaderboard` and `results` configs hold the earlier 103-question baseline (v1): 23 systems, graded with the
earlier holistic grader. They are not comparable with the v2.1 table above. Muse Wonder's provider slowed down when
16 questions ran at once, so its questions that hit the 10-minute limit then were run again three at a time.

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
- **Conflict of interest.** Vertesia sells the index and the agent used in 21 of the 23 baseline rows, and the
  benchmark's publisher ran every row. The questions, rubric and per-question grades are published so others can judge,
  and outside submissions are graded the same way.
- **Link rot.** Some source URLs may stop resolving over time (see above).

## Licence

The question set, rubric, grades, leaderboard and this card are released under CC BY 4.0. The documents are public
records published by NASA; see [The document files](#the-document-files) for their status. NASA does not endorse
this benchmark, and the use of NASA documents here implies no endorsement by NASA of any system measured.

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
