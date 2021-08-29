# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
from typing import Tuple
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
		self.telnet: Telnet = Telnet(self.gameReceives.extend, self.playerReceives.extend)

	def tearDown(self) -> None:
		self.telnet.on_connectionLost()
		del self.telnet
		self.gameReceives.clear()
		self.playerReceives.clear()

	def parse(self, data: bytes) -> Tuple[bytes, bytes]:
		self.telnet.on_dataReceived(data)
		playerReceives: bytes = bytes(self.playerReceives)
		self.playerReceives.clear()
		gameReceives: bytes = bytes(self.gameReceives)
		self.gameReceives.clear()
		return playerReceives, gameReceives

	def testTelnetCharset(self) -> None:
		self.telnet._charsets = (b"US-ASCII", b"UTF-8")
		oldCharset: bytes = self.telnet.charset
		self.assertEqual(oldCharset, b"US-ASCII")
		with self.assertRaises(ValueError):
			self.telnet.charset = b"**junk**"
		self.assertEqual(self.telnet.charset, oldCharset)
		self.telnet.charset = b"UTF-8"
		self.assertEqual(self.telnet.charset, b"UTF-8")

	@patch("mudproto.charset.logger", Mock())
	def testTelnetNegotiateCharset(self) -> None:
		self.telnet.negotiateCharset(b"**junk**")
		self.assertEqual(self.gameReceives, b"")
		self.telnet._charsets = (b"US-ASCII", b"UTF-8")
		self.telnet.negotiateCharset(b"UTF-8")
		self.assertEqual(self.gameReceives, IAC + SB + CHARSET + CHARSET_REQUEST + b";" + b"UTF-8" + IAC + SE)

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
		self.assertEqual(self.telnet.charset, b"US-ASCII")
		mockLogger.reset_mock()
		mockNegotiateCharset.reset_mock()
		self.telnet._charsets = (b"US-ASCII", b"UTF-8")
		# Charset accepted.
		self.telnet.on_charset(CHARSET_ACCEPTED + b"UTF-8")
		self.assertEqual(self.telnet.charset, b"UTF-8")
		mockLogger.debug.assert_called_once_with("Peer responds: Charset b'UTF-8' accepted.")
		mockLogger.reset_mock()
		self.telnet.charset = b"US-ASCII"
		# Charset rejected.
		self.telnet.on_charset(CHARSET_REJECTED + b"UTF-8")
		self.assertEqual(self.telnet.charset, b"US-ASCII")
		mockLogger.warning.assert_called_once_with("Peer responds: Charset rejected.")
		mockLogger.reset_mock()
		# Invalid response.
		self.telnet.on_charset(b"**junk**")
		self.assertEqual(self.telnet.charset, b"US-ASCII")
		mockWont.assert_called_once_with(CHARSET)

	@patch("mudproto.charset.logger", Mock())
	def testTelnetOn_enableLocal(self) -> None:
		self.assertTrue(self.telnet.on_enableLocal(CHARSET))

	@patch("mudproto.charset.logger", Mock())
	def testTelnetOn_disableLocal(self) -> None:
		self.telnet.on_disableLocal(CHARSET)  # Should not throw an exception.
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
