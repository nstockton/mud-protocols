"""
MUD Client Compression protocol.
"""


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
import zlib
from typing import Any

# Local Modules:
from .base import Protocol
from .telnet_constants import IAC, MCCP1, MCCP2, SB, SE, WILL


logger: logging.Logger = logging.getLogger(__name__)


class MCCPMixIn(Protocol):
	"""An MCCP mix in class for the Telnet protocol."""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self.subnegotiationMap[MCCP1] = lambda *args: None  # type: ignore[attr-defined]
		self.subnegotiationMap[MCCP2] = lambda *args: None  # type: ignore[attr-defined]
		self._isCompressed: bool = False
		self._usingMCCp1: bool = False
		self._usingMCCp2: bool = False
		self._compressedInputBuffer: bytearray = bytearray()
		self._decompressor: Any = None

	def on_dataReceived(self, data: bytes) -> None:
		outputBuffer: list[bytes] = []
		inputBuffer: bytearray = self._compressedInputBuffer
		inputBuffer.extend(data)
		while inputBuffer:
			if self._isCompressed:
				# Compressed data:
				outputBuffer.append(self._decompressor.decompress(inputBuffer))
				inputBuffer.clear()
				if self._decompressor.unused_data:
					# Uncompressed data following the compressed data, likely due to the server terminating compression.
					logger.debug(
						"received uncompressed data while compression enabled. Disabling compression."
					)
					inputBuffer.extend(self._decompressor.unused_data)
					self._isCompressed = False
					self._usingMCCp1 = False
					self._usingMCCp2 = False
					del self._decompressor
					self._decompressor = None
					continue  # Process the remaining uncompressed data.
				break  # inputBuffer is empty, no need to loop again.
			# Uncompressed data:
			iacIndex: int = inputBuffer.find(IAC)
			if iacIndex >= 0:
				# An IAC byte was found.
				outputBuffer.append(inputBuffer[:iacIndex])
				del inputBuffer[:iacIndex]
				if len(inputBuffer) == 1:
					# Partial IAC sequence.
					break
				elif inputBuffer[1] == SB[0]:
					seIndex: int = inputBuffer.find(SE)
					if seIndex < 0 or inputBuffer[seIndex - 1 : seIndex] not in (IAC, WILL):
						# Partial subnegotiation sequence.
						break
					elif inputBuffer[:seIndex] in (IAC + SB + MCCP1 + WILL, IAC + SB + MCCP2 + IAC):
						# The server enabled compression. Subsequent data will be compressed.
						self._isCompressed = True
						self._decompressor = zlib.decompressobj(zlib.MAX_WBITS)
						logger.debug("Peer notifies us that subsequent data will be compressed.")
					else:
						# We don't care about other subnegotiations, pass it on.
						outputBuffer.append(inputBuffer[: seIndex + 1])
					del inputBuffer[: seIndex + 1]
				else:
					# We don't care about other IAC sequences, pass it on.
					outputBuffer.append(inputBuffer[:2])
					del inputBuffer[:2]
			else:
				# No IAC was found.
				outputBuffer.append(inputBuffer.copy())
				inputBuffer.clear()
		if outputBuffer:
			super().on_dataReceived(b"".join(outputBuffer))

	def on_enableRemote(self, option: bytes) -> bool:
		if option == MCCP1:
			# Only enable MCCP1 if MCCP2 is not enabled.
			self._usingMCCp1 = not self._usingMCCp2
			logger.debug(f"MCCP1 negotiation {'enabled' if self._usingMCCp1 else 'disabled'}.")
			return self._usingMCCp1
		elif option == MCCP2:
			# Only enable MCCP2 if MCCP1 is not enabled.
			self._usingMCCp2 = not self._usingMCCp1
			logger.debug(f"MCCP2 negotiation {'enabled' if self._usingMCCp2 else 'disabled'}.")
			return self._usingMCCp2
		return bool(super().on_enableRemote(option))  # type: ignore[misc] # pragma: no cover

	def on_disableRemote(self, option: bytes) -> None:
		if option in (MCCP1, MCCP2):
			logger.debug(f"MCCP{'1' if option == MCCP1 else '2'} negotiation disabled.")
			return None
		super().on_disableRemote(option)  # type: ignore[misc] # pragma: no cover
