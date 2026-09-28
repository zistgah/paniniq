# CONTEXT: cold-start map for Panini Q

© 1993–2026 Abhishek Choudhary. All rights reserved. AyeAI.

A fresh session or contributor rebuilds working context from this file and the sources it
names. Read [CONTRACT.md](CONTRACT.md) first, then this, then [README.md](README.md) for what
is tested, mocked and open, then [GLOSSARY.md](GLOSSARY.md).

## Mission

The quantum-simulation realization backend of PANINI: substrates that programs can be realised
on and validated against, starting with an oscillator network, the PEDLER automaton on it, and
a bridge that checks the classical dynamics against a quantum circuit.

## Where it sits

The author's layering (27 Sep 2026):

1. **Front end.** ILM and the language parsers of tajziya, Sanskrit first: the languages a
   program or a prompt can arrive in (doi:10.5281/zenodo.22982238).
2. **Middleware.** PANINI's own front ends, 37 of them in the merged release, from `ada.pni`
   to `zig.pni` and `sysml.pni`, and the PANINI language itself (doi:10.5281/zenodo.22103243).
3. **Core PANINI.** The construct model: common semantics plus decorators.
4. **Realization backends.** Where a program meets a substrate. Panini Q is one of them.

The author's three Acts (his note "3 Act ASI ∧ Panini"):

- **Act I, AGI complete.** The front end, and the cyclers with genie as agents and harnesses.
  Process cyclers are designed and run in AAB.
- **Act II, post-AGI to ASI.** Cognitive enablement modules and the accelerators. Panini Q's
  substrate, an oscillator Ising machine with a learning automaton on it, belongs here.
- **Act III, post-ASI.** Brain-computer interfaces; Synthematic Pragmatic Realism leading to
  TransEg, the transferred alter ego; the habitats: Humanesque, with Zistgah (Earth, Moon and
  Bahram, Mars), Kaivalyik and Cosmopolis.

Placement says when a piece matters most, not when work on it starts.

## State

| Piece | State |
|---|---|
| `JellySubstrate`, `PedlerEngine`, Max-Cut solvers, frame packing, Hamiltonian and unitary | tested by `tests/test_core.py` |
| `QiskitValidator`, `solve_max_cut_qaoa` | tested, executed with qiskit 2.5.2; skipped by name without qiskit |
| `ClassicalSubstrate` (torch) | written, not executed |
| Hardware bridge | packing tested; the port is mocked; no firmware exists |

## Open

- PEDLER's canonical inclination is signed, on edges, in [-1, +1], decaying with its sign kept.
  This code's inclination field is non-negative and on nodes. Which one the substrate should
  carry is the author's call; until then both are named, neither is changed.
- A Duffing extension (amplitude as well as phase) if genuine bistability is wanted.
- A real hardware bridge and firmware protocol.
- The larger PANINIq system in the README's next steps (BCI or EEG input, symbolic
  orchestration, a physical or quantum ISA, manufacturing execution) is planned, not built.

## Rules while working here

Say plainly what is tested, mocked or only written. Keep the author's terms and add the common
term beside them; never replace one with the other. Stay inside the repository folder. Run
`bash ops/verify.sh` before proposing anything.
