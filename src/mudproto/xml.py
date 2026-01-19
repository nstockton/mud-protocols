# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mume XML Protocol."""

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
import re
from collections.abc import Iterable
from contextlib import suppress
from enum import Enum, auto
from typing import Any, ClassVar

# Third-party Modules:
from knickknacks.databytes import decode_bytes
from knickknacks.typedef import ReBytesMatchType, ReBytesPatternType
from knickknacks.xml import unescape_xml_bytes

# Local Modules:
from .connection import ConnectionInterface
from .mpi import MPI_INIT
from .telnet_constants import CR, CR_LF, LF


LT: bytes = b"<"
GT: bytes = b">"
DIRECTIONS_REGEX: ReBytesPatternType = re.compile(rb"dir\=['\x22]?(?P<dir>north|east|south|west|up|down)")


logger: logging.Logger = logging.getLogger(__name__)


def direction_from_movement(movement: bytes) -> bytes:
	"""
	Retrieves the direction of movement from a movement tag.

	Args:
		movement: The movement tag to parse.

	Returns:
		The direction of movement.
	"""
	match: ReBytesMatchType = DIRECTIONS_REGEX.search(movement)
	return match.group("dir") if match is not None else b""


class XMLState(Enum):
	"""Valid states for the state machine."""

	DATA = auto()
	TAG = auto()


class XMLMode(Enum):
	"""Valid modes corresponding to supported XML tags."""

	NONE = auto()
	DESCRIPTION = auto()
	EXITS = auto()
	MAGIC = auto()
	NAME = auto()
	PROMPT = auto()
	ROOM = auto()
	TERRAIN = auto()


def get_xml_mode(tag: str) -> XMLMode | None:
	"""
	Retrieves an XMLMode enum from a tag name.

	Args:
		tag: The tag name.

	Returns:
		the XMLMode enum corresponding to the tag name, None if not found.
	"""
	with suppress(KeyError):
		return XMLMode[tag.upper()]
	return None


def get_tintin_tag_replacement(tag: bytes, valid_tags: Iterable[bytes]) -> bytes:
	"""
	Retrieves a Tintin tag replacement from a tag name.

	Args:
		tag: The tag name.
		valid_tags: The supported tag names.

	Returns:
		Uppercase tag name followed by a colon if opening tag,
		a colon followed by uppercase tag name if closing tag,
		An empty bytes object if not found.
	"""
	is_closing: bool = tag.startswith(b"/")
	tag = tag.strip(b"/")
	return b"" if tag not in valid_tags else b":" + tag.upper() if is_closing else tag.upper() + b":"


