# Panini Q

DOI: [10.5281/zenodo.23020648](https://doi.org/10.5281/zenodo.23020648)

Panini Q is the quantum-simulation realization backend of PANINI. This first seed carries the
PEDLER / Jelly-Substrate stack described below: an oscillator substrate, the PEDLER automaton
built on it, a Qiskit validation bridge, Max-Cut benchmarks and a mocked hardware bridge.
Where it sits in the wider architecture is in [CONTEXT.md](CONTEXT.md); every term it uses,
with the nearest term in common use, is in [GLOSSARY.md](GLOSSARY.md).

© 1993–2026 Abhishek Choudhary. All rights reserved. AyeAI.

Gate: `bash ops/verify.sh` · tests: `python3 -m unittest discover -s tests`

# PEDLER / Jelly-Substrate stack

A continuous-wave oscillator substrate ("Jelly Substrate"), the PEDLER
cognitive-automaton lifecycle built on top of it, a Qiskit validation
bridge, a Max-Cut benchmark suite, and a mocked hardware bridge --
implemented as a small Python package (`pedler/`).

This is a seed repository: a working first pass, documented honestly
about what's actually verified versus written-but-untested, so
contributors know exactly what ground they're standing on.

## What this is

- **`pedler.substrate`** -- a network of phase oscillators (Kuramoto
  model), coupled through an evanescent (exponentially distance-decaying)
  matrix. Two implementations behind the same interface: `JellySubstrate`
  (scipy, adaptive-step, fine up to a few hundred nodes) and
  `ClassicalSubstrate` (vectorized PyTorch, GPU-capable, for large node
  counts).
- **`pedler.pedler_engine`** -- the PEDLER automaton: a 6-tuple
  `P = (I, G, U, S, F, *)` where point events map onto an "inclination
  field" over the substrate, phase-locking dynamics decide whether an
  event is novel enough to spawn a new state, and a separate
  prune/consolidate operator keeps the state set from growing forever.
- **`pedler.quantum_validator`** -- maps the substrate's coupling matrix
  onto a Hamiltonian and builds a Qiskit circuit implementing a
  Continuous-Time Quantum Walk (CTQW) on `ceil(log2(N))` qubits, for
  validating the classical dynamics against a real quantum circuit
  construction.
- **`pedler.maxcut`** -- three Max-Cut solvers for benchmarking against
  each other: the oscillator substrate itself (as an anti-ferromagnetic
  Ising machine), brute force (ground truth for small graphs), and a
  standard QAOA circuit.
- **`pedler.hardware_bridge`** -- a mocked serial interface: real,
  tested K-matrix -> byte-frame packing logic, wired to a `MockSerialPort`
  instead of real hardware.
- **`pedler.api`** -- `PedlerEnvironment`, the high-level object that
  wires all of the above together.

## What's actually verified, and how

The seeding pass (27 Sep 2026) ran everything with numpy 2.4.4, scipy 1.17.1 and qiskit
2.5.2; torch and pyserial were not installed. So:

| Piece | Status |
|---|---|
| `JellySubstrate` (Kuramoto phase model, evanescent coupling, structural plasticity) | **Tested** -- `tests/test_core.py`; `demo.py` §1 shows it |
| `PedlerEngine` (inclination field, spawn, decay/prune/consolidate) | **Tested** -- `tests/test_core.py`; `demo.py` §2 shows it |
| Max-Cut via oscillator relaxation, vs. brute-force ground truth | **Tested** -- `tests/test_core.py` against brute force on six graphs, never above the optimum, exact on the bipartite ones; `demo.py` §4 |
| `HardwareBridge` K-matrix -> byte-frame packing | **Tested** -- `tests/test_core.py` decodes the frames (packing logic only; `MockSerialPort` records writes, nothing touches real hardware) |
| K -> Hamiltonian -> unitary math (Hermitian H, unitary U(t)) | **Tested** -- `tests/test_core.py`, independent of qiskit, with plain numpy/scipy |
| `QiskitValidator` circuit construction, statevector run | **Tested** -- `tests/test_core.py`, executed with qiskit 2.5.2; the statevector matches exp(-iHt) computed directly |
| `solve_max_cut_qaoa` | **Tested** -- `tests/test_core.py`, executed with qiskit 2.5.2 |
| `ClassicalSubstrate` (PyTorch, GPU-capable) | **Written, not executed here** -- needs `pip install torch` |

"Tested" here means `tests/test_core.py` asserts it (`python3 -m unittest discover -s tests`,
23 assertions-bearing tests; the qiskit ones skip by name when qiskit is absent). `demo.py`
still shows every piece running. `ClassicalSubstrate` stays written but unexecuted until torch
is installed.

Run `python3 demo.py` after installing the missing packages to exercise
everything; it detects what's present and reports rather than silently
skipping what isn't.

## Install & run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 demo.py
```

Optional extras (each is independent; install any subset):

```bash
pip install qiskit   # unlocks QiskitValidator + solve_max_cut_qaoa
pip install torch    # unlocks ClassicalSubstrate (uses CUDA automatically if available)
pip install pyserial # only needed if you replace MockSerialPort with a real serial.Serial(...)
```

Or, for an editable install using `pyproject.toml`:

```bash
pip install -e ".[quantum,gpu,hardware]"
```

## Honest notes on the spec itself

A few places where the original brief's prose doesn't quite match its
own math -- worth knowing before you build further on this:

1. **"Kuramoto-Duffing"**: the equations given (and implemented) are the
   standard Kuramoto phase model -- each node has a phase only. A real
   Duffing oscillator has its own amplitude with a cubic nonlinear
   restoring force. That's a separate, nontrivial extension (coupled
   amplitude+phase dynamics) if the substrate needs genuine bistability
   -- not implemented here since it wasn't in the given equations.

2. **The "O(2^N), crashes past 25-30 nodes" quantum-scaling claim**: true
   for an encoding with *one qubit per graph vertex* (the standard QAOA
   Max-Cut ansatz -- `solve_max_cut_qaoa`, genuinely exponential, capped
   at N<=12 for that reason). **Not** true of `build_ctqw_circuit`, which
   addresses N nodes with `ceil(log2(N))` qubits -- a Hilbert space of
   size ~N, not 2^N. The two constructions solve different problems and
   belong in the same codebase for comparison, not as substitutes for
   each other.

3. **"Inclination field," "causal tension," "resolution match"** are this
   framework's own vocabulary, not terms from an established physics or
   cognitive-science theory. The code treats them as exactly what the
   equations say -- an exponential-kernel potential field mapped onto
   oscillator phases -- which is a legitimate, well-defined computational
   object in its own right. It's not standard science, and the code
   doesn't claim otherwise. Likewise, `PedlerEngine` implements the given
   equations faithfully; it is not a claim that this simulates cognition,
   consciousness, or any biological substrate.

## What's genuinely mocked vs. real research

The oscillator-based Max-Cut solver (anti-ferromagnetic coupling + phase
relaxation) is a real technique -- see "oscillator Ising machines" (Wang
& Roychowdhury and follow-on work) -- not something invented for this
project. The hardware bridge, by contrast, is a plausible sketch of an
interface, not a protocol any real firmware speaks; adapting the frame
format to whatever microcontroller firmware you actually have, and
physically wiring a serial connection, is unstarted work -- this sandbox
has no way to reach real hardware at all.

## Known issues fixed during hardening

- **`hardware_bridge.k_matrix_to_frames` used to silently zero every
  frame for anti-ferromagnetic matrices** (the kind
  `maxcut.solve_max_cut_oscillator` produces), because it normalized by
  `max(K)` directly instead of by magnitude. Fixed by normalizing on
  `|K_ij|` and carrying sign in its own byte -- see CHANGELOG.md for the
  full writeup. This changed the wire format from 5 bytes/frame to 6;
  nothing else in this repo decoded the old format, so nothing else
  needed updating.

## Next steps

Roughly in order of how self-contained each one is:

1. **Broaden the assertion suite in `tests/test_core.py`.** The first pass
   covers the pieces marked "Tested" above; it should keep growing. A test suite should cover: `JellySubstrate` invariants
   (order parameter in `[0, 1]`, phases wrap to `[0, 2*pi)`), spawn/
   prune/consolidate edge cases (`N=1`, nothing to prune, everything
   pruned), Max-Cut cross-checks against brute force on more graphs than
   just the one 5-node example, and `hardware_bridge` round-trips
   (including the anti-ferromagnetic case the fix above addresses).
2. **Install `torch`** and confirm `ClassicalSubstrate` runs as written. The
   qiskit pieces were executed in the seeding pass and are now under test.
3. **Add a real `Duffing` extension to the substrate** (coupled
   amplitude+phase dynamics) if genuine bistability is needed --
   currently out of scope per note 1 above.
4. **Real hardware bridge**: swap `MockSerialPort` for `serial.Serial(...)`
   and define an actual firmware-side frame protocol once there's a
   physical op-amp / digital-potentiometer mesh to target. Nothing here
   has touched real electronics.
5. **PANINIq** -- a separate, considerably larger planned system (BCI/EEG
   input -> symbolic orchestration -> a physical/quantum ISA ->
   manufacturing/assembly hardware execution, plus a parallel JS
   implementation and a GitHub Pages docs site) is **deliberately not
   scaffolded in this seed.** Building even the scaffold files without a
   real hardware target would produce a README and demo site that read
   as though a brain-to-quantum-to-manufacturing bridge already works,
   when what would exist is unrun mock code. Recommended path: pick one
   concrete, independently useful piece (e.g. just the JS compiler core,
   or just the docs-site interactive demo) and build and label that on
   its own, the same way this README labels real vs. mocked vs. untested
   for the current stack.

## Contributing

Issues and PRs welcome. If you add a module, please keep doing what this
one tries to do: say plainly what's tested, what's mocked, and what's
just written and waiting for a dependency or a piece of hardware --
future contributors (and future you) will thank you.

## License

GPL-3.0-or-later, see `LICENSE`. Copyright (C) 1993-2026 Abhishek
Choudhary. `LICENSE` is the FSF's verbatim text: its sha256,
3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986, is the digest of
<https://www.gnu.org/licenses/gpl-3.0.txt>, and the gate checks it.
