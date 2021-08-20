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
	WILL,
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
		oldCharset: bytes = self.telnet.charset
		self.assertEqual(oldCharset, b"US-ASCII")
		with self.assertRaises(ValueError):
			self.telnet.charset = b"**junk**"
		self.assertEqual(self.telnet.charset, oldCharset)
		self.telnet.charset = b"UTF-8"
		self.assertEqual(self.telnet.charset, b"UTF-8")

	@patch("mudproto.charset.logger", Mock())
	def testTelnetNegotiateCharset(self) -> None:
		oldCharset: bytes = self.telnet.charset
		self.telnet.negotiateCharset(b"**junk**")
		self.assertEqual(
			self.gameReceives, IAC + SB + CHARSET + CHARSET_REQUEST + b";" + oldCharset + IAC + SE
		)
		self.gameReceives.clear()
		self.telnet.negotiateCharset(b"UTF-8")
		self.assertEqual(self.gameReceives, IAC + SB + CHARSET + CHARSET_REQUEST + b";" + b"UTF-8" + IAC + SE)

	@patch("mudproto.telnet.TelnetProtocol.wont")
	@patch("mudproto.charset.logger")
	def testTelnetOn_charset(self, mockLogger: Mock, mockWont: Mock) -> None:
		# self.telnet.charset is the charset the user requested.
		self.telnet.charset = b"UTF-8"
		# self.telnet._oldCharset is the charset the user was using before the request.
		self.telnet._oldCharset = b"US-ASCII"
		# Charset accepted.
		self.telnet.on_charset(CHARSET_ACCEPTED + b"UTF-8")
		mockLogger.debug.assert_called_once_with("Peer responds: Charset b'UTF-8' accepted.")
		mockLogger.reset_mock()
		# Charset rejected, and _oldCharset and charset are the same.
		self.telnet._oldCharset = self.telnet.charset
		self.telnet.on_charset(CHARSET_REJECTED + b"UTF-8")
		mockLogger.warning.assert_called_with(
			f"Unable to fall back to {self.telnet.charset!r}. Old and new charsets match."
		)
		mockLogger.reset_mock()
		# Charset rejected, and _oldCharset and charset differ.
		self.telnet._oldCharset = b"US-ASCII"
		self.telnet.on_charset(CHARSET_REJECTED + b"UTF-8")
		mockLogger.debug.assert_called_once_with("Falling back to b'US-ASCII'.")
		self.assertEqual(self.telnet.charset, b"US-ASCII")
		self.telnet.charset = b"UTF-8"
		# Invalid response.
		self.telnet._oldCharset = b"US-ASCII"
		self.telnet.on_charset(b"**junk**")
		self.assertEqual(self.telnet.charset, b"US-ASCII")
		mockWont.assert_called_once_with(CHARSET)

	@patch("mudproto.charset.logger", Mock())
	@patch("mudproto.telnet.TelnetProtocol.on_connectionMade")
	def testTelnetOn_connectionMade(self, mockOn_connectionMade: Mock) -> None:
		self.telnet.on_connectionMade()
		mockOn_connectionMade.assert_called_once()
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", IAC + WILL + CHARSET))

	@patch("mudproto.charset.logger", Mock())
	@patch("mudproto.charset.CharsetMixIn.negotiateCharset")
	def testTelnetOn_enableLocal(self, mockNegotiateCharset: Mock) -> None:
		self.assertTrue(self.telnet.on_enableLocal(CHARSET))
		mockNegotiateCharset.assert_called_once_with(self.telnet.charset)

	@patch("mudproto.charset.logger", Mock())
	def testTelnetOn_disableLocal(self) -> None:
		self.telnet.on_disableLocal(CHARSET)  # Should not throw an exception.
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
