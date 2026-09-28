# pedler.hardware_bridge -- mocked serial bridge, K-matrix to byte-frame packing.
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
Hardware abstraction layer -- MOCKED.

This is a software interface showing what a bridge to physical oscillator
hardware would look like. It does not, and cannot from this sandboxed
environment, talk to a real microcontroller, DAC, or lab instrument: there
is no serial port, no USB device, and no network access here.

What's real and tested: the K-matrix -> byte-command packing logic. That's
pure math/bit-packing and is fully unit-tested below with MockSerialPort.

What's NOT real: any actual electrical signal reaching a breadboard. To
drive real hardware, swap MockSerialPort for `serial.Serial(port,
baudrate)` (the `pyserial` package -- also not installed here) running on a
machine that is physically wired to your op-amp / digital-potentiometer
mesh, and you'll need firmware on the microcontroller side that
understands the frame format below (or that you adapt it to whatever
protocol your firmware actually speaks -- this format is a reasonable
starting point, not a standard).
"""
import numpy as np


class MockSerialPort:
    """Records writes instead of sending them over a real serial line."""

    def __init__(self, port_name="MOCK"):
        self.port_name = port_name
        self.sent_frames = []

    def write(self, data: bytes) -> int:
        self.sent_frames.append(bytes(data))
        return len(data)

    def close(self):
        pass


class HardwareBridge:
    def __init__(self, serial_port=None):
        # Swap in a real serial.Serial(...) object to talk to actual
        # hardware. Defaults to a mock so this is always safe to run.
        self.port = serial_port or MockSerialPort()

    @staticmethod
    def k_matrix_to_frames(K_matrix, header=b"\xAA\x55"):
        """
        Pack the upper triangle of K (symmetric, zero diagonal, so only
        i<j edges carry information) into one frame per edge:

            [header 2B][i 1B][j 1B][sign 1B][magnitude 1B]

        sign is 0 for K_ij >= 0 (ferromagnetic/attractive) and 1 for
        K_ij < 0 (anti-ferromagnetic/repulsive -- e.g. maxcut.py's
        solve_max_cut_oscillator, which sets K = -adjacency). magnitude
        is |K_ij| normalized against max(|K_ij|) over the whole matrix
        and quantized to 0-255.

        Bug fixed here (found during hardening, 2026-09-27): the previous
        5-byte format (no sign byte) normalized by max(K) directly and
        clipped negative ratios to 0. For any all-non-positive K -- which
        is every K solve_max_cut_oscillator produces -- max(K) is 0, so
        every edge's ratio came out <= 0 and was clipped to byte_val=0.
        The bridge silently emitted uninformative all-zero-magnitude
        frames for every anti-ferromagnetic matrix in this codebase,
        with no error and no warning. Normalizing on |K_ij| and carrying
        sign separately fixes this and is also strictly more general.
        This changes the wire format (5 bytes/frame -> 6); anything
        decoding the old format needs updating to match.
        """
        K = np.asarray(K_matrix, dtype=float)
        n = K.shape[0]
        max_abs = np.abs(K).max()
        max_abs = max_abs if max_abs > 0 else 1.0
        frames = []
        for i in range(n):
            for j in range(i + 1, n):
                sign = 0 if K[i, j] >= 0 else 1
                byte_val = int(round(255 * (abs(K[i, j]) / max_abs)))
                byte_val = min(max(byte_val, 0), 255)
                frames.append(header + bytes([i & 0xFF, j & 0xFF, sign, byte_val]))
        return frames

    def export_k_matrix_to_serial(self, K_matrix):
        frames = self.k_matrix_to_frames(K_matrix)
        for f in frames:
            self.port.write(f)
        return frames
