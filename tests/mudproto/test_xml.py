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
		detectMagic: bytes = b"\x1b[35mTraces of white tones form the aura of this place.\x1b[0m"
		rawDynamic: bytes = (
			b"A finely crafted <object>crystal lamp</object> is hanging from a tree branch." + LF
			+ b"An <character>elven caretaker</character> is standing here, offering his guests a rest." + LF
		)
		dynamic: bytes = (
			b"A finely crafted crystal lamp is hanging from a tree branch." + LF
			+ b"An elven caretaker is standing here, offering his guests a rest." + LF
		)
		rawExits: bytes = b"<exits>Exits: <exit dir=north id=4805400>north</exit>." + LF + b"</exits>"
		exits: bytes = b"Exits: north." + LF
		magic: bytes = b"You feel less protected."
		line: bytes = b"Hello world!"
		self.rawPrompt: bytes = b"<prompt>!# CW A1 M1 P8 S3 XP:<status>317k</status>&gt;</prompt>"
		self.prompt: bytes = b"!# CW A1 M1 P8 S3 XP:317k>"
		self.rawData: bytes = (
			b"<movement dir=south/>"
			+ b'<room id=13168037 area="Lorien" terrain="forest">'
			+ b"<name>" + name + b"</name>" + LF
			+ b"<gratuitous><description>" + description + b"</description></gratuitous>"
			+ b"<terrain>" + terrain + b"</terrain>" + LF
			+ b"<magic>" + detectMagic + b"</magic>" + LF
			+ rawDynamic
			+ rawExits
			+ b"</room>" + LF
			+ b"<magic>" + magic + b"</magic>" + LF
			+ line + LF
			+ self.rawPrompt
		)
		self.normalData: bytes = (
			name + LF
			+ terrain + LF
			+ detectMagic + LF
			+ dynamic
			+ exits + LF
			+ magic + LF
			+ line + LF
			+ self.prompt
		)
		self.tintinData: bytes = (
			b"NAME:" + name + b":NAME" + LF
			+ terrain + LF
			+ detectMagic + LF
			+ dynamic
			+ exits + LF
			+ magic + LF
			+ line + LF
			+ b"PROMPT:" + self.prompt + b":PROMPT"
		)
		# fmt: on
		self.expectedEvents: list[Callable[[tuple[str, bytes]], _Call]] = [
			call("movement", b"south"),
			call("room", b'id=13168037 area="Lorien" terrain="forest"'),
			call("name", name),
			call("description", description),
			call("terrain", terrain),
			call("magic", detectMagic),
			call("exits", exits),
			call("dynamic", dynamic),
			call("magic", magic),
			call("line", line),
			call("prompt", self.prompt),
		]
		self.gameReceives: bytearray = bytearray()
		self.playerReceives: bytearray = bytearray()
		self.xml: XMLProtocol = XMLProtocol(
			self.gameReceives.extend,
			self.playerReceives.extend,
			outputFormat="normal",
			isClient=True,
		)

	def tearDown(self) -> None:
		self.xml.on_connectionLost()
		del self.xml
		self.gameReceives.clear()
		self.playerReceives.clear()

	def parse(self, data: bytes) -> tuple[bytes, bytes, XMLState]:
		self.xml.on_dataReceived(data)
		playerReceives: bytes = bytes(self.playerReceives)
		self.playerReceives.clear()
		gameReceives: bytes = bytes(self.gameReceives)
		self.gameReceives.clear()
		state: XMLState = self.xml.state
		self.xml.state = XMLState.DATA
		return playerReceives, gameReceives, state

	def assertCallList(
		self,
		originalCalls: Iterable[Callable[..., _Call]],
		expectedCalls: Iterable[Callable[..., _Call]],
	) -> None:
		for original, expected in zip_longest(originalCalls, expectedCalls):
			self.assertEqual(original, expected)

	@patch("mudproto.xml.XMLProtocol.on_xmlEvent")
	def testXMLOn_dataReceived(self, mockOnEvent: Mock) -> None:
		data: bytes = b"Hello World!" + LF
		self.xml.outputFormat = "normal"
		self.xml.on_connectionMade()
		self.assertEqual(self.parse(data), (data, MPI_INIT + b"X2" + LF + b"3G" + LF, XMLState.DATA))
		mockOnEvent.assert_called_once_with("line", data.rstrip(LF))
		mockOnEvent.reset_mock()
		# Insure that partial lines are properly buffered.
		for delimiter in (CR, LF):
			self.assertEqual(self.parse(b"partial"), (b"partial", b"", XMLState.DATA))
			mockOnEvent.assert_not_called()
			self.assertEqual(self.parse(delimiter), (delimiter, b"", XMLState.DATA))
			mockOnEvent.assert_called_once_with("line", b"partial")
			mockOnEvent.reset_mock()
		self.assertEqual(self.parse(LT + b"IncompleteTag"), (b"", b"", XMLState.TAG))
		mockOnEvent.assert_not_called()
		self.assertEqual(self.xml._tagBuffer, b"IncompleteTag")
		self.assertEqual(self.xml._textBuffer, b"")
		self.xml._tagBuffer.clear()
		self.assertEqual(self.parse(self.rawData), (self.normalData, b"", XMLState.DATA))
		self.assertCallList(mockOnEvent.call_args_list, self.expectedEvents)
		mockOnEvent.reset_mock()
		self.xml.outputFormat = "tintin"
		self.assertEqual(self.parse(self.rawData), (self.tintinData, b"", XMLState.DATA))
		self.assertCallList(mockOnEvent.call_args_list, self.expectedEvents)
		mockOnEvent.reset_mock()
		self.xml.outputFormat = "raw"
		self.assertEqual(self.parse(self.rawData), (self.rawData, b"", XMLState.DATA))
		self.assertCallList(mockOnEvent.call_args_list, self.expectedEvents)
		mockOnEvent.reset_mock()
		latin1Tag: bytes = b"<m\xf3vement dir=south/>"
		self.assertEqual(self.parse(latin1Tag), (latin1Tag, b"", XMLState.DATA))
		mockOnEvent.assert_called_once_with("movement", b"south")
