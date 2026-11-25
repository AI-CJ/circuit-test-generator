from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import unittest

from fsm import Machine, Sequence, Transition, coverage_report, load_machine, run_sequences


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "examples/parity.json"


class CoverageTests(unittest.TestCase):
    def report(self, machine, *inputs):
        with redirect_stdout(StringIO()):
            traversed = run_sequences(machine, [Sequence(bits, None) for bits in inputs])
        return coverage_report(machine, traversed).splitlines()

    def test_parity_cli(self):
        run = subprocess.run(
            [sys.executable, ROOT / "fsm.py", PARITY, "--coverage", "--sequences",
             ROOT / "examples/parity-cases.json"], capture_output=True, text=True, check=True,
        )
        self.assertEqual(run.stdout.splitlines()[-3:], [
            "States visited: 2/2 reachable", "Transitions exercised: 3/4 reachable",
            "Missed: even -- input 0, output 0 --> even",
        ])

    def test_reset_only_and_unreachable_cycle(self):
        machine = load_machine(PARITY)
        machine.transitions["unused"] = {bit: Transition("unused", 0) for bit in "01"}
        lines = self.report(machine, "")
        self.assertEqual(lines[:4], [
            "States visited: 1/2 reachable", "Transitions exercised: 0/4 reachable",
            "Unreachable from reset: unused", "Unvisited reachable state: odd",
        ])
        self.assertEqual(sum(line.startswith("Missed:") for line in lines), 4)

    def test_distinct_inputs_to_same_destination(self):
        machine = Machine("idle", {"idle": {bit: Transition("idle", 0) for bit in "01"}})
        self.assertEqual(self.report(machine, "000", "0"), [
            "States visited: 1/1 reachable", "Transitions exercised: 1/2 reachable",
            "Missed: idle -- input 1, output 0 --> idle",
        ])
        self.assertEqual(self.report(machine, "000", "1"), [
            "States visited: 1/1 reachable", "Transitions exercised: 2/2 reachable",
        ])
