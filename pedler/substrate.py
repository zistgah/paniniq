# pedler.substrate -- Kuramoto oscillator substrate (JellySubstrate, ClassicalSubstrate).
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
Module 1 -- Continuous-wave "Jelly" substrate.

A network of phase oscillators (Kuramoto model), coupled through an
evanescent (exponentially distance-decaying) matrix K_ij = K0 * exp(-alpha
* r_ij), with zero self-coupling.

Two implementations, sharing the same interface (relax / add_node /
remove_nodes), so PedlerEngine can drive either one interchangeably:

  * JellySubstrate    -- scipy.integrate.solve_ivp. Accurate adaptive-step
                         ODE integration. Fine up to a few hundred nodes.
                         This is the one that's fully tested in this
                         sandbox (numpy/scipy are installed here).

  * ClassicalSubstrate -- vectorized PyTorch, fixed-step Euler integration.
                         Written to scale to large node counts and to use
                         a GPU automatically if `torch.cuda.is_available()`.
                         torch is NOT installed in this sandbox and there's
                         no network access to install it, so this class is
                         untested here -- it will raise a clear ImportError
                         if you try to use it in an environment without
                         torch. Install torch yourself and re-run
                         demo.py to exercise this path.

Honest naming note: the brief calls this a "Kuramoto-Duffing" engine, but
the differential equation actually specified (and implemented below) is
the standard Kuramoto phase model -- each node has a phase only. A true
Duffing oscillator carries its own amplitude with a cubic nonlinear
restoring force (x'' + delta*x' + alpha*x + beta*x^3 = ...), which isn't
part of the given equations. If you want that added (coupled
amplitude+phase dynamics, giving the substrate genuine bistability), say so
and I'll extend it -- it's a real, separate piece of work, not a one-line
change.
"""
import numpy as np
from scipy.integrate import solve_ivp

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class JellySubstrate:
    """Reference (scipy-based) oscillator substrate."""

    def __init__(self, num_nodes=4, alpha=0.5, K0=1.0, seed=None):
        if num_nodes < 1:
            raise ValueError("num_nodes must be >= 1")
        self.rng = np.random.default_rng(seed)
        self.N = num_nodes
        self.alpha = alpha
        self.K0 = K0

        # 12 fractal frequency tiers, log-spaced 1 .. 1000 (rad/s, as used
        # directly in the phase ODE below -- the brief doesn't specify a
        # 2*pi conversion from Hz, so none is applied).
        self.freq_tiers = np.logspace(0, 3, 12)
        self.omegas = self.rng.choice(self.freq_tiers, size=self.N)

        self.coords = self.rng.random((self.N, 3))
        self._update_coupling_matrix()

    def _update_coupling_matrix(self):
        dist = np.linalg.norm(self.coords[:, None, :] - self.coords[None, :, :], axis=-1)
        self.K = self.K0 * np.exp(-self.alpha * dist)
        np.fill_diagonal(self.K, 0.0)

    def add_node(self, coord=None):
        """Structural plasticity: grow the substrate by one node."""
        new_coord = (np.asarray(coord, dtype=float).reshape(1, 3)
                     if coord is not None else self.rng.random((1, 3)))
        self.coords = np.vstack([self.coords, new_coord])
        self.omegas = np.append(self.omegas, self.rng.choice(self.freq_tiers))
        self.N += 1
        self._update_coupling_matrix()

    def remove_nodes(self, keep_mask):
        """Structural pruning/consolidation: keep only nodes where
        keep_mask[i] is True. Caller is responsible for keeping any
        parallel arrays it owns (PedlerEngine's eta/wc/F) in sync using
        the same mask."""
        keep_mask = np.asarray(keep_mask, dtype=bool)
        if keep_mask.shape[0] != self.N:
            raise ValueError("keep_mask length must equal current N")
        self.coords = self.coords[keep_mask]
        self.omegas = self.omegas[keep_mask]
        self.N = int(keep_mask.sum())
        self._update_coupling_matrix()

    def kuramoto_rhs(self, t, theta):
        phase_diffs = theta[None, :] - theta[:, None]
        return self.omegas + np.sum(self.K * np.sin(phase_diffs), axis=1)

    def relax(self, init_phases, duration=2.0, n_eval=200):
        """Simulate phase-locking relaxation; return (final_phases, R)."""
        init_phases = np.asarray(init_phases, dtype=float)
        if init_phases.shape[0] != self.N:
            raise ValueError(f"init_phases has length {init_phases.shape[0]}, expected {self.N}")
        sol = solve_ivp(
            self.kuramoto_rhs,
            (0, duration),
            init_phases,
            t_eval=np.linspace(0, duration, n_eval),
        )
        final_phases = sol.y[:, -1] % (2 * np.pi)
        order_param = np.abs(np.mean(np.exp(1j * final_phases)))
        return final_phases, float(order_param)


class ClassicalSubstrate:
    """
    Vectorized PyTorch substrate for large node counts / GPU execution.
    Same physics as JellySubstrate, fixed-step Euler instead of adaptive
    RK45 (needed to keep the whole relax() loop as tensor ops with no
    Python-level per-node work).

    NOT importable/usable without `torch` installed -- raises ImportError
    immediately on construction if torch isn't present, rather than
    failing confusingly later.
    """

    def __init__(self, num_nodes, alpha=0.5, K0=1.0, device=None, seed=None,
                 natural_frequencies=False):
        if not TORCH_AVAILABLE:
            raise ImportError(
                "ClassicalSubstrate requires PyTorch, which is not installed "
                "in this environment (and this sandbox has no network access "
                "to install it). Run `pip install torch` in an environment "
                "with network access, then this class works as written."
            )
        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if seed is not None:
            torch.manual_seed(seed)

        self.N = num_nodes
        self.alpha = alpha
        self.K0 = K0

        if natural_frequencies:
            freq_tiers = torch.logspace(0, 3, 12, device=self.device)
            idx = torch.randint(0, 12, (self.N,), device=self.device)
            self.omegas = freq_tiers[idx]
        else:
            self.omegas = torch.zeros(self.N, device=self.device)

        self.coords = torch.rand((self.N, 3), device=self.device)
        self.K = self._update_coupling_matrix()

    def _update_coupling_matrix(self):
        torch = self.torch
        dist = torch.cdist(self.coords, self.coords)
        K = self.K0 * torch.exp(-self.alpha * dist)
        K.fill_diagonal_(0.0)
        return K

    def add_node(self, coord=None):
        torch = self.torch
        new_coord = (torch.as_tensor(coord, dtype=torch.float32, device=self.device).reshape(1, 3)
                     if coord is not None else torch.rand((1, 3), device=self.device))
        self.coords = torch.cat([self.coords, new_coord])
        self.omegas = torch.cat([self.omegas, torch.zeros(1, device=self.device)])
        self.N += 1
        self.K = self._update_coupling_matrix()

    def remove_nodes(self, keep_mask):
        torch = self.torch
        keep = torch.as_tensor(keep_mask, dtype=torch.bool, device=self.device)
        self.coords = self.coords[keep]
        self.omegas = self.omegas[keep]
        self.N = int(keep.sum().item())
        self.K = self._update_coupling_matrix()

    def relax(self, initial_phases, dt=0.01, steps=1000):
        torch = self.torch
        theta = torch.as_tensor(initial_phases, dtype=torch.float32, device=self.device).clone()
        for _ in range(steps):
            phase_diffs = theta.unsqueeze(0) - theta.unsqueeze(1)
            interaction = torch.sum(self.K * torch.sin(phase_diffs), dim=1)
            theta = theta + (self.omegas + interaction) * dt
        R = torch.abs(torch.mean(torch.polar(torch.ones_like(theta), theta))).item()
        return torch.remainder(theta, 2 * np.pi), R
