# pedler -- Jelly Substrate oscillator + PEDLER cognitive automaton, package entry point.
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
pedler -- a continuous-wave oscillator substrate + the PEDLER cognitive
automaton built on top of it, with an optional quantum (Qiskit) validation
bridge, a Max-Cut solver, and a mocked hardware abstraction layer.

See README.md at the repo root for an honest account of what's simulated,
what's mocked, and what would need real hardware/GPU/network access to go
further.
"""
from .substrate import JellySubstrate, ClassicalSubstrate, TORCH_AVAILABLE
from .pedler_engine import PedlerEngine
from .quantum_validator import QiskitValidator, QISKIT_AVAILABLE
from .hardware_bridge import HardwareBridge, MockSerialPort
from .api import PedlerEnvironment
from . import maxcut

__all__ = [
    "JellySubstrate",
    "ClassicalSubstrate",
    "TORCH_AVAILABLE",
    "PedlerEngine",
    "QiskitValidator",
    "QISKIT_AVAILABLE",
    "HardwareBridge",
    "MockSerialPort",
    "PedlerEnvironment",
    "maxcut",
]
