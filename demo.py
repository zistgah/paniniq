# pedler demo -- exercises every module, reporting rather than silently skipping what needs qiskit/torch.
# Copyright (C) 1993-2026  Abhishek Choudhary
# © 1993–2026 Abhishek Choudhary. All rights reserved. AyeAI.
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Functional test script -- runs everything that's installed in the current
environment, and clearly reports (rather than silently skipping) anything
that needs a library not present here (qiskit, torch).

Sections:
  1. Point event -> inclination field -> substrate relaxation -> spawn
  2. Lifecycle maintenance (decay / prune / consolidate)
  3. Compile to Qiskit + statevector validation            [needs qiskit]
  4. Max-Cut benchmark: oscillator vs. brute force vs. QAOA [QAOA needs qiskit]
  5. Hardware bridge (mocked serial export)
  6. ClassicalSubstrate (PyTorch) scaling demo              [needs torch]
"""
import time
import numpy as np

from pedler import (
    PedlerEnvironment, QISKIT_AVAILABLE, TORCH_AVAILABLE,
    ClassicalSubstrate, maxcut,
)

SEP = "=" * 60


def section(title):
    print(f"\n{SEP}\n{title}\n{SEP}")


def main():
    # ---------------------------------------------------------------
    section("1. Point events -> inclination field -> relaxation -> spawn")
    env = PedlerEnvironment(initial_nodes=4, seed=42)

    # Whether a given point event ends up "novel" (R below threshold, so it
    # spawns a node) isn't simply a function of distance between events --
    # it depends on how the initial phase pattern that event induces
    # interacts with the substrate's existing coupling topology. Rather
    # than assert an outcome in advance, novelty_threshold=0.5 is set high
    # enough that this random seed is expected to produce at least one
    # spawn, and the printed R values below show exactly which ones did.
    events = [
        [0.85, 0.12, 0.44],
        [0.10, 0.90, 0.30],
        [0.83, 0.14, 0.46],
    ]
    prev_cardinality = len(env.engine.S)
    for k, event in enumerate(events):
        result = env.inject_point_event(event, novelty_threshold=0.5)
        spawned = result['state_cardinality'] > prev_cardinality
        prev_cardinality = result['state_cardinality']
        print(f"event {k}: point={event}")
        print(f"   order parameter R = {result['order_parameter_R']:.4f}   "
              f"|S| = {result['state_cardinality']}"
              f"{'   -> SPAWNED a node' if spawned else ''}")

    # ---------------------------------------------------------------
    section("2. Lifecycle maintenance (decay priors, then prune/consolidate)")
    # Repeat the *first* event a few more times so its prior stays strong
    # while anything spawned from a one-off point event decays away.
    for _ in range(3):
        env.inject_point_event(events[0], novelty_threshold=0.25)
    print(f"|S| before maintenance: {len(env.engine.S)}")
    n_pruned, n_merged = env.run_lifecycle_maintenance(lam=0.5, dt=2.0, prior_epsilon=0.05)
    print(f"pruned={n_pruned}, merged={n_merged}")
    print(f"|S| after maintenance:  {len(env.engine.S)}")

    # ---------------------------------------------------------------
    section("3. Compile to Qiskit + statevector validation")
    if QISKIT_AVAILABLE:
        qc = env.compile_to_qiskit(evolution_time=0.5)
        print(qc.draw(output="text"))
        sv = env.validator.statevector_after(env.substrate.K, evolution_time=0.5)
        probs = np.asarray(sv.probabilities())
        print(f"statevector dim = {len(probs)}, sums to {probs.sum():.6f} (unitarity check)")
    else:
        print("SKIPPED: qiskit is not installed in this sandbox (no network access "
              "to install it here). This code is written and ready -- "
              "`pip install qiskit` in your own environment and re-run this script.")

    # ---------------------------------------------------------------
    section("4. Max-Cut benchmark: oscillator vs. brute force vs. QAOA")
    butterfly = np.array([
        [0, 1, 1, 1, 1],
        [1, 0, 1, 0, 0],
        [1, 1, 0, 0, 0],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 1, 0],
    ], dtype=float)
    results = maxcut.benchmark_max_cut(butterfly, seed=7)
    for method, res in results.items():
        if method.endswith("_error"):
            print(f"{method}: {res}")
            continue
        print(f"{method:12s} cut_value={res['cut_value']:.1f}  "
              f"time={res['time_seconds']*1000:.2f} ms")
    if not maxcut.QAOA_AVAILABLE:
        print("QAOA baseline SKIPPED: qiskit is not installed in this sandbox. "
              "Code is written in pedler/maxcut.py::solve_max_cut_qaoa -- "
              "install qiskit and re-run to exercise it.")

    # ---------------------------------------------------------------
    section("5. Hardware bridge (mocked -- no real serial device exists here)")
    frames = env.push_k_matrix_to_hardware()
    print(f"{len(frames)} frame(s) 'sent' to {env.hardware.port.port_name}")
    if frames:
        print(f"sample frame (hex): {frames[0].hex()}")
    print("This only proves the K-matrix -> byte-frame packing is correct. "
          "No physical oscillator was touched -- there's no serial port or "
          "USB device available in this sandbox.")

    # ---------------------------------------------------------------
    section("6. ClassicalSubstrate (PyTorch) scaling demo")
    if TORCH_AVAILABLE:
        import torch
        n_nodes = 2000
        sub = ClassicalSubstrate(num_nodes=n_nodes, seed=1)
        init_phases = torch.rand(n_nodes) * 2 * np.pi
        t0 = time.perf_counter()
        _, R = sub.relax(init_phases, dt=0.01, steps=300)
        elapsed = time.perf_counter() - t0
        print(f"device={sub.device}, N={n_nodes}, steps=300 -> "
              f"R={R:.4f} in {elapsed:.3f}s")
    else:
        print("SKIPPED: torch is not installed in this sandbox (no network access "
              "to install it here). pedler/substrate.py::ClassicalSubstrate is "
              "written and ready -- `pip install torch` and re-run this script; "
              "it will automatically use a GPU if `torch.cuda.is_available()`.")


if __name__ == "__main__":
    main()
