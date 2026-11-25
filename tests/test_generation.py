from itertools import product
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fsm import Sequence, Transition, generate_cases, load_machine, load_sequences, simulate


ROOT = Path(__file__).resolve().parents[1]


class GenerationTests(unittest.TestCase):
    def test_shortest_paths_cover_every_reachable_edge(self):
        machine = load_machine(ROOT / "examples/three-ones.json")
        machine.transitions["unused"] = {bit: Transition("unused", 0) for bit in "01"}

        # Independently enumerate words by length to find the first that ends on each edge.
        shortest = {}
        for length in range(1, 4):
            for bits in product("01", repeat=length):
                inputs = "".join(bits)
                source, bit, _ = list(simulate(machine, inputs))[-1]
                shortest.setdefault((source, bit), inputs)
        cases = list(generate_cases(machine, set()))
        self.assertEqual(sorted(case.inputs for case in cases), sorted(shortest.values()))
        self.assertIn(Sequence("111", "001"), cases)
        self.assertEqual(len(shortest), 6)
        self.assertEqual(list(generate_cases(machine, set(shortest))), [])

    def test_combined_suite_replays_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original.json"
            original.write_text('[{"inputs":"101"}]')
            combined = Path(directory) / "combined.json"
            cmd = [sys.executable, ROOT / "fsm.py", ROOT / "examples/parity.json"]
            subprocess.run([*cmd, "--sequences", original, "--generate", combined],
                           check=True, capture_output=True)
            self.assertEqual(load_sequences(combined), [Sequence("101", None), Sequence("0", "0")])
            replay = subprocess.run([*cmd, "--sequences", combined, "--coverage"],
                                    check=True, capture_output=True, text=True)
            self.assertIn("Transitions exercised: 4/4 reachable", replay.stdout)
            before = combined.read_bytes()
            failure = subprocess.run([*cmd, "--generate", combined], capture_output=True)
            self.assertNotEqual(failure.returncode, 0)
            self.assertEqual(combined.read_bytes(), before)
