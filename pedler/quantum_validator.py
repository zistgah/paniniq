# pedler.quantum_validator -- Qiskit CTQW validation bridge for the K-matrix.
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
Module 2 -- Quantum infrastructure validation pipeline.

Maps the (real, symmetric, zero-diagonal) coupling matrix K_ij onto a
quantum Hamiltonian H = sum_ij K_ij (|i><j| + |j><i|), builds the unitary
U(t) = exp(-i H t) for a Continuous-Time Quantum Walk, and wraps it as a
Qiskit circuit on ceil(log2(N)) qubits -- a *binary/address* encoding of
the N substrate nodes, not one qubit per node.

NOT importable/usable without `qiskit` installed -- this sandbox has
neither qiskit nor network access to install it, so nothing in this file
has been executed here. It's written to run as-is once qiskit is
available; please run demo.py yourself after `pip install qiskit` to
confirm it behaves as expected in your environment.

Honest note on scaling, because the brief's own numbers contradict its
code: the "classical quantum-walk simulation crashes past ~25-30 nodes,
O(2^N) memory" claim describes an encoding with *one qubit per graph
node* (N qubits -> 2^N-dimensional statevector) -- that's the standard
QAOA Max-Cut ansatz, and it really is exponential in the number of graph
vertices. It is NOT what build_ctqw_circuit implements. Here, N nodes are
addressed with ceil(log2(N)) qubits, so the simulated Hilbert space
dimension is ~N (rounded up to a power of two), not 2^N. The wall you'll
actually hit first with this construction is dense `scipy.linalg.expm` on
a (dim x dim) matrix -- expensive above a few thousand *nodes*, for cubic-
in-dimension reasons, not exponential ones. The two constructions solve
different problems (CTQW position-encoding vs. QAOA spin-encoding) and
scale differently; maxcut.py below implements both so you can see the
difference directly.
"""
import numpy as np
from scipy.linalg import expm

try:
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator, Statevector
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


class QiskitValidator:
    @staticmethod
    def build_hamiltonian(K_matrix):
        """Pad K_ij into a 2^num_qubits x 2^num_qubits Hermitian matrix."""
        K_matrix = np.asarray(K_matrix, dtype=float)
        N = K_matrix.shape[0]
        num_qubits = max(1, int(np.ceil(np.log2(max(N, 2)))))
        dim = 2 ** num_qubits
        H = np.zeros((dim, dim), dtype=complex)
        H[:N, :N] = K_matrix
        return H, num_qubits

    @staticmethod
    def build_ctqw_circuit(K_matrix, evolution_time=1.0, measure=True):
        """Build a Qiskit circuit implementing U(t) = exp(-i H t) as a
        single arbitrary-unitary gate over ceil(log2(N)) qubits."""
        if not QISKIT_AVAILABLE:
            raise ImportError(
                "qiskit is not installed in this environment (and this "
                "sandbox has no network access to install it). Run "
                "`pip install qiskit` and re-run demo.py to exercise this."
            )
        H, num_qubits = QiskitValidator.build_hamiltonian(K_matrix)
        U_t = expm(-1j * H * evolution_time)
        qc = QuantumCircuit(num_qubits)
        qc.unitary(Operator(U_t), list(range(num_qubits)), label="CTQW(K,t)")
        if measure:
            qc.measure_all()
        return qc

    @staticmethod
    def statevector_after(K_matrix, evolution_time=1.0, initial_index=0):
        """Run the CTQW without measurement and return the resulting
        Statevector. Doesn't need Aer or any shot-based backend -- this is
        how compile_to_qiskit's output gets validated in demo.py."""
        if not QISKIT_AVAILABLE:
            raise ImportError(
                "qiskit is not installed in this environment (and this "
                "sandbox has no network access to install it)."
            )
        qc = QiskitValidator.build_ctqw_circuit(K_matrix, evolution_time, measure=False)
        init = Statevector.from_int(initial_index, 2 ** qc.num_qubits)
        return init.evolve(qc)
