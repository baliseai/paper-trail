"""Check the generic runner and the open-question grader end to end, with no network."""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import grade_open  # noqa: E402

QUESTIONS = json.loads((ROOT / "docs/data/questions.json").read_text(encoding="utf-8"))
OPEN = [q for q in QUESTIONS if q["split"] == "open"]

ADAPTER = textwrap.dedent('''
    import os, time
    SYSTEM = {"name": "Test system"}
    def answer(question):
        with open(os.environ["PT_LOG"], "a") as f:
            f.write(question["id"] + "\\n")
        print("noise on stdout must not break the result")
        if question["id"] == "M5":
            time.sleep(30)
        if question["id"] == "M9":
            raise RuntimeError("boom")
        return {"answer": question["prompt"], "sources": ["a.pdf", 3], "input_tokens": 12, "output_tokens": "many"}
''')

# Grades "correct" when the answer equals the reference, "wrong" for the literal WRONG, otherwise "partial".
JUDGE = textwrap.dedent('''
    import json, sys
    r = json.load(sys.stdin)
    g = "correct" if r["answer"] == r["reference_answer"] else "wrong" if r["answer"] == "WRONG" else "partial"
    print("Here is my grade:\\n```json\\n" + json.dumps({"grade": g, "reason": "test"}) + "\\n```")
''')
ALWAYS_PARTIAL = 'import json; print(json.dumps({"grade": "partial", "reason": "test"}))'


def run(script, *args, env=None):
    return subprocess.run([sys.executable, str(HERE / script), *args], capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


class RunCustomTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.adapter = self.tmp / "adapter.py"
        self.adapter.write_text(ADAPTER)
        self.log = self.tmp / "calls.log"
        self.args = ["--system-id", "t", "--adapter", str(self.adapter), "--out-dir", str(self.tmp),
                     "--ids", "M1,M5,M9", "--time-limit", "2", "--workers", "3"]

    def answers(self):
        return {a["id"]: a for a in json.loads((self.tmp / "t.json").read_text())["answers"]}

    def test_adapter_run_timeout_error_and_resume(self):
        first = run("run_custom.py", *self.args, env={"PT_LOG": str(self.log)})
        self.assertEqual(first.returncode, 0, first.stderr)
        data = json.loads((self.tmp / "t.json").read_text())
        self.assertEqual([a["id"] for a in data["answers"]], [q["id"] for q in QUESTIONS])
        self.assertEqual(data["system"]["name"], "Test system")
        got = self.answers()
        m1 = next(q for q in QUESTIONS if q["id"] == "M1")
        self.assertEqual(got["M1"]["answer"], "Treat today as 23 November 2026. " + m1["question"])
        self.assertEqual(got["M1"]["sources"], ["a.pdf"])
        self.assertEqual((got["M1"]["input_tokens"], got["M1"]["output_tokens"]), (12, None))
        self.assertTrue(got["M5"]["hit_time_limit"])
        self.assertEqual((got["M5"]["answer"], got["M5"]["seconds"]), ("", 2.0))
        self.assertIn("boom", got["M9"]["error"])
        self.assertEqual(got["M16"]["answer"], "")  # not selected, left blank

        second = run("run_custom.py", *self.args, env={"PT_LOG": str(self.log)})
        self.assertEqual(second.returncode, 0, second.stderr)
        calls = self.log.read_text().split()
        # The answered and the timed-out question are kept; only the failed one runs again.
        self.assertEqual((calls.count("M1"), calls.count("M5"), calls.count("M9")), (1, 1, 2))

    def test_command_mode_takes_plain_text(self):
        prog = self.tmp / "agent.py"
        prog.write_text('import json, sys\nq = json.load(sys.stdin)\nprint("answer for " + q["id"])\n')
        done = run("run_custom.py", "--system-id", "t", "--command", f"{sys.executable} {prog}",
                   "--out-dir", str(self.tmp), "--ids", "P20")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.answers()["P20"]["answer"], "answer for P20")


class GradeOpenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.judge = self.tmp / "judge.py"
        self.judge.write_text(JUDGE)
        answers = []
        for i, q in enumerate(OPEN):
            text = "" if i == 0 else "WRONG" if i == 1 else "close enough" if i == 2 else q["answer"]
            answers.append({"id": q["id"], "answer": text, "sources": []})
        self.sub = self.tmp / "sub.json"
        self.sub.write_text(json.dumps({"system": {}, "answers": answers}))

    def test_scores_from_one_judge(self):
        done = run("grade_open.py", str(self.sub), "--judge", f"command:{sys.executable} {self.judge}")
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        report = json.loads((self.tmp / "sub.open-grades.json").read_text())
        s = report["summary"]
        n = len(OPEN)
        self.assertEqual((s["correct"], s["partial"], s["wrong"], s["no_answer"]), (n - 3, 1, 1, 1))
        self.assertEqual(s["score"], round(100 * (n - 3 + 0.5) / n, 1))
        self.assertEqual(s["strict"], round(100 * (n - 3 + 0.5 - 1) / n, 1))
        self.assertEqual(report["questions"][0]["judges"], {})  # an empty answer never reaches a judge

    def test_two_judges_take_the_lower_grade(self):
        done = run("grade_open.py", str(self.sub), "--judge", f"command:{sys.executable} {self.judge}",
                   "--judge", f"command:{sys.executable} -c '{ALWAYS_PARTIAL}'")
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        rows = json.loads((self.tmp / "sub.open-grades.json").read_text())["questions"]
        self.assertEqual((rows[1]["grade"], rows[1]["agreed"]), ("wrong", False))     # wrong vs partial
        self.assertEqual((rows[2]["grade"], rows[2]["agreed"]), ("partial", True))    # both partial
        self.assertEqual((rows[3]["grade"], rows[3]["agreed"]), ("partial", False))   # correct vs partial

    def test_failed_judge_gives_no_score(self):
        done = run("grade_open.py", str(self.sub), "--judge", f"command:{sys.executable} -c 'print(1)'")
        self.assertEqual(done.returncode, 1)
        self.assertNotIn("summary", json.loads((self.tmp / "sub.open-grades.json").read_text()))

    def test_parse_and_settle(self):
        self.assertEqual(grade_open.parse_grade('{"grade": "No_Answer", "reason": "x"}')["grade"], "no answer")
        self.assertEqual(grade_open.parse_grade('ok {"grade":"partial","reason":"has } brace"} done')["grade"], "partial")
        with self.assertRaises(grade_open.JudgeError):
            grade_open.parse_grade('{"grade": "excellent"}')
        self.assertEqual(grade_open.settle(["correct", "correct"]), ("correct", True))
        self.assertEqual(grade_open.settle(["correct", "partial"]), ("partial", False))
        self.assertEqual(grade_open.settle(["correct", "correct", "wrong"]), ("correct", False))
        self.assertEqual(grade_open.settle(["correct", "partial", "wrong"]), ("wrong", False))


if __name__ == "__main__":
    unittest.main()
