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
from typing import TYPE_CHECKING, Any, Union

# Local Modules:
from .telnet import BaseTelnetProtocol, TelnetProtocol
from .telnet_constants import IAC, MCCP1, MCCP2, SB, SE, WILL


logger: logging.Logger = logging.getLogger(__name__)


if TYPE_CHECKING:  # pragma: no cover
	Base = TelnetProtocol
else:  # pragma: no cover
	Base = BaseTelnetProtocol


class MCCPMixIn(Base):
	"""An MCCP mix in class for the Telnet protocol."""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self.subnegotiationMap[MCCP1] = lambda *args: None
		self.subnegotiationMap[MCCP2] = lambda *args: None
		self._compressionEnabled: bool = False
		self._mccpVersion: Union[int, None] = None
		self._compressedInputBuffer: bytearray = bytearray()
		self._decompressor: Any = None

	def disableMCCP(self) -> None:
		self._mccpVersion = None
		self._compressionEnabled = False
		self._decompressor = None

	def on_dataReceived(self, data: bytes) -> None:
		inputBuffer: bytearray = self._compressedInputBuffer
		inputBuffer.extend(data)
		while inputBuffer:
			if self._compressionEnabled:
				# Compressed data:
				super().on_dataReceived(self._decompressor.decompress(inputBuffer))
				inputBuffer.clear()
				if self._decompressor.unused_data:
					# Uncompressed data following the compressed data, likely due to the server terminating compression.
					logger.debug(
						"received uncompressed data while compression enabled. Disabling compression."
					)
					inputBuffer.extend(self._decompressor.unused_data)
					state = self.getOptionState(MCCP1 if self._mccpVersion == 1 else MCCP2)
					state.him.enabled = False
					state.him.negotiating = False
					self.disableMCCP()
					continue  # Process the remaining uncompressed data.
				return None  # inputBuffer is empty, no need to loop again.
			# Uncompressed data:
			iacIndex: int = inputBuffer.find(IAC)
			if self._mccpVersion is not None and iacIndex >= 0:
				# MCCP was negotiated on, and an IAC byte was found.
				if iacIndex > 0:
					super().on_dataReceived(bytes(inputBuffer[:iacIndex]))
					del inputBuffer[:iacIndex]
				if len(inputBuffer) == 1:
					# Partial IAC sequence.
					return None
				elif inputBuffer[1] == SB[0]:
					seIndex: int = inputBuffer.find(SE)
					if seIndex < 0 or inputBuffer[seIndex - 1 : seIndex] not in (IAC, WILL):
						# Partial subnegotiation sequence.
						return None
					elif inputBuffer[:seIndex] in (IAC + SB + MCCP1 + WILL, IAC + SB + MCCP2 + IAC):
						# The server enabled compression. Subsequent data will be compressed.
						self._compressionEnabled = True
						self._decompressor = zlib.decompressobj(zlib.MAX_WBITS)
						logger.debug("Peer notifies us that subsequent data will be compressed.")
					else:
						# We don't care about other subnegotiations, pass it on.
						super().on_dataReceived(bytes(inputBuffer[: seIndex + 1]))
					del inputBuffer[: seIndex + 1]
				else:
					# We don't care about other IAC sequences, pass it on.
					super().on_dataReceived(bytes(inputBuffer[:2]))
					del inputBuffer[:2]
			else:
				# MCCP was not negotiated on, or no IAC was found.
				super().on_dataReceived(bytes(inputBuffer))
				inputBuffer.clear()

	def on_enableRemote(self, option: bytes) -> bool:
		if option in (MCCP1, MCCP2):
			if self._mccpVersion is None:
				self._mccpVersion = 1 if option == MCCP1 else 2
				logger.debug(f"MCCP{self._mccpVersion} negotiation enabled.")
				return True
			return False
		return bool(super().on_enableRemote(option))  # pragma: no cover

	def on_disableRemote(self, option: bytes) -> None:
		if option in (MCCP1, MCCP2):
			logger.debug(
				f"MCCP{self._mccpVersion if self._mccpVersion is not None else ''} negotiation disabled."
			)
			self.disableMCCP()
			return None
		super().on_disableRemote(option)  # pragma: no cover
