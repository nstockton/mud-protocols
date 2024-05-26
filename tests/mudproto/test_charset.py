# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
from unittest import TestCase
from unittest.mock import Mock, patch

# MUD Protocol Modules:
from mudproto.charset import CharsetMixIn
from mudproto.telnet import TelnetProtocol
from mudproto.telnet_constants import (
	CHARSET,
	CHARSET_ACCEPTED,
	CHARSET_REJECTED,
	CHARSET_REQUEST,
	IAC,
	SB,
	SE,
)


class Telnet(CharsetMixIn, TelnetProtocol):
	def on_connectionLost(self) -> None:
		pass


class TestCharsetMixIn(TestCase):
	def setUp(self) -> None:
		self.gameReceives: bytearray = bytearray()
		self.playerReceives: bytearray = bytearray()
		self.telnet: Telnet = Telnet(self.gameReceives.extend, self.playerReceives.extend, isClient=True)

	def tearDown(self) -> None:
		self.telnet.on_connectionLost()
		del self.telnet
		self.gameReceives.clear()
		self.playerReceives.clear()

	def parse(self, data: bytes) -> tuple[bytes, bytes]:
		self.telnet.on_dataReceived(data)
		playerReceives: bytes = bytes(self.playerReceives)
		self.playerReceives.clear()
		gameReceives: bytes = bytes(self.gameReceives)
		self.gameReceives.clear()
		return playerReceives, gameReceives

	def testTelnetCharset(self) -> None:
		self.telnet._charset = b"UTF-8"
		self.assertEqual(self.telnet.charset, "UTF-8")

	@patch("mudproto.charset.logger", Mock())
	def testTelnetNegotiateCharset(self) -> None:
		self.telnet._charsets = (b"ISO_8859-1:1987", b"UTF-8", b"US-ASCII")
		self.telnet.negotiateCharset(b"**junk**")
		self.assertEqual(self.gameReceives, b"")
		self.telnet.negotiateCharset(b"cp1252")
		self.assertEqual(self.gameReceives, b"")
		self.telnet.negotiateCharset(b"latin-1")
		self.assertEqual(
			self.gameReceives,
			IAC + SB + CHARSET + CHARSET_REQUEST + b";" + self.telnet._charsets[0] + IAC + SE,
		)

	def testTelnetParseSupportedCharsets(self) -> None:
		supportedCharsets: bytes = b"ISO_8859-1:1987;ISO-8859-1;UTF-8;US-ASCII"
		separator: bytes = b";"
		result: tuple[bytes, ...] = self.telnet.parseSupportedCharsets(separator + supportedCharsets)
		self.assertEqual(len(result), 3)
		# ISO_8859-1:1987 and ISO-8859-1 are aliases for the same codec.
		# When 2 or more aliases point to the same codec, the first one should be used and the duplicates removed.
		deduplicated: tuple[bytes, ...] = tuple(
			i for i in supportedCharsets.split(separator) if i != b"ISO-8859-1"
		)
		self.assertEqual(result, deduplicated)

	@patch("mudproto.telnet.TelnetProtocol.wont")
	@patch("mudproto.charset.CharsetMixIn.negotiateCharset")
	@patch("mudproto.charset.logger")
	def testTelnetOn_charset(self, mockLogger: Mock, mockNegotiateCharset: Mock, mockWont: Mock) -> None:
		# Charset request.
		self.assertEqual(self.telnet._charsets, (b"US-ASCII",))
		self.telnet.on_charset(CHARSET_REQUEST + b";US-ASCII;UTF-8")
		self.assertEqual(self.telnet._charsets, (b"US-ASCII", b"UTF-8"))
		mockLogger.debug.assert_called_once_with(
			"Peer responds: Supported charsets: (b'US-ASCII', b'UTF-8')."
		)
		mockNegotiateCharset.assert_called_once_with(b"US-ASCII")
		self.assertEqual(self.telnet._charset, b"US-ASCII")
		mockLogger.reset_mock()
		mockNegotiateCharset.reset_mock()
		self.telnet._charsets = (b"US-ASCII", b"UTF-8")
		# Charset accepted.
		self.telnet.on_charset(CHARSET_ACCEPTED + b"UTF-8")
		self.assertEqual(self.telnet._charset, b"UTF-8")
		mockLogger.debug.assert_called_once_with("Peer responds: Charset b'UTF-8' accepted.")
		mockLogger.reset_mock()
		self.telnet._charset = b"US-ASCII"
		# Charset rejected.
		self.telnet.on_charset(CHARSET_REJECTED + b"UTF-8")
		self.assertEqual(self.telnet._charset, b"US-ASCII")
		mockLogger.warning.assert_called_once_with("Peer responds: Charset rejected.")
		mockLogger.reset_mock()
		# Invalid response.
		self.telnet.on_charset(b"**junk**")
		self.assertEqual(self.telnet._charset, b"US-ASCII")
		mockWont.assert_called_once_with(CHARSET)

	@patch("mudproto.charset.logger", Mock())
	def testTelnetOn_enableLocal(self) -> None:
		self.assertTrue(self.telnet.on_enableLocal(CHARSET))

	@patch("mudproto.charset.logger", Mock())
	def testTelnetOn_disableLocal(self) -> None:
		self.telnet.on_disableLocal(CHARSET)  # Should not throw an exception.
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
