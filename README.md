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

## Generate cases for missed transitions

```sh
python fsm.py examples/parity.json --sequences examples/parity-cases.json --generate parity-full.json
python fsm.py examples/parity.json --sequences parity-full.json --coverage
```

The new JSON file contains the original cases followed by one case per missed
reachable transition. The parity example adds input `0` with expected output
`0`. Replaying the file covers 4/4 reachable transitions. Choose a fresh output
filename each time.

Omit `--sequences` to generate a suite from scratch. For `examples/three-ones.json`,
this produces six cases covering all six transitions. Input `111` produces
`001`: the circuit signals the third consecutive one. Breadth-first search
finds a shortest path from reset to each source state, exploring input 0 first
to break ties. Appending the target input gives a shortest case for that edge.
Different cases can repeat prefixes, so the combined suite can contain redundant steps.

## Run the cases in Logisim Evolution

Install Java 21 and download the `logisim-evolution-5.0.0-all.jar` asset from
the [5.0.0 release](https://github.com/logisim-evolution/logisim-evolution/releases/tag/v5.0.0).
From the repository root, run both examples with the path to your JAR:

```sh
python tests/check_logisim.py /path/to/logisim-evolution-5.0.0-all.jar
```

On Linux without a desktop, prefix the command with `xvfb-run -a`. The check
generates fresh cases, exports them, and reads the simulator's pass/fail counts.
Parity covers 4/4 reachable transitions in 16 vector rows. The three-ones
detector covers 6/6 in 30 rows. Both circuits are in `examples/machines.circ`.

To inspect the vectors yourself, use the `parity-full.json` file generated above:

```sh
python fsm.py examples/parity.json --sequences parity-full.json --logisim parity.txt
java -jar /path/to/logisim-evolution-5.0.0-all.jar --test-vector parity parity.txt examples/machines.circ
```

To test another circuit, expose four single-bit pins named `Bit`, `Clock`,
`Reset`, and `Result`. Each case starts with an active-high asynchronous reset.
The circuit must enter the state named by the specification's `reset` field.
For each input, the low-clock row checks the Mealy output. The next row holds
the input steady and raises the clock so the flip-flops store the next state.
`<DC>` skips the output check during reset and on the rising edge. Each case
has its own `<set>` number, and `<seq>` orders its rows. The export checks
observable output bits. It assumes one rising-edge clock and settled signals.
