"""Read a complete single-input, single-output Mealy machine."""

import argparse
import json
from collections import deque
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Transition:
    next_state: str
    output: int


@dataclass
class Machine:
    reset: str
    transitions: dict[str, dict[str, Transition]]


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def require_fields(value, fields, location):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{location} requires exactly these keys: {', '.join(sorted(fields))}")


def load_machine(path: Path) -> Machine:
    spec = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
    require_fields(spec, {"reset", "states"}, "machine")
    states = spec["states"]
    if not isinstance(states, dict) or not states or any(not name.strip() for name in states):
        raise ValueError("states must be a nonempty object with nonblank state names")
    reset = spec["reset"]
    if not isinstance(reset, str) or reset not in states:
        raise ValueError("reset must name a declared state")

    transitions = {}
    for state, inputs in states.items():
        require_fields(inputs, {"0", "1"}, f"state {state!r}")
        transitions[state] = {}
        for bit, edge in inputs.items():
            location = f"state {state!r} input {bit}"
            require_fields(edge, {"next", "output"}, location)
            target, output = edge["next"], edge["output"]
            if not isinstance(target, str) or target not in states:
                raise ValueError(f"{location}: next must name a declared state")
            if type(output) is not int or output not in (0, 1):
                raise ValueError(f"{location}: output must be the integer 0 or 1")
            transitions[state][bit] = Transition(target, output)
    return Machine(reset, transitions)


@dataclass(frozen=True)
class Sequence:
    inputs: str
    expected: str | None


def load_sequences(path: Path) -> list[Sequence]:
    rows = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
    if not isinstance(rows, list) or not rows:
        raise ValueError("expected a nonempty array of sequences")
    sequences = []
    for number, row in enumerate(rows, 1):
        label = f"sequence {number}"
        if not isinstance(row, dict) or "inputs" not in row or set(row) - {"inputs", "expected"}:
            raise ValueError(f"{label} requires inputs and accepts an optional expected field")
        for key, bits in row.items():
            if not isinstance(bits, str) or any(bit not in "01" for bit in bits):
                raise ValueError(f"{label}: {key} must be a string of binary digits")
        inputs = row["inputs"]
        expected = row.get("expected")
        if expected is not None and len(expected) != len(inputs):
            raise ValueError(f"{label}: expected must contain one bit per input")
        sequences.append(Sequence(inputs, expected))
    return sequences


def simulate(machine: Machine, inputs: str) -> Iterator[tuple[str, str, Transition]]:
    state = machine.reset
    for bit in inputs:
        edge = machine.transitions[state][bit]
        yield state, bit, edge
        state = edge.next_state


def run_sequences(machine: Machine, sequences: list[Sequence]) -> set[tuple[str, str]]:
    traversed = set()
    for number, sequence in enumerate(sequences, 1):
        outputs = []
        state = machine.reset
        for step, (source, bit, edge) in enumerate(simulate(machine, sequence.inputs), 1):
            output = str(edge.output)
            if sequence.expected is not None and sequence.expected[step - 1] != output:
                raise ValueError(
                    f"sequence {number}, step {step}: state={source}, input={bit}, "
                    f"expected={sequence.expected[step - 1]}, actual={output}"
                )
            traversed.add((source, bit))
            outputs.append(output)
            state = edge.next_state
        print(f"sequence {number}: outputs={''.join(outputs)!r}, final={state}")
    return traversed


def search_from_reset(machine: Machine) -> dict[str, tuple[str, str] | None]:
    """Record the first (source state, input) that reaches each state."""
    parents = {machine.reset: None}
    pending = deque([machine.reset])
    while pending:
        source = pending.popleft()
        for bit in ("0", "1"):
            target = machine.transitions[source][bit].next_state
            if target not in parents:
                parents[target] = (source, bit)
                pending.append(target)
    return parents


def reachable_states(machine: Machine) -> set[str]:
    return set(search_from_reset(machine))


def generate_cases(machine: Machine, traversed: set[tuple[str, str]]) -> Iterator[Sequence]:
    parents = search_from_reset(machine)
    for source in parents:
        for bit in ("0", "1"):
            if (source, bit) in traversed:
                continue
            path = [bit]
            state = source
            while parents[state] is not None:
                state, incoming = parents[state]
                path.append(incoming)
            inputs = "".join(reversed(path))
            expected = "".join(str(edge.output) for _, _, edge in simulate(machine, inputs))
            yield Sequence(inputs, expected)


def coverage_report(machine: Machine, traversed: set[tuple[str, str]]) -> str:
    reachable = reachable_states(machine)
    possible = {(state, bit) for state in reachable for bit in machine.transitions[state]}
    visited = {machine.reset}
    for state, bit in traversed:
        visited.add(machine.transitions[state][bit].next_state)

    lines = [
        f"States visited: {len(visited)}/{len(reachable)} reachable",
        f"Transitions exercised: {len(traversed)}/{len(possible)} reachable",
    ]
    for state in sorted(machine.transitions.keys() - reachable):
        lines.append(f"Unreachable from reset: {state}")
    for state in sorted(reachable - visited):
        lines.append(f"Unvisited reachable state: {state}")
    for state, bit in sorted(possible - traversed):
        edge = machine.transitions[state][bit]
        lines.append(f"Missed: {state} -- input {bit}, output {edge.output} --> {edge.next_state}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--sequences", type=Path, help="simulate a JSON array of test cases")
    parser.add_argument("--coverage", action="store_true", help="report coverage of the supplied sequences")
    parser.add_argument("--generate", type=Path, metavar="FILE",
                        help="write original and generated cases to a new JSON file")
    args = parser.parse_args()
    if args.coverage and args.sequences is None:
        parser.error("--coverage requires --sequences")
    try:
        machine = load_machine(args.spec)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{args.spec}: {exc}\n")
    edges = sum(len(row) for row in machine.transitions.values())
    print(f"{len(machine.transitions)} states, {edges} transitions, reset={machine.reset}")
    sequences = []
    traversed = set()
    if args.sequences is not None:
        try:
            sequences = load_sequences(args.sequences)
            traversed = run_sequences(machine, sequences)
            if args.coverage:
                print(coverage_report(machine, traversed))
        except (OSError, ValueError) as exc:
            parser.exit(1, f"{args.sequences}: {exc}\n")
    if args.generate is not None:
        additions = list(generate_cases(machine, traversed))
        cases = [asdict(case) if case.expected is not None else {"inputs": case.inputs}
                 for case in sequences + additions]
        try:
            with args.generate.open("x", encoding="utf-8") as out:
                json.dump(cases, out, indent=2)
                out.write("\n")
        except OSError as exc:
            parser.exit(1, f"{args.generate}: {exc}\n")
        print(f"Added {len(additions)} cases; wrote {len(cases)} to {args.generate}")


if __name__ == "__main__":
    main()
