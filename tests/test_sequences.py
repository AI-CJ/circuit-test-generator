import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fsm import load_machine, load_sequences, simulate


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "examples/parity.json"


class SequenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "cases.json"

    def run_cli(self, cases):
        self.path.write_text(json.dumps(cases))
        return subprocess.run(
            [sys.executable, ROOT / "fsm.py", PARITY, "--sequences", self.path],
            capture_output=True, text=True,
        )

    def test_trace_keeps_source_and_destination(self):
        trace = simulate(load_machine(PARITY), "101")
        self.assertEqual([(src, bit, edge.next_state, edge.output) for src, bit, edge in trace],
                         [("even", "1", "odd", 1), ("odd", "0", "odd", 1),
                          ("odd", "1", "even", 0)])

    def test_example_cases_each_start_at_reset(self):
        cases = json.loads((ROOT / "examples/parity-cases.json").read_text())
        result = self.run_cli(cases)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[1:], [
            "sequence 1: outputs='11', final=odd", "sequence 2: outputs='110', final=even",
        ])

    def test_optional_expected_and_empty_sequence(self):
        result = self.run_cli([{"inputs": "001"}, {"inputs": "", "expected": ""}])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("outputs='001', final=odd", result.stdout)
        self.assertIn("outputs='', final=even", result.stdout)

    def test_cli_identifies_first_mismatch(self):
        result = self.run_cli([{"inputs": "0"}, {"inputs": "101", "expected": "101"}])
        self.assertEqual(result.returncode, 1)
        self.assertIn("sequence 2, step 2: state=odd, input=0, expected=0, actual=1", result.stderr)

    def test_rejects_invalid_cases(self):
        for rows in ([], {}, [1], [{}], [{"inputs": 0}], [{"inputs": "12"}],
                     [{"inputs": "", "expected": None}], [{"inputs": "1", "expected": ""}],
                     [{"inputs": "", "unexpected": 0}]):
            with self.subTest(rows=rows):
                self.path.write_text(json.dumps(rows))
                with self.assertRaises(ValueError):
                    load_sequences(self.path)
