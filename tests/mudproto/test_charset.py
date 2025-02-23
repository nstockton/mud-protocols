# Copyright (c) 2025 Nick Stockton
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
	def on_connection_lost(self) -> None:
		pass


class TestCharsetMixIn(TestCase):
	def setUp(self) -> None:
		self.game_receives: bytearray = bytearray()
		self.player_receives: bytearray = bytearray()
		self.telnet: Telnet = Telnet(self.game_receives.extend, self.player_receives.extend, is_client=True)

	def tearDown(self) -> None:
		self.telnet.on_connection_lost()
		del self.telnet
		self.game_receives.clear()
		self.player_receives.clear()

	def parse(self, data: bytes) -> tuple[bytes, bytes]:
		self.telnet.on_data_received(data)
		player_receives: bytes = bytes(self.player_receives)
		self.player_receives.clear()
		game_receives: bytes = bytes(self.game_receives)
		self.game_receives.clear()
		return player_receives, game_receives

	def test_telnet_charset(self) -> None:
		self.telnet._charset = b"UTF-8"
		self.assertEqual(self.telnet.charset, "UTF-8")

	@patch("mudproto.charset.logger", Mock())
	def test_telnet_negotiate_charset(self) -> None:
		self.telnet._charsets = (b"ISO_8859-1:1987", b"UTF-8", b"US-ASCII")
		self.telnet.negotiate_charset(b"**junk**")
		self.assertEqual(self.game_receives, b"")
		self.telnet.negotiate_charset(b"cp1252")
		self.assertEqual(self.game_receives, b"")
		self.telnet.negotiate_charset(b"latin-1")
		self.assertEqual(
			self.game_receives,
			IAC + SB + CHARSET + CHARSET_REQUEST + b";" + self.telnet._charsets[0] + IAC + SE,
		)

	def test_telnet_parse_supported_charsets(self) -> None:
		supported_charsets: bytes = b"ISO_8859-1:1987;ISO-8859-1;UTF-8;US-ASCII"
		separator: bytes = b";"
		result: tuple[bytes, ...] = self.telnet.parse_supported_charsets(separator + supported_charsets)
		self.assertEqual(len(result), 3)
		# ISO_8859-1:1987 and ISO-8859-1 are aliases for the same codec.
		# When 2 or more aliases point to the same codec, the
		# first one should be used and the duplicates removed.
		deduplicated: tuple[bytes, ...] = tuple(
			i for i in supported_charsets.split(separator) if i != b"ISO-8859-1"
		)
		self.assertEqual(result, deduplicated)

	@patch("mudproto.telnet.TelnetProtocol.wont")
	@patch("mudproto.charset.CharsetMixIn.negotiate_charset")
	@patch("mudproto.charset.logger")
	def test_telnet_on_charset(
		self, mock_logger: Mock, mock_negotiate_charset: Mock, mock_wont: Mock
	) -> None:
		# Charset request.
		self.assertEqual(self.telnet._charsets, (b"US-ASCII",))
		self.telnet.on_charset(CHARSET_REQUEST + b";US-ASCII;UTF-8")
		self.assertEqual(self.telnet._charsets, (b"US-ASCII", b"UTF-8"))
		mock_logger.debug.assert_called_once_with(
			"Peer responds: Supported charsets: (b'US-ASCII', b'UTF-8')."
		)
		mock_negotiate_charset.assert_called_once_with(b"US-ASCII")
		self.assertEqual(self.telnet._charset, b"US-ASCII")
		mock_logger.reset_mock()
		mock_negotiate_charset.reset_mock()
		self.telnet._charsets = (b"US-ASCII", b"UTF-8")
		# Charset accepted.
		self.telnet.on_charset(CHARSET_ACCEPTED + b"UTF-8")
		self.assertEqual(self.telnet._charset, b"UTF-8")
		mock_logger.debug.assert_called_once_with("Peer responds: Charset b'UTF-8' accepted.")
		mock_logger.reset_mock()
		self.telnet._charset = b"US-ASCII"
		# Charset rejected.
		self.telnet.on_charset(CHARSET_REJECTED + b"UTF-8")
		self.assertEqual(self.telnet._charset, b"US-ASCII")
		mock_logger.warning.assert_called_once_with("Peer responds: Charset rejected.")
		mock_logger.reset_mock()
		# Invalid response.
		self.telnet.on_charset(b"**junk**")
		self.assertEqual(self.telnet._charset, b"US-ASCII")
		mock_wont.assert_called_once_with(CHARSET)

	@patch("mudproto.charset.logger", Mock())
	def test_telnet_on_enable_local(self) -> None:
		self.assertTrue(self.telnet.on_enable_local(CHARSET))

	@patch("mudproto.charset.logger", Mock())
	def test_telnet_on_disable_local(self) -> None:
		self.telnet.on_disable_local(CHARSET)  # Should not throw an exception.
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
