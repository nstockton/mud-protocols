# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
from unittest import TestCase

# MUD Protocol Modules:
from mudproto.mpi import MPI_INIT
from mudproto.telnet_constants import CR, LF
from mudproto.utils import unescapeXMLBytes
from mudproto.xml import EVENT_CALLER_TYPE, LT, XMLProtocol


class TestXMLProtocol(TestCase):
	def setUp(self) -> None:
		name: bytes = b"\x1b[34mLower Flet\x1b[0m"
		# fmt: off
		description: bytes = (
			b"\x1b[35mBeing close to the ground, this white platform is not encircled by any rail.\x1b[0m" + LF
			+ b"\x1b[35mInstead, beautiful draperies and tapestries hang from the many branches that\x1b[0m" + LF
			+ b"\x1b[35msurround the flet. Swaying gently in the breeze, images on the colourful\x1b[0m" + LF
			+ b"\x1b[35mcloth create a place where one can stand and let the mind wander into the\x1b[0m" + LF
			+ b"\x1b[35mstories told by the everchanging patterns.\x1b[0m" + LF
		)
		detectMagic: bytes = b"\x1b[35mTraces of white tones form the aura of this place.\x1b[0m"
		dynamic: bytes = (
			b"A finely crafted crystal lamp is hanging from a tree branch." + LF
			+ b"An elven caretaker is standing here, offering his guests a rest." + LF
		)
		exits: bytes = b"Exits: north." + LF
		magic: bytes = b"You feel less protected."
		line: bytes = b"Hello world!"
		prompt: bytes = b"*f CW&gt;"
		self.rawData: bytes = (
			b"<movement dir=south/>"
			+ b'<room area="Lorien" terrain="forest"><name>' + name + b"</name>" + LF
			+ b"<gratuitous><description>" + description + b"</description></gratuitous>"
			+ b"<magic>" + detectMagic + b"</magic>" + LF
			+ dynamic
			+ b"<exits>" + exits + b"</exits></room>" + LF
			+ b"<magic>" + magic + b"</magic>" + LF
			+ line + LF
			+ b"<prompt>" + prompt + b"</prompt>"
		)
		self.normalData: bytes = (
			name + LF
			+ detectMagic + LF
			+ dynamic
			+ exits + LF
			+ magic + LF
			+ line + LF
			+ unescapeXMLBytes(prompt)
		)
		self.tintinData: bytes = (
			b"NAME:" + name + b":NAME" + LF
			+ detectMagic + LF
			+ dynamic
			+ exits + LF
			+ magic + LF
			+ line + LF
			+ b"PROMPT:" + unescapeXMLBytes(prompt) + b":PROMPT"
		)
		# fmt: on
		self.expectedEvents: list[EVENT_CALLER_TYPE] = [
			("movement", b"south"),
			("room", b'area="Lorien" terrain="forest"'),
			("name", name),
			("description", description),
			("magic", detectMagic),
			("exits", exits),
			("dynamic", dynamic),
			("magic", magic),
			("line", line),
			("prompt", unescapeXMLBytes(prompt)),
		]
		self.gameReceives: bytearray = bytearray()
		self.playerReceives: bytearray = bytearray()
		self.receivedEvents: list[EVENT_CALLER_TYPE] = []
		self.xml: XMLProtocol = XMLProtocol(
			self.gameReceives.extend,
			self.playerReceives.extend,
			outputFormat="normal",
			eventCaller=self.receivedEvents.append,
		)

	def tearDown(self) -> None:
		self.xml.on_connectionLost()
		del self.xml
		self.gameReceives.clear()
		self.playerReceives.clear()

	def parse(self, data: bytes) -> tuple[bytes, bytes, str]:
		self.xml.on_dataReceived(data)
		playerReceives: bytes = bytes(self.playerReceives)
		self.playerReceives.clear()
		gameReceives: bytes = bytes(self.gameReceives)
		self.gameReceives.clear()
		state: str = self.xml.state
		self.xml.state = "data"
		return playerReceives, gameReceives, state

	def testXMLState(self) -> None:
		with self.assertRaises(ValueError):
			self.xml.state = "**junk**"

	def testXMLOn_dataReceived(self) -> None:
		data: bytes = b"Hello World!" + LF
		self.xml.outputFormat = "normal"
		self.xml.on_connectionMade()
		self.assertEqual(self.parse(data), (data, MPI_INIT + b"X2" + LF + b"3G" + LF, "data"))
		self.assertEqual(self.receivedEvents, [("line", data.rstrip(LF))])
		self.receivedEvents.clear()
		# Insure that partial lines are properly buffered.
		for delimiter in (CR, LF):
			self.assertEqual(self.parse(b"partial"), (b"partial", b"", "data"))
			self.assertFalse(self.receivedEvents)
			self.assertEqual(self.parse(delimiter), (delimiter, b"", "data"))
			self.assertEqual(
				self.receivedEvents, [("line", b"partial")], f"When {delimiter!r} is used as line delimiter."
			)
			self.receivedEvents.clear()
		self.assertEqual(self.parse(LT + b"IncompleteTag"), (b"", b"", "tag"))
		self.assertFalse(self.receivedEvents)
		self.assertEqual(self.xml._tagBuffer, b"IncompleteTag")
		self.assertEqual(self.xml._textBuffer, b"")
		self.xml._tagBuffer.clear()
		self.assertEqual(self.parse(self.rawData), (self.normalData, b"", "data"))
		self.assertEqual(self.receivedEvents, self.expectedEvents)
		self.receivedEvents.clear()
		self.xml.outputFormat = "tintin"
		self.assertEqual(self.parse(self.rawData), (self.tintinData, b"", "data"))
		self.assertEqual(self.receivedEvents, self.expectedEvents)
		self.receivedEvents.clear()
		self.xml.outputFormat = "raw"
		self.assertEqual(self.parse(self.rawData), (self.rawData, b"", "data"))
		self.assertEqual(self.receivedEvents, self.expectedEvents)