class XMLProtocol(ConnectionInterface):
	"""Implements the Mume XML protocol."""

	tintin_replacements: ClassVar[set[bytes]] = {
		b"prompt",
		b"name",
		b"tell",
		b"narrate",
		b"pray",
		b"say",
		b"emote",
	}
	"""Tag to replacement values for Tintin."""

	def __init__(
		self,
		*args: Any,
		output_format: str,
		**kwargs: Any,
	) -> None:
		"""
		Defines the constructor.

		Args:
			*args: Positional arguments to be passed to the parent constructor.
			output_format: The output format to be used.
			**kwargs: Key-word only arguments to be passed to the parent constructor.
		"""
		self.output_format: str = output_format
		super().__init__(*args, **kwargs)
		self.state: XMLState = XMLState.DATA
		"""The state of the state machine."""
		self._tag_buffer: bytearray = bytearray()  # Used for start and end tag names.
		self._text_buffer: bytearray = bytearray()  # Used for the text between start and end tags.
		self._dynamic_buffer: bytearray = bytearray()  # Used for dynamic room descriptions.
		self._line_buffer: bytearray = bytearray()  # Used for non-XML lines.
		self._gratuitous: bool = False
		self._mode: XMLMode = XMLMode.NONE
		self._parent_modes: list[XMLMode] = []

	def _handle_xml_text(self, data: bytes, app_data_buffer: bytearray) -> bytes:
		"""
		Handles XML data that is not part of a tag.

		Args:
			data: The received data.
			app_data_buffer: The application level data buffer.

		Returns:
			The remaining data.
		"""
		app_data, separator, data = data.partition(LT)
		if self.output_format == "raw" or not self._gratuitous:
			# Gratuitous text should be omitted unless format is 'raw'.
			app_data_buffer.extend(app_data)
		if self._mode is XMLMode.NONE:
			self._line_buffer.extend(app_data)
			lines = self._line_buffer.splitlines(keepends=True)
			self._line_buffer.clear()
			if lines and not lines[-1].endswith((CR, LF)):
				# Final line is incomplete.
				self._line_buffer.extend(lines.pop())
			for line in lines:
				if line.strip():
					self.on_xml_event("line", unescape_xml_bytes(line.rstrip(CR_LF)))
		elif self._mode is XMLMode.ROOM:
			self._dynamic_buffer.extend(app_data)
		else:
			self._text_buffer.extend(app_data)
		if separator:
			self.state = XMLState.TAG
		return data

	def _handle_xml_tag(self, data: bytes, app_data_buffer: bytearray) -> bytes:  # NOQA: C901, PLR0912
		"""
		Handles XML data that is part of a tag (I.E. enclosed in '<>').

		Args:
			data: The received data.
			app_data_buffer: The application level data buffer.

		Returns:
			The remaining data.
		"""
		app_data, separator, data = data.partition(GT)
		self._tag_buffer.extend(app_data)
		if not separator:
			# End of tag not reached yet.
			return data
		tag: bytes = bytes(self._tag_buffer).strip()
		self._tag_buffer.clear()
		tag_name: str = decode_bytes(tag).strip("/").split(None, 1)[0] if tag else ""
		is_closing_tag: bool = tag.startswith(b"/")
		if self.output_format == "raw":
			app_data_buffer.extend(LT + tag + GT)
		elif self.output_format == "tintin" and not self._gratuitous:
			app_data_buffer.extend(get_tintin_tag_replacement(tag, self.tintin_replacements))
		if tag_name == "gratuitous":
			self._gratuitous = not is_closing_tag
		elif is_closing_tag and get_xml_mode(tag_name) is self._mode:
			# The tag is a closing tag, corresponding with the current mode.
			if self._mode is XMLMode.ROOM:
				self.on_xml_event("dynamic", unescape_xml_bytes(bytes(self._dynamic_buffer).lstrip(b"\r\n")))
				self._dynamic_buffer.clear()
			else:
				self.on_xml_event(tag_name, unescape_xml_bytes(bytes(self._text_buffer)))
				self._text_buffer.clear()
			self._mode = self._parent_modes.pop()
		elif tag_name == "magic":
			# Magic tags can occur inside and outside room info.
			self._parent_modes.append(self._mode)
			self._mode = XMLMode.MAGIC
		elif self._mode is XMLMode.NONE and tag_name == "movement":
			# Movement is transmitted as a self-closing tag, I.E. opening and closing tag in one.
			# Because of this, we don't need a separate mode for movement.
			self.on_xml_event(tag_name, direction_from_movement(unescape_xml_bytes(tag)))
		elif self._mode is XMLMode.NONE:
			# A new child mode from NONE.
			if tag_name == "prompt":
				self._parent_modes.append(self._mode)
				self._mode = XMLMode.PROMPT
			elif tag_name == "room":
				self._parent_modes.append(self._mode)
				self._mode = XMLMode.ROOM
				self.on_xml_event("room", unescape_xml_bytes(tag[5:]))
		elif self._mode is XMLMode.ROOM:
			# New child mode from ROOM.
			if tag_name == "name":
				self._parent_modes.append(self._mode)
				self._mode = XMLMode.NAME
			elif tag_name == "description":
				self._parent_modes.append(self._mode)
				self._mode = XMLMode.DESCRIPTION
			elif tag_name == "exits":
				self._parent_modes.append(self._mode)
				self._mode = XMLMode.EXITS
			elif tag_name == "terrain":
				self._parent_modes.append(self._mode)
				self._mode = XMLMode.TERRAIN
		self.state = XMLState.DATA
		return data

	def on_data_received(self, data: bytes) -> None:  # NOQA: D102
		app_data_buffer: bytearray = bytearray()
		while data:
			if self.state is XMLState.DATA:
				data = self._handle_xml_text(data, app_data_buffer)
			elif self.state is XMLState.TAG:
				data = self._handle_xml_tag(data, app_data_buffer)
		if app_data_buffer:
			if self.output_format == "raw":
				super().on_data_received(bytes(app_data_buffer))
			else:
				super().on_data_received(unescape_xml_bytes(bytes(app_data_buffer)))

	def on_connection_made(self) -> None:  # NOQA: D102
		# Turn on XML mode.
		# Mode "3" tells MUME to enable XML output without sending an initial "<xml>" tag.
		# Option "G" tells MUME to wrap room descriptions in gratuitous
		# tags if they would otherwise be hidden.
		self.write(MPI_INIT + b"X2" + LF + b"3G" + LF)

	def on_connection_lost(self) -> None:  # NOQA: D102
		pass

	def on_xml_event(self, name: str, data: bytes) -> None:
		"""
		Called when an XML event was received.

		Args:
			name: The event name.
			data: The payload.
		"""
