from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fsm import Sequence, load_machine, logisim_rows


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "examples/parity.json"


class LogisimTests(unittest.TestCase):
    def test_reset_and_pre_edge_output(self):
        cases = [Sequence("10", None), Sequence("", None), Sequence("0", None)]
        self.assertEqual(list(logisim_rows(load_machine(SPEC), cases)), [
            "Bit Clock Reset Result <set> <seq>",
            "0 0 1 <DC> 1 1",
            "1 0 0 1 1 2",
            "1 1 0 <DC> 1 3",
            "0 0 0 1 1 4",
            "0 1 0 <DC> 1 5",
            "0 0 1 <DC> 2 1",
            "0 0 1 <DC> 3 1",
            "0 0 0 0 3 2",
            "0 1 0 <DC> 3 3",
        ])

    def test_bad_expectation_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = Path(directory) / "cases.json"
            vector = Path(directory) / "vector.txt"
            args = [sys.executable, ROOT / "fsm.py", SPEC,
                    "--sequences", cases, "--logisim", vector]
            cases.write_text('[{"inputs":"1","expected":"0"}]')
            failure = subprocess.run(args, capture_output=True, text=True)
            self.assertIn("expected=0, actual=1", failure.stderr)
            self.assertNotEqual(failure.returncode, 0)
            self.assertFalse(vector.exists())
            cases.write_text('[{"inputs":"1"}]')
            vector.write_text("keep")
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertEqual(vector.read_text(), "keep")
