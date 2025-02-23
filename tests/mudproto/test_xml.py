# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Future Modules:
from __future__ import annotations

# Built-in Modules:
from collections.abc import Callable, Iterable
from itertools import zip_longest
from unittest import TestCase
from unittest.mock import Mock, _Call, call, patch

# MUD Protocol Modules:
from mudproto.mpi import MPI_INIT
from mudproto.telnet_constants import CR, LF
from mudproto.xml import LT, XMLProtocol, XMLState


class TestXMLProtocol(TestCase):
	def setUp(self) -> None:
		name: bytes = b"\x1b[34mLower Flet\x1b[0m"
		# fmt: off
		description: bytes = (
			b"\x1b[35mBeing close to the ground, this white platform is not encircled by any rail.\x1b[0m"
			+ LF
			+ b"\x1b[35mInstead, beautiful draperies and tapestries hang from the many branches that\x1b[0m"
			+ LF
			+ b"\x1b[35msurround the flet. Swaying gently in the breeze, images on the colourful\x1b[0m" + LF
			+ b"\x1b[35mcloth create a place where one can stand and let the mind wander into the\x1b[0m" + LF
			+ b"\x1b[35mstories told by the everchanging patterns.\x1b[0m" + LF
		)
		terrain: bytes = b"There is some snow on the ground."
		detect_magic: bytes = b"\x1b[35mTraces of white tones form the aura of this place.\x1b[0m"
		raw_dynamic: bytes = (
			b"A finely crafted <object>crystal lamp</object> is hanging from a tree branch." + LF
			+ b"An <character>elven caretaker</character> is standing here, offering his guests a rest." + LF
		)
		dynamic: bytes = (
			b"A finely crafted crystal lamp is hanging from a tree branch." + LF
			+ b"An elven caretaker is standing here, offering his guests a rest." + LF
		)
		raw_exits: bytes = b"<exits>Exits: <exit dir=north id=4805400>north</exit>." + LF + b"</exits>"
		exits: bytes = b"Exits: north." + LF
		magic: bytes = b"You feel less protected."
		line: bytes = b"Hello world!"
		self.raw_prompt: bytes = b"<prompt>!# CW A1 M1 P8 S3 XP:<status>317k</status>&gt;</prompt>"
		self.prompt: bytes = b"!# CW A1 M1 P8 S3 XP:317k>"
		self.raw_data: bytes = (
			b"<movement dir=south/>"
			+ b'<room id=13168037 area="Lorien" terrain="forest">'
			+ b"<name>" + name + b"</name>" + LF
			+ b"<gratuitous><description>" + description + b"</description></gratuitous>"
			+ b"<terrain>" + terrain + b"</terrain>" + LF
			+ b"<magic>" + detect_magic + b"</magic>" + LF
			+ raw_dynamic
			+ raw_exits
			+ b"</room>" + LF
			+ b"<magic>" + magic + b"</magic>" + LF
			+ line + LF
			+ self.raw_prompt
		)
		self.normal_data: bytes = (
			name + LF
			+ terrain + LF
			+ detect_magic + LF
			+ dynamic
			+ exits + LF
			+ magic + LF
			+ line + LF
			+ self.prompt
		)
		self.tintin_data: bytes = (
			b"NAME:" + name + b":NAME" + LF
			+ terrain + LF
			+ detect_magic + LF
			+ dynamic
			+ exits + LF
			+ magic + LF
			+ line + LF
			+ b"PROMPT:" + self.prompt + b":PROMPT"
		)
		# fmt: on
		self.expected_events: list[Callable[[tuple[str, bytes]], _Call]] = [
			call("movement", b"south"),
			call("room", b'id=13168037 area="Lorien" terrain="forest"'),
			call("name", name),
			call("description", description),
			call("terrain", terrain),
			call("magic", detect_magic),
			call("exits", exits),
			call("dynamic", dynamic),
			call("magic", magic),
			call("line", line),
			call("prompt", self.prompt),
		]
		self.game_receives: bytearray = bytearray()
		self.player_receives: bytearray = bytearray()
		self.xml: XMLProtocol = XMLProtocol(
			self.game_receives.extend,
			self.player_receives.extend,
			output_format="normal",
			is_client=True,
		)

	def tearDown(self) -> None:
		self.xml.on_connection_lost()
		del self.xml
		self.game_receives.clear()
		self.player_receives.clear()

	def parse(self, data: bytes) -> tuple[bytes, bytes, XMLState]:
		self.xml.on_data_received(data)
		player_receives: bytes = bytes(self.player_receives)
		self.player_receives.clear()
		game_receives: bytes = bytes(self.game_receives)
		self.game_receives.clear()
		state: XMLState = self.xml.state
		self.xml.state = XMLState.DATA
		return player_receives, game_receives, state

	def assert_call_list(
		self,
		original_calls: Iterable[Callable[..., _Call]],
		expected_calls: Iterable[Callable[..., _Call]],
	) -> None:
		for original, expected in zip_longest(original_calls, expected_calls):
			self.assertEqual(original, expected)

	@patch("mudproto.xml.XMLProtocol.on_xml_event")
	def test_xml_on_data_received(self, mock_on_xml_event: Mock) -> None:
		data: bytes = b"Hello World!" + LF
		self.xml.output_format = "normal"
		self.xml.on_connection_made()
		self.assertEqual(self.parse(data), (data, MPI_INIT + b"X2" + LF + b"3G" + LF, XMLState.DATA))
		mock_on_xml_event.assert_called_once_with("line", data.rstrip(LF))
		mock_on_xml_event.reset_mock()
		# Insure that partial lines are properly buffered.
		for delimiter in (CR, LF):
			self.assertEqual(self.parse(b"partial"), (b"partial", b"", XMLState.DATA))
			mock_on_xml_event.assert_not_called()
			self.assertEqual(self.parse(delimiter), (delimiter, b"", XMLState.DATA))
			mock_on_xml_event.assert_called_once_with("line", b"partial")
			mock_on_xml_event.reset_mock()
		self.assertEqual(self.parse(LT + b"IncompleteTag"), (b"", b"", XMLState.TAG))
		mock_on_xml_event.assert_not_called()
		self.assertEqual(self.xml._tag_buffer, b"IncompleteTag")
		self.assertEqual(self.xml._text_buffer, b"")
		self.xml._tag_buffer.clear()
		self.assertEqual(self.parse(self.raw_data), (self.normal_data, b"", XMLState.DATA))
		self.assert_call_list(mock_on_xml_event.call_args_list, self.expected_events)
		mock_on_xml_event.reset_mock()
		self.xml.output_format = "tintin"
		self.assertEqual(self.parse(self.raw_data), (self.tintin_data, b"", XMLState.DATA))
		self.assert_call_list(mock_on_xml_event.call_args_list, self.expected_events)
		mock_on_xml_event.reset_mock()
		self.xml.output_format = "raw"
		self.assertEqual(self.parse(self.raw_data), (self.raw_data, b"", XMLState.DATA))
		self.assert_call_list(mock_on_xml_event.call_args_list, self.expected_events)
		mock_on_xml_event.reset_mock()
		latin1_tag: bytes = b"<m\xf3vement dir=south/>"
		self.assertEqual(self.parse(latin1_tag), (latin1_tag, b"", XMLState.DATA))
		mock_on_xml_event.assert_called_once_with("movement", b"south")
