# pedler.pedler_engine -- PEDLER cognitive-automaton engine (inclination field, spawn/prune/consolidate).
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
Module 3 -- PEDLER automaton engine.

Implements PEDLER as a 6-tuple P = (I, G, U, S, F, *) on top of a
substrate (JellySubstrate or ClassicalSubstrate -- anything exposing
.N, .coords, .K, .relax(), .add_node(), .remove_nodes()):

  I  -- inclination field: computed fresh each call, not stored as state
  G  -- the resolution-match kernel: exp(-gamma * ||F(v_i) - r_t||)
  U  -- point events: arbitrary R^3 vectors, fed via process_point_event
  S  -- the state set: python list of ids, len(S) == substrate.N, always
  F  -- topological mapping F(v_i): one R^3 row per state, self.F
  *  -- governing operator: spawn (grows S) and prune/consolidate (shrinks
        it) are both part of "*". The brief's monotonicity constraint,
        |S(t)| <= |S(t+dt)|, is a growth-only rule -- a system that only
        ever grows can't run forever in bounded memory, which is exactly
        why the write-up also calls for a pruning/consolidation operator.
        Both are implemented below: _spawn_state enforces the original
        monotonicity constraint on its own; prune_and_consolidate is the
        explicit, separate escape hatch from it, run on a schedule you
        control (see run_lifecycle_maintenance in api.py), not
        automatically after every point event.

Terminology note, stated plainly rather than silently assumed:
"inclination field", "causal tension", and "resolution match" are this
framework's own vocabulary, not standard terms from an established
cognitive-science or physics theory. What follows is a faithful
implementation of the *equations* as given: an exponential-kernel
potential field over R^3, mapped onto oscillator phases, collapsed by
phase-locking dynamics. That's a legitimate, well-defined computational
object. It is not a claim that this simulates cognition, consciousness,
or any biological substrate.
"""
import numpy as np


def _to_numpy(x):
    return x.detach().cpu().numpy() if hasattr(x, "detach") else np.asarray(x)


def _phase_distance(a, b):
    """Circular distance between two phases (radians), in [0, pi]."""
    return np.abs(np.angle(np.exp(1j * (a - b))))


class PedlerEngine:
    def __init__(self, substrate, gamma=1.0, prior_gain=0.05, seed=None):
        self.substrate = substrate
        self.gamma = gamma
        self.prior_gain = prior_gain
        self.rng = np.random.default_rng(seed)

        N = substrate.N
        self.S = list(range(N))                       # state set
        self.eta = np.zeros(N)                         # historical priors
        self.wc = np.ones(N)                           # topological weights
        self.F = _to_numpy(substrate.coords).copy()    # F(v_i)
        self.last_phases = None                        # set after first event

    # ---- Inclination field (I), using kernel (G) -------------------
    def compute_inclination_field(self, r_t):
        r_t = np.asarray(r_t, dtype=float)
        distances = np.linalg.norm(self.F - r_t, axis=1)
        resolution_match = np.exp(-self.gamma * distances)
        return self.eta + self.wc * resolution_match

    # ---- Point events (U) -> collapse via substrate relaxation -----
    def process_point_event(self, r_t, novelty_threshold=0.25, relax_kwargs=None):
        relax_kwargs = relax_kwargs or {}
        r_t = np.asarray(r_t, dtype=float)

        I0 = self.compute_inclination_field(r_t)

        # Map potential -> initial phase: highest potential -> phase near 0.
        # Lateral inhibition / resonant self-excitation both live inside
        # substrate.relax() itself; this just sets the starting condition.
        init_phases = 2 * np.pi * (1.0 - I0 / (np.max(I0) + 1e-8))

        final_phases, R = self.substrate.relax(init_phases, **relax_kwargs)
        final_phases = _to_numpy(final_phases)
        self.last_phases = final_phases

        # Historical priors strengthen wherever resolution was actually
        # found this step. Without this, eta stays at 0 forever and
        # decay/pruning has nothing to act on.
        resolution_match = np.exp(-self.gamma * np.linalg.norm(self.F - r_t, axis=1))
        self.eta = self.eta + self.prior_gain * resolution_match

        if R < novelty_threshold:
            self._spawn_state(r_t)

        return final_phases, R

    # ---- Governing operator (*), spawn half -------------------------
    def _spawn_state(self, r_t):
        r_t = np.asarray(r_t, dtype=float).reshape(3,)
        self.substrate.add_node(coord=r_t)

        self.S.append(len(self.S))
        self.eta = np.append(self.eta, 0.1)
        self.wc = np.append(self.wc, 1.0)
        self.F = np.vstack([self.F, r_t])
        self.last_phases = None  # topology changed; stale phase info

    # ---- Governing operator (*), prune/consolidate half -------------
    def decay_priors(self, lam, dt):
        """eta_i(t + dt) = eta_i(t) * exp(-lambda * dt)."""
        self.eta = self.eta * np.exp(-lam * dt)

    def prune_and_consolidate(self, prior_epsilon=0.02, phase_lock_tol=0.05,
                               coupling_frac=0.9):
        """
        Prune: drop states whose historical prior has decayed below
        prior_epsilon.
        Consolidate: merge state j into state i when K_ij is within
        coupling_frac of the current max coupling AND their last-known
        phases are within phase_lock_tol radians (circular distance) of
        each other. Needs process_point_event to have run since the last
        topology change; otherwise there's no phase information and only
        decay/prune applies.

        Returns (n_pruned, n_merged).
        """
        n = len(self.S)
        if n <= 1:
            return 0, 0

        K = _to_numpy(self.substrate.K)
        parent = np.arange(n)

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        if self.last_phases is not None and len(self.last_phases) == n:
            k_max = K.max()
            threshold = coupling_frac * k_max if k_max > 0 else np.inf
            for i in range(n):
                for j in range(i + 1, n):
                    if K[i, j] >= threshold and _phase_distance(
                            self.last_phases[i], self.last_phases[j]) < phase_lock_tol:
                        ri, rj = find(i), find(j)
                        if ri != rj:
                            self.wc[ri] += self.wc[rj]
                            parent[rj] = ri

        is_root = np.array([find(i) == i for i in range(n)])
        n_merged = int((~is_root).sum())

        keep = is_root.copy()
        keep[is_root] &= (self.eta[is_root] >= prior_epsilon)
        n_pruned = int(is_root.sum() - keep.sum())

        if keep.all():
            return 0, 0

        self.eta = self.eta[keep]
        self.wc = self.wc[keep]
        self.F = self.F[keep]
        self.S = list(range(int(keep.sum())))
        self.substrate.remove_nodes(keep)
        self.last_phases = None

        return n_pruned, n_merged
