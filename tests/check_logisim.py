"""Run the generated suites against the two example circuits in Logisim Evolution."""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def check_circuit(jar, directory, spec_name, circuit, expected_rows):
    spec = ROOT / "examples" / f"{spec_name}.json"
    cases = directory / f"{spec_name}.json"
    vectors = directory / f"{spec_name}.txt"
    cli = [sys.executable, ROOT / "fsm.py", spec]
    subprocess.run([*cli, "--generate", cases], check=True)
    subprocess.run([*cli, "--sequences", cases, "--coverage", "--logisim", vectors], check=True)
    result = subprocess.run(
        ["java", "-jar", jar, "--locale", "en", "--test-vector", circuit, vectors,
         ROOT / "examples/machines.circ"],
        capture_output=True, text=True, timeout=60,
    )
    output = result.stdout + result.stderr
    # Version 5.0.0 can exit successfully even when a vector fails.
    summary = f"Passed: {expected_rows}, Failed: 0"
    if result.returncode or summary not in output.splitlines():
        raise SystemExit(f"{circuit}: {output}")
    print(f"{circuit}: {summary}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jar", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        check_circuit(args.jar, Path(temporary), "parity", "parity", 16)
        check_circuit(args.jar, Path(temporary), "three-ones", "three_ones", 30)
