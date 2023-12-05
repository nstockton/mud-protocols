"""
Mume XML Protocol.
"""


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
from enum import Enum, auto
from typing import Any, ClassVar, Union

# Local Modules:
from .base import Protocol
from .mpi import MPI_INIT
from .telnet_constants import CR, CR_LF, LF
from .utils import unescapeXMLBytes


LT: bytes = b"<"
GT: bytes = b">"


logger: logging.Logger = logging.getLogger(__name__)


class XMLState(Enum):
	"""
	Valid states for the state machine.
	"""

	DATA = auto()
	TAG = auto()


class XMLProtocol(Protocol):
	"""
	Implements the Mume XML protocol.
	"""

	modes: ClassVar[dict[bytes, Union[bytes, None]]] = {
		b"room": b"room",
		b"/room": None,
		b"name": b"name",
		b"/name": b"room",
		b"description": b"description",
		b"/description": b"room",
		b"terrain": None,
		b"/terrain": b"room",
		b"magic": b"magic",
		b"/magic": None,
		b"exits": b"exits",
		b"/exits": None,
		b"prompt": b"prompt",
		b"/prompt": None,
	}
	"""A mapping of XML mode to new XML mode values."""
	tintinReplacements: ClassVar[dict[bytes, bytes]] = {
		b"prompt": b"PROMPT:",
		b"/prompt": b":PROMPT",
		b"name": b"NAME:",
		b"/name": b":NAME",
		b"tell": b"TELL:",
		b"/tell": b":TELL",
		b"narrate": b"NARRATE:",
		b"/narrate": b":NARRATE",
		b"pray": b"PRAY:",
		b"/pray": b":PRAY",
		b"say": b"SAY:",
		b"/say": b":SAY",
		b"emote": b"EMOTE:",
		b"/emote": b":EMOTE",
	}
	"""A mapping of tag to replacement values for Tintin."""

	def __init__(
		self,
		*args: Any,
		outputFormat: str,
		**kwargs: Any,
	) -> None:
		self.outputFormat: str = outputFormat
		super().__init__(*args, **kwargs)
		self.state: XMLState = XMLState.DATA
		"""The state of the state machine."""
		self._tagBuffer: bytearray = bytearray()  # Used for start and end tag names.
		self._textBuffer: bytearray = bytearray()  # Used for the text between start and end tags.
		self._dynamicBuffer: bytearray = bytearray()  # Used for dynamic room descriptions.
		self._lineBuffer: bytearray = bytearray()  # Used for non-XML lines.
		self._gratuitous: bool = False
		self._inRoom: bool = False
		self._mode: Union[bytes, None] = None

	def _handleXMLText(self, data: bytes, appDataBuffer: bytearray) -> bytes:
		"""
		Handles XML data that is not part of a tag.

		Args:
			data: The received data.
			appDataBuffer: The application level data buffer.

		Returns:
			The remaining data.
		"""
		appData, separator, data = data.partition(LT)
		if not (self._gratuitous and self.outputFormat != "raw"):
			# Gratuitous text should be omitted unless format is 'raw'.
			appDataBuffer.extend(appData)
		if self._mode is None:
			self._lineBuffer.extend(appData)
			lines = self._lineBuffer.splitlines(True)
			self._lineBuffer.clear()
			if lines and lines[-1][-1:] not in (CR, LF):
				# Final line is incomplete.
				self._lineBuffer.extend(lines.pop())
			lines = [line.rstrip(CR_LF) for line in lines if line.strip()]
			for line in lines:
				self.on_xmlEvent("line", unescapeXMLBytes(line))
		else:
			self._textBuffer.extend(appData)
		if separator:
			self.state = XMLState.TAG
		return data

	def _handleXMLTag(self, data: bytes, appDataBuffer: bytearray) -> bytes:
		"""
		Handles XML data that is part of a tag (I.E. enclosed in '<>').

		Args:
			data: The received data.
			appDataBuffer: The application level data buffer.

		Returns:
			The remaining data.
		"""
		appData, separator, data = data.partition(GT)
		self._tagBuffer.extend(appData)
		if not separator:
			# End of tag not reached yet.
			return data
		tag: bytes = bytes(self._tagBuffer).strip()
		self._tagBuffer.clear()
		baseTag: bytes = tag.replace(b"/", b"", 1) if tag.startswith(b"/") else tag
		isStatusTag: bool = baseTag == b"status"
		text: bytes = bytes(self._textBuffer)
		if not isStatusTag:
			self._textBuffer.clear()
		if self.outputFormat == "raw":
			appDataBuffer.extend(LT + tag + GT)
		elif self.outputFormat == "tintin" and not self._gratuitous:
			appDataBuffer.extend(self.tintinReplacements.get(tag, b""))
		if self._mode is None and tag.startswith(b"movement"):
			self.on_xmlEvent("movement", unescapeXMLBytes(tag[13:-1]))
		elif baseTag == b"gratuitous":
			self._gratuitous = not tag.startswith(b"/")
		elif tag.startswith(b"room"):
			self._inRoom = True
			self._mode = self.modes[b"room"]
			self.on_xmlEvent("room", unescapeXMLBytes(tag[5:]))
		elif tag == b"/room":
			self._inRoom = False
			self._mode = self.modes[tag]
			self._dynamicBuffer.extend(text)
			self.on_xmlEvent("dynamic", unescapeXMLBytes(bytes(self._dynamicBuffer).lstrip(b"\r\n")))
			self._dynamicBuffer.clear()
		elif tag in self.modes:
			if tag.startswith(b"/"):
				# Closing tag.
				self._mode = b"room" if self._inRoom else self.modes[tag]
				self.on_xmlEvent(tag[1:].decode("us-ascii"), unescapeXMLBytes(text))
			else:
				# Opening tag.
				self._mode = self.modes[tag]
				if self._inRoom:
					self._dynamicBuffer.extend(text)
		self.state = XMLState.DATA
		return data

	def on_dataReceived(self, data: bytes) -> None:
		appDataBuffer: bytearray = bytearray()
		while data:
			if self.state == XMLState.DATA:
				data = self._handleXMLText(data, appDataBuffer)
			elif self.state == XMLState.TAG:
				data = self._handleXMLTag(data, appDataBuffer)
		if appDataBuffer:
			if self.outputFormat == "raw":
				super().on_dataReceived(bytes(appDataBuffer))
			else:
				super().on_dataReceived(unescapeXMLBytes(bytes(appDataBuffer)))

	def on_connectionMade(self) -> None:
		# Turn on XML mode.
		# Mode "3" tells MUME to enable XML output without sending an initial "<xml>" tag.
		# Option "G" tells MUME to wrap room descriptions in gratuitous tags if they would otherwise be hidden.
		self.write(MPI_INIT + b"X2" + LF + b"3G" + LF)

	def on_connectionLost(self) -> None:
		pass

	def on_xmlEvent(self, name: str, data: bytes) -> None:
		"""
		Called when an XML event was received.

		Args:
			name: The event name.
			data: The payload.
		"""
