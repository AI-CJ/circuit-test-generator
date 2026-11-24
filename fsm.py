"""Read a complete single-input, single-output Mealy machine."""

import argparse
import json
from dataclasses import dataclass
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    args = parser.parse_args()
    try:
        machine = load_machine(args.spec)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{args.spec}: {exc}\n")
    edges = sum(len(row) for row in machine.transitions.values())
    print(f"{len(machine.transitions)} states, {edges} transitions, reset={machine.reset}")


if __name__ == "__main__":
    main()
