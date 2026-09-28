# © 1993–2026 Abhishek Choudhary. All rights reserved. AyeAI.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Assertions for the Panini Q seed: substrate, PEDLER engine, Max-Cut, frames, quantum bridge.

Run with:  python3 -m unittest discover -s tests
Pieces that need qiskit or torch are skipped, by name, when the package is absent.
"""
import math
import os
import sys
import unittest

import numpy as np
from scipy.linalg import expm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pedler import maxcut                                    # noqa: E402
from pedler.api import PedlerEnvironment                     # noqa: E402
from pedler.hardware_bridge import HardwareBridge, MockSerialPort  # noqa: E402
from pedler.pedler_engine import PedlerEngine                # noqa: E402
from pedler.quantum_validator import QISKIT_AVAILABLE, QiskitValidator  # noqa: E402
from pedler.substrate import JellySubstrate                  # noqa: E402

TWO_PI = 2 * math.pi


def graph(n, edges):
    a = np.zeros((n, n))
    for i, j in edges:
        a[i, j] = a[j, i] = 1.0
    return a


TRIANGLE = graph(3, [(0, 1), (1, 2), (0, 2)])                       # best cut 2
SQUARE = graph(4, [(0, 1), (1, 2), (2, 3), (3, 0)])                 # best cut 4, bipartite
K4 = graph(4, [(i, j) for i in range(4) for j in range(i + 1, 4)])  # best cut 4
PENTAGON = graph(5, [(i, (i + 1) % 5) for i in range(5)])           # best cut 4
K23 = graph(5, [(i, j) for i in (0, 1) for j in (2, 3, 4)])         # best cut 6, bipartite
PETERSEN = graph(10, [(i, (i + 1) % 5) for i in range(5)] + [(i, i + 5) for i in range(5)]
                 + [(5 + i, 5 + (i + 2) % 5) for i in range(5)])   # best cut 12
KNOWN = [(TRIANGLE, 2), (SQUARE, 4), (K4, 4), (PENTAGON, 4), (K23, 6), (PETERSEN, 12)]


class Substrate(unittest.TestCase):
    def test_coupling_is_symmetric_evanescent_and_zero_on_the_diagonal(self):
        s = JellySubstrate(num_nodes=6, alpha=0.5, K0=1.0, seed=1)
        self.assertTrue(np.allclose(s.K, s.K.T))
        self.assertTrue(np.all(np.diag(s.K) == 0))
        off = s.K[~np.eye(6, dtype=bool)]
        self.assertTrue(np.all(off > 0) and np.all(off <= 1.0))

    def test_relaxation_returns_wrapped_phases_and_an_order_parameter_in_the_unit_interval(self):
        s = JellySubstrate(num_nodes=5, seed=2)
        phases, r = s.relax(np.linspace(0, 3, 5), duration=1.0)
        self.assertEqual(phases.shape, (5,))
        self.assertTrue(np.all(phases >= 0) and np.all(phases < TWO_PI))
        self.assertTrue(0.0 <= r <= 1.0)

    def test_growth_and_pruning_keep_every_array_in_step(self):
        s = JellySubstrate(num_nodes=3, seed=3)
        s.add_node([0.5, 0.5, 0.5])
        self.assertEqual((s.N, s.K.shape, s.coords.shape, s.omegas.shape), (4, (4, 4), (4, 3), (4,)))
        s.remove_nodes([True, False, True, True])
        self.assertEqual((s.N, s.K.shape, s.coords.shape, s.omegas.shape), (3, (3, 3), (3, 3), (3,)))

    def test_bad_sizes_are_refused(self):
        with self.assertRaises(ValueError):
            JellySubstrate(num_nodes=0)
        s = JellySubstrate(num_nodes=3, seed=4)
        with self.assertRaises(ValueError):
            s.relax(np.zeros(4))
        with self.assertRaises(ValueError):
            s.remove_nodes([True, False])


class Engine(unittest.TestCase):
    def setUp(self):
        self.sub = JellySubstrate(num_nodes=4, seed=5)
        self.eng = PedlerEngine(self.sub, gamma=1.0, seed=5)

    def in_step(self):
        n = self.sub.N
        self.assertEqual((len(self.eng.S), len(self.eng.eta), len(self.eng.wc), len(self.eng.F)), (n, n, n, n))

    def test_the_inclination_field_is_one_non_negative_value_per_state(self):
        field = self.eng.compute_inclination_field([0.2, 0.4, 0.6])
        self.assertEqual(field.shape, (4,))
        self.assertTrue(np.all(field >= 0))

    def test_a_point_event_strengthens_priors(self):
        before = self.eng.eta.copy()
        self.eng.process_point_event([0.2, 0.4, 0.6], novelty_threshold=0.0)
        self.assertTrue(np.all(self.eng.eta > before))

    def test_a_novel_event_spawns_a_state_and_a_familiar_one_does_not(self):
        self.eng.process_point_event([0.1, 0.2, 0.3], novelty_threshold=0.0)   # R < 0 never holds
        self.assertEqual(len(self.eng.S), 4)
        self.eng.process_point_event([0.9, 0.8, 0.7], novelty_threshold=1.01)  # R < 1.01 always holds
        self.assertEqual(len(self.eng.S), 5)
        self.in_step()

    def test_decay_is_exponential(self):
        self.eng.eta = np.full(4, 0.8)
        self.eng.decay_priors(lam=0.5, dt=2.0)
        self.assertTrue(np.allclose(self.eng.eta, 0.8 * math.exp(-1.0)))

    def test_prune_removes_exactly_the_faded_states(self):
        self.eng.eta = np.array([0.5, 0.001, 0.5, 0.001])
        pruned, merged = self.eng.prune_and_consolidate(prior_epsilon=0.02)
        self.assertEqual((pruned, merged), (2, 0))
        self.assertEqual(self.sub.N, 2)
        self.in_step()

    def test_nothing_to_prune_and_a_single_state_are_left_alone(self):
        self.eng.eta = np.full(4, 0.5)
        self.assertEqual(self.eng.prune_and_consolidate(prior_epsilon=0.02), (0, 0))
        self.assertEqual(self.sub.N, 4)
        lone = PedlerEngine(JellySubstrate(num_nodes=1, seed=6))
        self.assertEqual(lone.prune_and_consolidate(), (0, 0))

    def test_the_environment_reports_the_cardinality_it_holds(self):
        env = PedlerEnvironment(initial_nodes=4, seed=7)
        out = env.inject_point_event([0.3, 0.3, 0.3], novelty_threshold=1.01)
        self.assertEqual(out["state_cardinality"], len(env.engine.S))
        self.assertEqual(out["state_cardinality"], env.substrate.N)


class MaxCut(unittest.TestCase):
    def test_brute_force_finds_the_known_optimum(self):
        for adj, best in KNOWN:
            self.assertEqual(maxcut.solve_max_cut_bruteforce(adj)["cut_value"], best)

    def test_cut_value_counts_crossing_edges(self):
        self.assertEqual(maxcut.cut_value(SQUARE, np.array([1, -1, 1, -1])), 4.0)
        self.assertEqual(maxcut.cut_value(SQUARE, np.array([1, 1, 1, 1])), 0.0)

    def test_the_oscillator_gives_a_valid_cut_never_above_the_optimum(self):
        for adj, best in KNOWN:
            r = maxcut.solve_max_cut_oscillator(adj, seed=0)
            self.assertTrue(set(np.unique(r["spins"])) <= {-1.0, 1.0})
            self.assertEqual(r["cut_value"], maxcut.cut_value(adj, r["spins"]))
            self.assertLessEqual(r["cut_value"], best)

    def test_the_oscillator_solves_the_bipartite_graphs(self):
        for adj, best in ((SQUARE, 4), (K23, 6)):
            self.assertEqual(maxcut.solve_max_cut_oscillator(adj, seed=0)["cut_value"], best)

    @unittest.skipUnless(maxcut.QAOA_AVAILABLE, "qiskit is not installed; pip install qiskit")
    def test_qaoa_gives_a_valid_cut_never_above_the_optimum(self):
        for adj, best in ((SQUARE, 4), (PENTAGON, 4)):
            r = maxcut.solve_max_cut_qaoa(adj, seed=0)
            self.assertEqual(r["cut_value"], maxcut.cut_value(adj, r["spins"]))
            self.assertLessEqual(r["cut_value"], best)
        self.assertEqual(maxcut.solve_max_cut_qaoa(SQUARE, seed=0)["cut_value"], 4)


class Frames(unittest.TestCase):
    @staticmethod
    def decode(frame):
        return frame[:2], frame[2], frame[3], frame[4], frame[5]

    def test_one_six_byte_frame_per_upper_triangle_edge(self):
        frames = HardwareBridge.k_matrix_to_frames(JellySubstrate(num_nodes=5, seed=8).K)
        self.assertEqual(len(frames), 10)
        self.assertTrue(all(len(f) == 6 and f[:2] == b"\xAA\x55" for f in frames))

    def test_sign_and_magnitude_round_trip_for_mixed_couplings(self):
        k = np.array([[0.0, 0.5, -1.0], [0.5, 0.0, 0.25], [-1.0, 0.25, 0.0]])
        got = {(i, j): (sign, mag) for _, i, j, sign, mag in map(self.decode, HardwareBridge.k_matrix_to_frames(k))}
        self.assertEqual(got, {(0, 1): (0, 128), (0, 2): (1, 255), (1, 2): (0, 64)})

    def test_anti_ferromagnetic_matrices_are_no_longer_zeroed(self):
        frames = HardwareBridge.k_matrix_to_frames(-SQUARE)
        edges = {(i, j) for _, i, j, sign, mag in map(self.decode, frames) if sign == 1 and mag == 255}
        self.assertEqual(edges, {(0, 1), (1, 2), (2, 3), (0, 3)})

    def test_the_mock_port_records_every_frame_it_is_sent(self):
        port = MockSerialPort()
        sent = HardwareBridge(port).export_k_matrix_to_serial(K4)
        self.assertEqual(port.sent_frames, sent)
        self.assertEqual(len(sent), 6)


class Quantum(unittest.TestCase):
    def test_the_hamiltonian_is_hermitian_and_its_evolution_unitary(self):
        k = JellySubstrate(num_nodes=5, seed=9).K
        h, q = QiskitValidator.build_hamiltonian(k)
        self.assertEqual((q, h.shape), (3, (8, 8)))
        self.assertTrue(np.allclose(h, h.conj().T))
        u = expm(-1j * h * 0.7)
        self.assertTrue(np.allclose(u @ u.conj().T, np.eye(8)))

    def test_n_nodes_take_ceil_log2_n_qubits_not_n(self):
        for n, q in ((2, 1), (3, 2), (4, 2), (5, 3), (9, 4), (16, 4), (17, 5)):
            self.assertEqual(QiskitValidator.build_hamiltonian(np.zeros((n, n)))[1], q)

    @unittest.skipUnless(QISKIT_AVAILABLE, "qiskit is not installed; pip install qiskit")
    def test_the_ctqw_circuit_runs_and_keeps_the_state_normalised(self):
        k = JellySubstrate(num_nodes=5, seed=10).K
        self.assertEqual(QiskitValidator.build_ctqw_circuit(k, 0.5).num_qubits, 3)
        sv = QiskitValidator.statevector_after(k, evolution_time=0.5)
        self.assertAlmostEqual(float(np.sum(np.abs(np.asarray(sv.data)) ** 2)), 1.0, places=9)
        h, _ = QiskitValidator.build_hamiltonian(k)
        want = expm(-1j * h * 0.5)[:, 0]
        self.assertTrue(np.allclose(np.asarray(sv.data), want))


if __name__ == "__main__":
    unittest.main()
