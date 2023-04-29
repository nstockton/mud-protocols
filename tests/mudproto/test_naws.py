# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
from unittest import TestCase
from unittest.mock import Mock, patch

# MUD Protocol Modules:
from mudproto.naws import NAWSMixIn
from mudproto.naws import logger as nawsLogger
from mudproto.telnet import TelnetProtocol
from mudproto.telnet_constants import NAWS


class Telnet(NAWSMixIn, TelnetProtocol):
	"""
	Telnet protocol with NAWS support.
	"""


class TestNAWSMixIn(TestCase):
	def setUp(self) -> None:
		self.gameReceives: bytearray = bytearray()
		self.playerReceives: bytearray = bytearray()
		self.telnetClient: Telnet = Telnet(
			self.gameReceives.extend,
			self.playerReceives.extend,
			isClient=True,
		)
		self.telnetServer: Telnet = Telnet(
			self.gameReceives.extend,
			self.playerReceives.extend,
			isClient=False,
		)

	def tearDown(self) -> None:
		del self.telnetClient
		del self.telnetServer
		self.gameReceives.clear()
		self.playerReceives.clear()

	@patch("mudproto.telnet.TelnetProtocol.requestNegotiation")
	def test_dimensions_set_when_invalid_value(self, mockRequestNegotiation: Mock) -> None:
		self.assertEqual(self.telnetClient.dimensions, (0, 0))
		with self.assertRaises(ValueError):
			self.telnetClient.dimensions = (-1, 0)
		with self.assertRaises(ValueError):
			self.telnetClient.dimensions = (0, -1)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(self.telnetClient.dimensions, (0, 0))
		mockRequestNegotiation.assert_not_called()

	@patch("mudproto.telnet.TelnetProtocol.requestNegotiation")
	def test_dimensions_set_when_running_as_client(self, mockRequestNegotiation: Mock) -> None:
		dimensions: tuple[int, int] = (80, 25)
		payload: bytes = b"\x00\x50\x00\x19"
		self.assertEqual(self.telnetClient.dimensions, (0, 0))
		with self.assertLogs(nawsLogger, "DEBUG"):
			self.telnetClient.dimensions = dimensions
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(self.telnetClient.dimensions, dimensions)
		mockRequestNegotiation.assert_called_once_with(NAWS, payload)

	@patch("mudproto.telnet.TelnetProtocol.requestNegotiation")
	def test_dimensions_set_when_running_as_server(self, mockRequestNegotiation: Mock) -> None:
		dimensions: tuple[int, int] = (80, 25)
		self.assertEqual(self.telnetServer.dimensions, (0, 0))
		self.telnetServer.dimensions = dimensions
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(self.telnetServer.dimensions, dimensions)
		mockRequestNegotiation.assert_not_called()

	def test_on_naws_when_running_as_client(self) -> None:
		payload: bytes = b"\x00\x50\x00\x19"
		with self.assertLogs(nawsLogger, "WARNING"):
			self.telnetClient.on_naws(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(self.telnetClient.dimensions, (0, 0))

	def test_on_naws_when_running_as_server_and_invalid_data(self) -> None:
		with self.assertLogs(nawsLogger, "WARNING"):
			self.telnetServer.on_naws(b"**junk**")
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(self.telnetServer.dimensions, (0, 0))

	def test_on_naws_when_running_as_server_and_valid_data(self) -> None:
		dimensions: tuple[int, int] = (80, 25)
		payload: bytes = b"\x00\x50\x00\x19"
		self.assertEqual(self.telnetServer.dimensions, (0, 0))
		with self.assertLogs(nawsLogger, "DEBUG"):
			self.telnetServer.on_naws(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(self.telnetServer.dimensions, dimensions)

	@patch("mudproto.telnet.TelnetProtocol.do")
	def test_on_connectionMade_when_acting_as_client(self, mockDo: Mock) -> None:
		self.telnetClient.on_connectionMade()
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockDo.assert_not_called()

	@patch("mudproto.telnet.TelnetProtocol.do")
	def test_on_connectionMade_when_acting_as_server(self, mockDo: Mock) -> None:
		with self.assertLogs(nawsLogger, "DEBUG"):
			self.telnetServer.on_connectionMade()
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockDo.assert_called_once_with(NAWS)

	def test_on_enableLocal(self) -> None:
		with self.assertLogs(nawsLogger, "DEBUG"):
			self.assertTrue(self.telnetClient.on_enableLocal(NAWS))
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))

	def test_on_disableLocal(self) -> None:
		with self.assertLogs(nawsLogger, "DEBUG"):
			self.telnetClient.on_disableLocal(NAWS)  # Should not throw an exception.
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))

	def test_on_enableRemote(self) -> None:
		with self.assertLogs(nawsLogger, "DEBUG"):
			self.assertTrue(self.telnetServer.on_enableRemote(NAWS))
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))

	def test_on_disableRemote(self) -> None:
		with self.assertLogs(nawsLogger, "DEBUG"):
			self.telnetServer.on_disableRemote(NAWS)  # Should not throw an exception.
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
