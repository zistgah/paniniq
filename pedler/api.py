# pedler.api -- high-level PedlerEnvironment API tying the stack together.
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
Module 4 -- high-level programming layer.

PedlerEnvironment wraps the substrate, the PEDLER engine, the quantum
validator, and the (mocked) hardware bridge behind a small API, so calling
code doesn't need to touch the differential equations or the Hamiltonian
construction directly.
"""
import numpy as np

from .substrate import JellySubstrate
from .pedler_engine import PedlerEngine
from .quantum_validator import QiskitValidator
from .hardware_bridge import HardwareBridge


class PedlerEnvironment:
    def __init__(self, initial_nodes=4, alpha=0.5, K0=1.0, gamma=1.0, seed=None):
        self.substrate = JellySubstrate(num_nodes=initial_nodes, alpha=alpha, K0=K0, seed=seed)
        self.engine = PedlerEngine(self.substrate, gamma=gamma, seed=seed)
        self.validator = QiskitValidator()
        self.hardware = HardwareBridge()

    def inject_point_event(self, data_vector, novelty_threshold=0.25):
        r_t = np.array(data_vector, dtype=float)
        final_phases, R = self.engine.process_point_event(r_t, novelty_threshold=novelty_threshold)
        return {
            "order_parameter_R": R,
            "state_cardinality": len(self.engine.S),
            "final_phases": final_phases,
        }

    def evaluate_inclination_field(self, data_vector):
        return self.engine.compute_inclination_field(np.array(data_vector, dtype=float))

    def trigger_selection_collapse(self, data_vector, novelty_threshold=0.25):
        """Alias kept for API-shape parity with the original spec; does
        the same thing as inject_point_event."""
        return self.inject_point_event(data_vector, novelty_threshold=novelty_threshold)

    def run_lifecycle_maintenance(self, lam=0.1, dt=1.0, prior_epsilon=0.02):
        """Decay historical priors, then prune/consolidate. Call this
        periodically (e.g. once per N point events) rather than after
        every single event -- consolidation needs phase history from the
        most recent process_point_event call to do anything."""
        self.engine.decay_priors(lam, dt)
        return self.engine.prune_and_consolidate(prior_epsilon=prior_epsilon)

    def compile_to_qiskit(self, evolution_time=1.0):
        return self.validator.build_ctqw_circuit(self.substrate.K, evolution_time)

    def push_k_matrix_to_hardware(self):
        return self.hardware.export_k_matrix_to_serial(self.substrate.K)
