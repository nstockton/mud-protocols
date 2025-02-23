# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""MUD Client Compression protocol."""

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
import zlib
from typing import Any, Union

# Local Modules:
from .telnet import TelnetInterface
from .telnet_constants import IAC, MCCP1, MCCP2, SB, SE, WILL


IAC_SB: bytes = IAC + SB
MCCP_ENABLED_RESPONSES: tuple[bytes, bytes] = (
	IAC + SB + MCCP1 + WILL + SE,
	IAC + SB + MCCP2 + IAC + SE,
)


logger: logging.Logger = logging.getLogger(__name__)


class MCCPMixIn(TelnetInterface):
	"""An MCCP mix in class for the Telnet protocol."""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		"""
		Defines the constructor.

		Args:
			*args: Positional arguments to be passed to the parent constructor.
			**kwargs: Key-word only arguments to be passed to the parent constructor.
		"""
		super().__init__(*args, **kwargs)
		self.subnegotiation_map[MCCP1] = lambda *args: None
		self.subnegotiation_map[MCCP2] = lambda *args: None
		self._compression_enabled: bool = False
		self._mccp_version: Union[int, None] = None
		self._compressed_input_buffer: bytearray = bytearray()
		self._decompressor: Any = None

	def disable_mccp(self) -> None:
		"""Disables compression."""
		self._mccp_version = None
		self._compression_enabled = False
		self._decompressor = None

	def on_data_received(self, data: bytes) -> None:  # NOQA: D102
		input_buffer: bytearray = self._compressed_input_buffer
		input_buffer.extend(data)
		while input_buffer:
			if self._compression_enabled:
				# Data is compressed.
				super().on_data_received(self._decompressor.decompress(input_buffer))
				input_buffer.clear()
				if self._decompressor.unused_data:
					# Uncompressed data following the compressed data.
					# Likely due to the server terminating compression.
					logger.debug(
						"received uncompressed data while compression enabled. Disabling compression."
					)
					input_buffer.extend(self._decompressor.unused_data)
					state = self.get_option_state(MCCP1 if self._mccp_version == 1 else MCCP2)
					state.him.enabled = False
					state.him.negotiating = False
					self.disable_mccp()
					continue  # Process the remaining uncompressed data.
				return  # input_buffer is empty, no need to loop again.
			# Data is uncompressed.
			iac_index: int = input_buffer.find(IAC)
			if self._mccp_version is not None and iac_index != -1:
				# MCCP was negotiated on, and an IAC byte was found.
				if iac_index > 0:
					super().on_data_received(bytes(input_buffer[:iac_index]))
					del input_buffer[:iac_index]
				if input_buffer == IAC:
					# Partial IAC sequence.
					return
				if input_buffer.startswith(IAC_SB):
					se_index: int = input_buffer.find(SE)
					if se_index == -1:
						# Partial subnegotiation sequence.
						return
					if input_buffer.startswith(MCCP_ENABLED_RESPONSES):
						# The server enabled compression. Subsequent data will be compressed.
						self._compression_enabled = True
						self._decompressor = zlib.decompressobj(zlib.MAX_WBITS)
						logger.debug("Peer notifies us that subsequent data will be compressed.")
					else:
						# We don't care about other subnegotiations, pass it on.
						super().on_data_received(bytes(input_buffer[: se_index + 1]))
					del input_buffer[: se_index + 1]
				else:
					# We don't care about other IAC sequences, pass it on.
					super().on_data_received(bytes(input_buffer[:2]))
					del input_buffer[:2]
			else:
				# MCCP was not negotiated on, or no IAC was found.
				super().on_data_received(bytes(input_buffer))
				input_buffer.clear()

	def on_enable_remote(self, option: bytes) -> bool:  # NOQA: D102
		if option in {MCCP1, MCCP2}:
			if self._mccp_version is None:
				self._mccp_version = 1 if option == MCCP1 else 2
				logger.debug(f"MCCP{self._mccp_version} negotiation enabled.")
				return True
			return False
		return bool(super().on_enable_remote(option))  # pragma: no cover

	def on_disable_remote(self, option: bytes) -> None:  # NOQA: D102
		if option in {MCCP1, MCCP2}:
			logger.debug(
				f"MCCP{self._mccp_version if self._mccp_version is not None else ''} negotiation disabled."
			)
			self.disable_mccp()
			return
		super().on_disable_remote(option)  # type: ignore[safe-super]  # pragma: no cover
