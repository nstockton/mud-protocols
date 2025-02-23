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
from mudproto.naws import UINT16_MAX, Dimensions, NAWSMixIn
from mudproto.naws import logger as naws_logger
from mudproto.telnet import TelnetProtocol
from mudproto.telnet_constants import NAWS


class Telnet(NAWSMixIn, TelnetProtocol):
	"""Telnet protocol with NAWS support."""


class TestNAWSMixIn(TestCase):
	def setUp(self) -> None:
		self.game_receives: bytearray = bytearray()
		self.player_receives: bytearray = bytearray()
		self.telnet_client: Telnet = Telnet(
			self.game_receives.extend,
			self.player_receives.extend,
			is_client=True,
		)
		self.telnet_server: Telnet = Telnet(
			self.game_receives.extend,
			self.player_receives.extend,
			is_client=False,
		)

	def tearDown(self) -> None:
		del self.telnet_client
		del self.telnet_server
		self.game_receives.clear()
		self.player_receives.clear()

	@patch("mudproto.telnet.TelnetProtocol.request_negotiation")
	def test_naws_dimensions_set_when_invalid_value(self, mock_request_negotiation: Mock) -> None:
		self.assertEqual(self.telnet_client.naws_dimensions, Dimensions(0, 0))
		with self.assertRaises(ValueError):
			self.telnet_client.naws_dimensions = Dimensions(-1, 0)
		with self.assertRaises(ValueError):
			self.telnet_client.naws_dimensions = Dimensions(UINT16_MAX + 1, 0)
		with self.assertRaises(ValueError):
			self.telnet_client.naws_dimensions = Dimensions(0, -1)
		with self.assertRaises(ValueError):
			self.telnet_client.naws_dimensions = Dimensions(0, UINT16_MAX + 1)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(self.telnet_client.naws_dimensions, Dimensions(0, 0))
		mock_request_negotiation.assert_not_called()

	@patch("mudproto.telnet.TelnetProtocol.request_negotiation")
	def test_naws_dimensions_set_when_running_as_client(self, mock_request_negotiation: Mock) -> None:
		naws_dimensions: Dimensions = Dimensions(80, 25)
		payload: bytes = b"\x00\x50\x00\x19"
		self.assertEqual(self.telnet_client.naws_dimensions, Dimensions(0, 0))
		with self.assertLogs(naws_logger, "DEBUG"):
			self.telnet_client.naws_dimensions = naws_dimensions
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(self.telnet_client.naws_dimensions, naws_dimensions)
		mock_request_negotiation.assert_called_once_with(NAWS, payload)

	@patch("mudproto.telnet.TelnetProtocol.request_negotiation")
	def test_naws_dimensions_set_when_running_as_server(self, mock_request_negotiation: Mock) -> None:
		naws_dimensions: Dimensions = Dimensions(80, 25)
		self.assertEqual(self.telnet_server.naws_dimensions, Dimensions(0, 0))
		self.telnet_server.naws_dimensions = naws_dimensions
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(self.telnet_server.naws_dimensions, naws_dimensions)
		mock_request_negotiation.assert_not_called()

	def test_on_naws_when_running_as_client(self) -> None:
		payload: bytes = b"\x00\x50\x00\x19"
		with self.assertLogs(naws_logger, "WARNING"):
			self.telnet_client.on_naws(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(self.telnet_client.naws_dimensions, Dimensions(0, 0))

	def test_on_naws_when_running_as_server_and_invalid_data(self) -> None:
		with self.assertLogs(naws_logger, "WARNING"):
			self.telnet_server.on_naws(b"**junk**")
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(self.telnet_server.naws_dimensions, Dimensions(0, 0))

	def test_on_naws_when_running_as_server_and_valid_data(self) -> None:
		naws_dimensions: Dimensions = Dimensions(80, 25)
		payload: bytes = b"\x00\x50\x00\x19"
		self.assertEqual(self.telnet_server.naws_dimensions, Dimensions(0, 0))
		with self.assertLogs(naws_logger, "DEBUG"):
			self.telnet_server.on_naws(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(self.telnet_server.naws_dimensions, naws_dimensions)

	@patch("mudproto.telnet.TelnetProtocol.do")
	def test_on_connection_made_when_acting_as_client(self, mock_do: Mock) -> None:
		self.telnet_client.on_connection_made()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_do.assert_not_called()

	@patch("mudproto.telnet.TelnetProtocol.do")
	def test_on_connection_made_when_acting_as_server(self, mock_do: Mock) -> None:
		with self.assertLogs(naws_logger, "DEBUG"):
			self.telnet_server.on_connection_made()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_do.assert_called_once_with(NAWS)

	def test_on_enable_local(self) -> None:
		with self.assertLogs(naws_logger, "DEBUG"):
			self.assertTrue(self.telnet_client.on_enable_local(NAWS))
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_on_disable_local(self) -> None:
		with self.assertLogs(naws_logger, "DEBUG"):
			self.telnet_client.on_disable_local(NAWS)  # Should not throw an exception.
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_on_enable_remote(self) -> None:
		with self.assertLogs(naws_logger, "DEBUG"):
			self.assertTrue(self.telnet_server.on_enable_remote(NAWS))
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_on_disable_remote(self) -> None:
		with self.assertLogs(naws_logger, "DEBUG"):
			self.telnet_server.on_disable_remote(NAWS)  # Should not throw an exception.
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
