# pedler.maxcut -- Max-Cut solvers: oscillator, brute force, and QAOA baseline.
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
Max-Cut solvers, for benchmarking the substrate against both ground truth
and an actual quantum approach (Module 2's "Benchmarking Function").

  * solve_max_cut_oscillator -- anti-ferromagnetic coupling (K_ij = -W_ij),
    phase-relaxation, sign(cos(theta)) readout. This is a real technique
    (an "oscillator Ising machine" -- see Wang & Roychowdhury's work on
    coupled-oscillator Ising solvers), not something invented for this
    project.

  * solve_max_cut_bruteforce -- exact answer via enumeration, for small
    graphs only (N <= 20). Ground truth to check the others against.

  * solve_max_cut_qaoa -- an actual p-layer QAOA circuit (standard Max-Cut
    ansatz: H on all qubits, RZZ per edge, RX per qubit, repeated p times),
    optimized classically, evaluated on a Qiskit Statevector -- no Aer or
    IBM hardware needed. This is the "N qubits, one per graph vertex"
    encoding, so it genuinely costs O(2^N) to simulate here -- capped at
    N <= 12 for that reason. This is deliberately a different circuit
    construction from quantum_validator.py's CTQW (which uses ceil(log2(N))
    qubits and doesn't have this blowup); see quantum_validator.py's
    module docstring for why that distinction matters.

qiskit is not installed in this sandbox, so solve_max_cut_qaoa is written
but untested here; solve_max_cut_oscillator and solve_max_cut_bruteforce
use only numpy/scipy and are fully tested (see demo.py output).
"""
import itertools
import time
import numpy as np

from .substrate import JellySubstrate

try:
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    from scipy.optimize import minimize
    QAOA_AVAILABLE = True
except ImportError:
    QAOA_AVAILABLE = False


def cut_value(adjacency, spins):
    adjacency = np.asarray(adjacency, dtype=float)
    A = np.where(spins > 0)[0]
    B = np.where(spins < 0)[0]
    return float(sum(adjacency[i, j] for i in A for j in B))


def solve_max_cut_oscillator(adjacency, duration=20.0, seed=None):
    """Map the graph onto the substrate as an anti-ferromagnetic Ising
    model and read the partition off the relaxed phases."""
    t0 = time.perf_counter()
    adjacency = np.asarray(adjacency, dtype=float)
    N = adjacency.shape[0]

    sub = JellySubstrate(num_nodes=N, seed=seed)
    sub.K = -1.0 * adjacency          # connected nodes repel in phase
    sub.omegas = np.zeros(N)          # dynamics driven by tension only

    rng = np.random.default_rng(seed)
    init_phases = rng.uniform(-0.1, 0.1, N)
    final_phases, R = sub.relax(init_phases, duration=duration)

    spins = np.sign(np.cos(final_phases))
    spins[spins == 0] = 1.0
    elapsed = time.perf_counter() - t0
    return {
        "spins": spins,
        "cut_value": cut_value(adjacency, spins),
        "order_parameter": R,
        "time_seconds": elapsed,
        "final_phases": final_phases,
    }


def solve_max_cut_bruteforce(adjacency):
    t0 = time.perf_counter()
    adjacency = np.asarray(adjacency, dtype=float)
    N = adjacency.shape[0]
    if N > 20:
        raise ValueError("Brute force is only offered for N <= 20 (2^20 combinations).")
    best_val, best_spins = -1.0, None
    for bits in itertools.product([1, -1], repeat=N):
        spins = np.array(bits, dtype=float)
        val = cut_value(adjacency, spins)
        if val > best_val:
            best_val, best_spins = val, spins
    elapsed = time.perf_counter() - t0
    return {"spins": best_spins, "cut_value": best_val, "time_seconds": elapsed}


def solve_max_cut_qaoa(adjacency, p=1, maxiter=150, seed=None):
    if not QAOA_AVAILABLE:
        raise ImportError(
            "qiskit (and scipy.optimize) are required for the QAOA baseline, "
            "and qiskit is not installed in this sandbox. Run "
            "`pip install qiskit` and re-run demo.py to exercise this."
        )
    t0 = time.perf_counter()
    adjacency = np.asarray(adjacency, dtype=float)
    N = adjacency.shape[0]
    if N > 12:
        raise ValueError(
            "This QAOA baseline uses one qubit per graph vertex (2^N "
            "statevector) -- capped at N <= 12 to keep the demo fast."
        )
    edges = [(i, j, adjacency[i, j]) for i in range(N) for j in range(i + 1, N)
              if adjacency[i, j] != 0]

    def build_circuit(params):
        gammas, betas = params[:p], params[p:]
        qc = QuantumCircuit(N)
        qc.h(range(N))
        for layer in range(p):
            for i, j, w in edges:
                qc.rzz(2 * gammas[layer] * w, i, j)
            for q in range(N):
                qc.rx(2 * betas[layer], q)
        return qc

    def expected_cut(params):
        qc = build_circuit(params)
        sv = Statevector.from_label('0' * N).evolve(qc)
        probs = np.asarray(sv.probabilities())
        idx = np.arange(len(probs))
        bits = (idx[:, None] >> np.arange(N)) & 1        # (2^N, N)
        spins = np.where(bits == 0, 1, -1)
        cvals = np.zeros(len(probs))
        for i, j, w in edges:
            cvals += w * (spins[:, i] != spins[:, j])
        return float(np.dot(probs, cvals))

    rng = np.random.default_rng(seed)
    x0 = rng.uniform(0, np.pi, size=2 * p)
    res = minimize(lambda x: -expected_cut(x), x0, method="COBYLA",
                    options={"maxiter": maxiter})

    qc = build_circuit(res.x)
    sv = Statevector.from_label('0' * N).evolve(qc)
    probs = np.asarray(sv.probabilities())
    best_idx = int(np.argmax(probs))
    bits = [(best_idx >> k) & 1 for k in range(N)]
    spins = np.array([1 if b == 0 else -1 for b in bits], dtype=float)
    elapsed = time.perf_counter() - t0
    return {
        "spins": spins,
        "cut_value": cut_value(adjacency, spins),
        "expected_cut_at_optimum": -res.fun,
        "time_seconds": elapsed,
    }


def benchmark_max_cut(adjacency, seed=0):
    """Run every solver that's feasible for this graph's size and return
    a dict of results, so time-to-solution and cut quality are directly
    comparable."""
    adjacency = np.asarray(adjacency, dtype=float)
    N = adjacency.shape[0]
    results = {"oscillator": solve_max_cut_oscillator(adjacency, seed=seed)}
    if N <= 15:
        results["bruteforce"] = solve_max_cut_bruteforce(adjacency)
    if QAOA_AVAILABLE and N <= 12:
        try:
            results["qaoa"] = solve_max_cut_qaoa(adjacency, seed=seed)
        except Exception as e:
            results["qaoa_error"] = str(e)
    return results
