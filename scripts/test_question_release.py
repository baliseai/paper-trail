"""Check that previously published answers stay out of the active held-out set."""

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = "docs/data/questions.json"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class QuestionReleaseTest(unittest.TestCase):
    def test_published_answers_stay_public_or_retired(self):
        held = [q for q in read_json(QUESTIONS) if q["split"] == "held-out"]
        published = read_json("docs/data/archived-open-examples.json")
        # The standing record of every question whose answer was ever published.
        published.extend(read_json("data/previously-published.json")["questions"])
        # Include previous public releases even when an example is later removed from the site.
        revisions = subprocess.check_output(
            ["git", "log", "--format=%H", "--", QUESTIONS], cwd=ROOT, text=True
        ).splitlines()
        for revision in revisions:
            previous = subprocess.check_output(
                ["git", "show", f"{revision}:{QUESTIONS}"], cwd=ROOT
            )
            published.extend(q for q in json.loads(previous) if q.get("answer"))
        known_ids = {q["id"] for q in published}
        known_text = {" ".join(q["question"].casefold().split()) for q in published}
        for q in held:
            with self.subTest(question=q["id"]):
                self.assertNotIn(q["id"], known_ids)
                self.assertNotIn(" ".join(q["question"].casefold().split()), known_text)
                self.assertFalse(any(q.get(k) for k in ("answer", "source_files", "answer_note", "note")))

    def test_both_templates_use_current_ids_in_order(self):
        ids = [q["id"] for q in read_json(QUESTIONS)]
        self.assertEqual(len(ids), len(set(ids)))
        for path in ("submission-template.json", "docs/data/submission-template.json"):
            self.assertEqual([a["id"] for a in read_json(path)["answers"]], ids)


if __name__ == "__main__":
    unittest.main()
