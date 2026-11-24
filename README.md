# Circuit test generator

Validate a deterministic finite-state machine with Python 3.10 or later. The current command reads the reference circuit for later simulation and coverage checks.

```sh
python fsm.py examples/parity.json
python -m unittest discover -s tests -v
```

The example tracks whether an odd number of ones has arrived since reset. The command prints `2 states, 4 transitions, reset=even`.

## Specification

The JSON object has two fields. `reset` names the starting state. `states` maps each state name to its two input cases, `"0"` and `"1"`. Each case gives a declared `next` state and an integer `output` of 0 or 1. Output belongs to the transition being taken (a Mealy machine).

Each state must define exactly one transition for each bit. This gives every input sequence a single interpretation. Unreachable states are valid parts of a specification. The format supports one input bit and one output bit per step.
