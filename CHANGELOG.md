# Changelog

## 0.1.0 -- initial seed (2026-09-27)

First public seed of the four modules described in the brief: the
`JellySubstrate` oscillator, the `PedlerEngine` cognitive-automaton
lifecycle, the `QiskitValidator` quantum bridge, and the high-level
`PedlerEnvironment` API -- plus a Max-Cut benchmark suite and a mocked
`HardwareBridge`. See README.md for what's actually tested versus
written-but-unexecuted in this sandbox.

### Fixed

- **`hardware_bridge.k_matrix_to_frames` silently zeroed anti-ferromagnetic
  matrices.** The original 5-byte frame format
  (`[header][i][j][magnitude]`) normalized `K_ij` by `max(K)` directly.
  For any all-non-positive `K` -- which is exactly what
  `maxcut.solve_max_cut_oscillator` produces (`K = -adjacency`) -- `max(K)`
  is 0, so every edge's ratio came out `<= 0` and was clipped to
  `byte_val = 0`. The bridge emitted uninformative all-zero-magnitude
  frames for every anti-ferromagnetic matrix in this codebase, with no
  error or warning.

  Fixed by normalizing on `|K_ij|` and carrying sign in its own byte:
  `[header 2B][i 1B][j 1B][sign 1B][magnitude 1B]`. This is a wire-format
  change (5 bytes/frame -> 6); nothing in this repo decodes the frame
  format yet, so nothing else needed updating. Found during a hardening
  pass, before any hardware ever saw the old format.

### Seeding pass (27 Sep 2026), before the first push

- `tests/test_core.py`: 23 tests with assertions replace inspection by eye. The qiskit pieces
  (`QiskitValidator`, `solve_max_cut_qaoa`) were executed with qiskit 2.5.2 and are under test.
- `demo.py` printed `|S| before maintenance` before three further point events, one of which
  can spawn a state, so the count appeared to rise across a prune. It now prints after them.
- `LICENSE` replaced by the FSF's verbatim GPL-3.0 text; the earlier file had the same words,
  rewrapped.
- Each source file carries the AyeAI copyright line and an SPDX identifier.
- Added `ops/verify.sh` (the gate), `CONTRACT.md`, `CONTEXT.md`, `GLOSSARY.md`, `AGENTS.md`,
  `PROVENANCE.md`, `CITATION.cff`, `misty.json` and `docs/index.html`.

## Unreleased / not yet done

See README.md's "Next steps" section -- a real `pytest` suite (this
version is still verified by `demo.py`'s printed output, not
assertions), broader Max-Cut benchmark graphs, `qiskit`/`torch`
execution once available, and the separate PANINIq system are all
still open.
