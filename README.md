# Circuit test generator

Validate a deterministic finite-state machine with Python 3.10 or later. Run binary input sequences against its transition table and check the output at each step.

```sh
python fsm.py examples/parity.json
python -m unittest discover -s tests -v
```

The example tracks whether an odd number of ones has arrived since reset. The command prints `2 states, 4 transitions, reset=even`.

## Specification

The JSON object has two fields. `reset` names the starting state. `states` maps each state name to its two input cases, `"0"` and `"1"`. Each case gives a declared `next` state and an integer `output` of 0 or 1. Output belongs to the transition being taken (a Mealy machine).

Each state must define exactly one transition for each bit. This gives every input sequence a single interpretation. Unreachable states are valid parts of a specification. The format supports one input bit and one output bit per step.

## Run sequences

```sh
python fsm.py examples/parity.json --sequences examples/parity-cases.json
```

Each entry starts from reset. Supply input bits as a string to preserve leading zeros.
Include an equally long `expected` bit string to check outputs, or omit it to print
the reference outputs. An empty string exercises reset alone.

The sample produces `11` and ends in `odd` for the first case. The second produces
`110` and ends in `even`. A mismatch stops the command with exit status 1 and
reports the case, one-based step, source state, input, expected bit and actual bit.

## Measure coverage

```sh
python fsm.py examples/parity.json --sequences examples/parity-cases.json --coverage
```

The sample visits both reachable states and exercises 3 of 4 reachable transitions.
It misses input 0 in state `even`, which outputs 0 and stays in `even`.

The report counts each distinct (source state, input bit) pair once across all
cases. Reset counts as a visit even for an empty input string. A traversal of
the reference table determines which states any input sequence can reach from
reset. The report lists unreachable states separately and excludes their edges
from the denominator. Coverage is printed after all expected outputs pass.
