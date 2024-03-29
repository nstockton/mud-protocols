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
import re
from enum import Enum, auto
from typing import Any, ClassVar, Union

# Local Modules:
from .base import Protocol
from .mpi import MPI_INIT
from .telnet_constants import CR, CR_LF, LF
from .utils import unescapeXMLBytes


LT: bytes = b"<"
GT: bytes = b">"
DIRECTIONS_REGEX: re.Pattern[bytes] = re.compile(rb"dir\=['\x22]?(?P<dir>north|east|south|west|up|down)")


logger: logging.Logger = logging.getLogger(__name__)


def directionFromMovement(movement: bytes) -> bytes:
	match: Union[re.Match[bytes], None] = DIRECTIONS_REGEX.search(movement)
	return match.group("dir") if match is not None else b""


class XMLState(Enum):
	"""
	Valid states for the state machine.
	"""

	DATA = auto()
	TAG = auto()


class XMLMode(Enum):
	"""
	Valid modes corresponding to supported XML tags.
	"""

	NONE = auto()
	DESCRIPTION = auto()
	EXITS = auto()
	MAGIC = auto()
	NAME = auto()
	PROMPT = auto()
	ROOM = auto()
	TERRAIN = auto()


class XMLProtocol(Protocol):
	"""
	Implements the Mume XML protocol.
	"""

	tagModes: ClassVar[dict[str, XMLMode]] = {
		"description": XMLMode.DESCRIPTION,
		"exits": XMLMode.EXITS,
		"magic": XMLMode.MAGIC,
		"name": XMLMode.NAME,
		"prompt": XMLMode.PROMPT,
		"room": XMLMode.ROOM,
		"terrain": XMLMode.TERRAIN,
	}
	"""A mapping of closing tags to mode objects."""
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
		self._mode: XMLMode = XMLMode.NONE
		self._parentModes: list[XMLMode] = []

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
		if self.outputFormat == "raw" or not self._gratuitous:
			# Gratuitous text should be omitted unless format is 'raw'.
			appDataBuffer.extend(appData)
		if self._mode is XMLMode.NONE:
			self._lineBuffer.extend(appData)
			lines = self._lineBuffer.splitlines(keepends=True)
			self._lineBuffer.clear()
			if lines and not lines[-1].endswith((CR, LF)):
				# Final line is incomplete.
				self._lineBuffer.extend(lines.pop())
			for line in lines:
				if line.strip():
					self.on_xmlEvent("line", unescapeXMLBytes(line.rstrip(CR_LF)))
		elif self._mode is XMLMode.ROOM:
			self._dynamicBuffer.extend(appData)
		else:
			self._textBuffer.extend(appData)
		if separator:
			self.state = XMLState.TAG
		return data

	def _handleXMLTag(self, data: bytes, appDataBuffer: bytearray) -> bytes:  # NOQA: C901
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
		tagName: str = str(tag, "us-ascii").strip("/").split(None, 1)[0] if tag else ""
		isClosingTag: bool = tag.startswith(b"/")
		if self.outputFormat == "raw":
			appDataBuffer.extend(LT + tag + GT)
		elif self.outputFormat == "tintin" and not self._gratuitous:
			appDataBuffer.extend(self.tintinReplacements.get(tag, b""))
		if tagName == "gratuitous":
			self._gratuitous = not isClosingTag
		elif isClosingTag and self.tagModes.get(tagName) is self._mode:
			# The tag is a closing tag, corresponding with the current mode.
			if self._mode is XMLMode.ROOM:
				self.on_xmlEvent("dynamic", unescapeXMLBytes(bytes(self._dynamicBuffer).lstrip(b"\r\n")))
				self._dynamicBuffer.clear()
			else:
				self.on_xmlEvent(tagName, unescapeXMLBytes(bytes(self._textBuffer)))
				self._textBuffer.clear()
			self._mode = self._parentModes.pop()
		elif tagName == "magic":
			# Magic tags can occur inside and outside room info.
			self._parentModes.append(self._mode)
			self._mode = XMLMode.MAGIC
		elif self._mode is XMLMode.NONE and tagName == "movement":
			# Movement is transmitted as a self-closing tag (I.E. opening and closing tag in one).
			# Because of this, we don't need a separate mode for movement.
			self.on_xmlEvent(tagName, directionFromMovement(unescapeXMLBytes(tag)))
		elif self._mode is XMLMode.NONE:
			# A new child mode from NONE.
			if tagName == "prompt":
				self._parentModes.append(self._mode)
				self._mode = XMLMode.PROMPT
			elif tagName == "room":
				self._parentModes.append(self._mode)
				self._mode = XMLMode.ROOM
				self.on_xmlEvent("room", unescapeXMLBytes(tag[5:]))
		elif self._mode is XMLMode.ROOM:
			# New child mode from ROOM.
			if tagName == "name":
				self._parentModes.append(self._mode)
				self._mode = XMLMode.NAME
			elif tagName == "description":
				self._parentModes.append(self._mode)
				self._mode = XMLMode.DESCRIPTION
			elif tagName == "exits":
				self._parentModes.append(self._mode)
				self._mode = XMLMode.EXITS
			elif tagName == "terrain":
				self._parentModes.append(self._mode)
				self._mode = XMLMode.TERRAIN
		self.state = XMLState.DATA
		return data

	def on_dataReceived(self, data: bytes) -> None:
		appDataBuffer: bytearray = bytearray()
		while data:
			if self.state is XMLState.DATA:
				data = self._handleXMLText(data, appDataBuffer)
			elif self.state is XMLState.TAG:
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
