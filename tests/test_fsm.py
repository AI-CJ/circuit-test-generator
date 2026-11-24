import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fsm import Transition, load_machine


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "parity.json"


class MachineTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "machine.json"
        self.spec = json.loads(EXAMPLE.read_text())

    def load(self):
        self.path.write_text(json.dumps(self.spec))
        return load_machine(self.path)

    def test_parity_table(self):
        machine = load_machine(EXAMPLE)
        self.assertEqual(machine.reset, "even")
        self.assertEqual(machine.transitions, {
            "even": {"0": Transition("even", 0), "1": Transition("odd", 1)},
            "odd": {"0": Transition("odd", 1), "1": Transition("even", 0)},
        })

    def test_unreachable_state_is_retained(self):
        self.spec["states"]["unused"] = self.spec["states"]["even"]
        self.assertIn("unused", self.load().transitions)

    def test_missing_input(self):
        del self.spec["states"]["odd"]["1"]
        with self.assertRaisesRegex(ValueError, "state 'odd'"):
            self.load()

    def test_unknown_states(self):
        self.spec["reset"] = "missing"
        with self.assertRaisesRegex(ValueError, "reset"):
            self.load()
        self.spec["reset"] = "even"
        self.spec["states"]["odd"]["0"]["next"] = "missing"
        with self.assertRaisesRegex(ValueError, "state 'odd' input 0"):
            self.load()

    def test_output_must_be_an_integer_bit(self):
        for value in (True, 0.0, 2, "1", None):
            with self.subTest(value=value):
                self.spec["states"]["even"]["1"]["output"] = value
                with self.assertRaisesRegex(ValueError, "output"):
                    self.load()

    def test_duplicate_input_is_rejected_before_decoding_loses_it(self):
        self.path.write_text(EXAMPLE.read_text().replace('"0":', '"1":', 1))
        with self.assertRaisesRegex(ValueError, "duplicate key '1'"):
            load_machine(self.path)

    def test_cli_reports_bad_json(self):
        self.path.write_text("{")
        result = subprocess.run([sys.executable, ROOT / "fsm.py", self.path],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(self.path), result.stderr)
        self.assertNotIn("Traceback", result.stderr)
