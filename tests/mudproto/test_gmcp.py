# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import json
from unittest import TestCase
from unittest.mock import Mock, patch

# MUD Protocol Modules:
from mudproto.gmcp import GMCPMixIn
from mudproto.gmcp import logger as gmcpLogger
from mudproto.telnet import TelnetProtocol
from mudproto.telnet_constants import GMCP


class Telnet(GMCPMixIn, TelnetProtocol):
	"""Telnet protocol with GMCP support."""


class TestGMCPMixIn(TestCase):
	def setUp(self) -> None:
		self.gameReceives: bytearray = bytearray()
		self.playerReceives: bytearray = bytearray()
		self.telnetClient: Telnet = Telnet(
			self.gameReceives.extend,
			self.playerReceives.extend,
			gmcpClientInfo=("test", "1.0"),
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
	def test_gmcpSend_when_value_is_object(self, mockRequestNegotiation: Mock) -> None:
		package: str = "Core.Hello"
		jsonValue: str = json.dumps(
			self.telnetClient._gmcpClientInfo, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {jsonValue}", "utf-8")
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetClient.gmcpSend("Core.Hello", self.telnetClient._gmcpClientInfo)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockRequestNegotiation.assert_called_once_with(GMCP, payload)

	@patch("mudproto.telnet.TelnetProtocol.requestNegotiation")
	def test_gmcpSend_when_value_is_string(self, mockRequestNegotiation: Mock) -> None:
		package: str = "Core.Hello"
		jsonValue: str = json.dumps(
			self.telnetClient._gmcpClientInfo, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {jsonValue}", "utf-8")
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetClient.gmcpSend("Core.Hello", jsonValue, isSerialized=True)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockRequestNegotiation.assert_called_once_with(GMCP, payload)

	@patch("mudproto.telnet.TelnetProtocol.requestNegotiation")
	def test_gmcpSend_when_value_is_bytes(self, mockRequestNegotiation: Mock) -> None:
		package: str = "Core.Hello"
		jsonValue: str = json.dumps(
			self.telnetClient._gmcpClientInfo, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {jsonValue}", "utf-8")
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetClient.gmcpSend("Core.Hello", bytes(jsonValue, "utf-8"), isSerialized=True)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockRequestNegotiation.assert_called_once_with(GMCP, payload)

	@patch("mudproto.gmcp.GMCPMixIn.gmcpSend")
	def test_gmcpHello(self, mockGMCPSend: Mock) -> None:
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetClient.gmcpHello()
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockGMCPSend.assert_called_once_with("Core.Hello", self.telnetClient._gmcpClientInfo)

	@patch("mudproto.gmcp.GMCPMixIn.gmcpSend")
	def test_gmcpSetPackages(self, mockGMCPSend: Mock) -> None:
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 0)
		packages: dict[str, int] = {"Char": 1, "Room": 1}
		self.telnetClient.gmcpSetPackages(packages)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 2)
		mockGMCPSend.assert_called_once_with("Core.Supports.Set", ("Char 1", "Room 1"))
		mockGMCPSend.reset_mock()
		# Sending set after previously called should clear old values before adding new values.
		newPackages: dict[str, int] = {"Char": 2, "Client": 1, "External": 1}
		self.telnetClient.gmcpSetPackages(newPackages)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 3)
		mockGMCPSend.assert_called_once_with("Core.Supports.Set", ("Char 2", "Client 1", "External 1"))

	@patch("mudproto.gmcp.GMCPMixIn.gmcpSend")
	def test_gmcpAddPackages(self, mockGMCPSend: Mock) -> None:
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 0)
		packages: dict[str, int] = {"Char": 1, "Room": 1}
		self.telnetClient.gmcpAddPackages(packages)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 2)
		mockGMCPSend.assert_called_once_with("Core.Supports.Add", ("Char 1", "Room 1"))
		mockGMCPSend.reset_mock()
		# Sending Add after previously called should append/update values without clearing existing values.
		newPackages: dict[str, int] = {"Char": 2, "Client": 1, "External": 1}
		self.telnetClient.gmcpAddPackages(newPackages)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 4)
		self.assertEqual(self.telnetClient._gmcpSupportedPackages["char"], 2)
		mockGMCPSend.assert_called_once_with("Core.Supports.Add", ("Char 2", "Client 1", "External 1"))

	@patch("mudproto.gmcp.GMCPMixIn.gmcpSend")
	def test_gmcpRemovePackages_when_existing_value(self, mockGMCPSend: Mock) -> None:
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 0)
		self.telnetClient._gmcpSupportedPackages["char"] = 1
		self.telnetClient._gmcpSupportedPackages["external"] = 1
		self.telnetClient._gmcpSupportedPackages["room"] = 1
		self.telnetClient.gmcpRemovePackages(("Char", "External"))
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 1)
		mockGMCPSend.assert_called_once_with("Core.Supports.Remove", ("Char", "External"))

	@patch("mudproto.gmcp.GMCPMixIn.gmcpSend")
	def test_gmcpRemovePackages_when_both_existing_and_nonexisting_values(self, mockGMCPSend: Mock) -> None:
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 0)
		self.telnetClient._gmcpSupportedPackages["char"] = 1
		self.telnetClient._gmcpSupportedPackages["external"] = 1
		self.telnetClient._gmcpSupportedPackages["room"] = 1
		with self.assertLogs(gmcpLogger, "WARNING"):
			self.telnetClient.gmcpRemovePackages(("Char", "**junk**"))
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 2)
		mockGMCPSend.assert_called_once_with("Core.Supports.Remove", ("Char",))

	@patch("mudproto.gmcp.GMCPMixIn.gmcpSend")
	def test_gmcpRemovePackages_when_not_existing_value(self, mockGMCPSend: Mock) -> None:
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 0)
		self.telnetClient._gmcpSupportedPackages["char"] = 1
		self.telnetClient._gmcpSupportedPackages["external"] = 1
		self.telnetClient._gmcpSupportedPackages["room"] = 1
		with self.assertLogs(gmcpLogger, "WARNING"):
			self.telnetClient.gmcpRemovePackages(("**junk**",))
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertEqual(len(self.telnetClient._gmcpSupportedPackages), 3)
		mockGMCPSend.assert_not_called()

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcpMessage")
	def test_on_gmcp(self, mockOn_gmcpMessage: Mock) -> None:
		# Test invalid data.
		with self.assertLogs(gmcpLogger, "WARNING"):
			self.telnetClient.on_gmcp(b"**junk**")
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockOn_gmcpMessage.assert_not_called()
		# Test valid data.
		package: str = "Char.Name"
		value: dict[str, str] = {"name": "Gandalf", "fullname": "Gandalf the Grey"}
		jsonValue: str = json.dumps(value, ensure_ascii=False, indent=None, separators=(", ", ": "))
		payload: bytes = bytes(f"{package} {jsonValue}", "utf-8")
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetClient.on_gmcp(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockOn_gmcpMessage.assert_called_once_with(package.lower(), bytes(jsonValue, "utf-8"))
		mockOn_gmcpMessage.reset_mock()
		# Test received valid data, but before initial GMCP Hello as server.
		self.assertFalse(self.telnetServer.isGMCPInitialized)
		with self.assertLogs(gmcpLogger, "WARNING"):
			self.telnetServer.on_gmcp(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockOn_gmcpMessage.assert_called_once_with(package.lower(), bytes(jsonValue, "utf-8"))
		mockOn_gmcpMessage.reset_mock()
		# Test received initial GMCP Hello as server.
		package = "Core.Hello"
		jsonValue = json.dumps(
			self.telnetClient._gmcpClientInfo, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload = bytes(f"{package} {jsonValue}", "utf-8")
		self.assertFalse(self.telnetServer.isGMCPInitialized)
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetServer.on_gmcp(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertTrue(self.telnetServer.isGMCPInitialized)
		mockOn_gmcpMessage.assert_not_called()
		# Test received a second GMCP Hello as server.
		self.assertTrue(self.telnetServer.isGMCPInitialized)
		with self.assertLogs(gmcpLogger, "WARNING"):
			self.telnetServer.on_gmcp(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockOn_gmcpMessage.assert_not_called()

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcpMessage")
	def test_on_gmcp_when_invalid_data(self, mockOn_gmcpMessage: Mock) -> None:
		with self.assertLogs(gmcpLogger, "WARNING"):
			self.telnetClient.on_gmcp(b"**junk**")
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockOn_gmcpMessage.assert_not_called()

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcpMessage")
	def test_on_gmcp_when_valid_data(self, mockOn_gmcpMessage: Mock) -> None:
		package: str = "Char.Name"
		value: dict[str, str] = {"name": "Gandalf", "fullname": "Gandalf the Grey"}
		jsonValue: str = json.dumps(value, ensure_ascii=False, indent=None, separators=(", ", ": "))
		payload: bytes = bytes(f"{package} {jsonValue}", "utf-8")
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetClient.on_gmcp(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockOn_gmcpMessage.assert_called_once_with(package.lower(), bytes(jsonValue, "utf-8"))

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcpMessage")
	def test_on_gmcp_when_valid_data_before_initial_hello(self, mockOn_gmcpMessage: Mock) -> None:
		# This might only happen if acting as GMCP server.
		package: str = "Char.Name"
		value: dict[str, str] = {"name": "Gandalf", "fullname": "Gandalf the Grey"}
		jsonValue: str = json.dumps(value, ensure_ascii=False, indent=None, separators=(", ", ": "))
		payload: bytes = bytes(f"{package} {jsonValue}", "utf-8")
		self.assertFalse(self.telnetServer.isGMCPInitialized)
		with self.assertLogs(gmcpLogger, "WARNING"):
			self.telnetServer.on_gmcp(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockOn_gmcpMessage.assert_called_once_with(package.lower(), bytes(jsonValue, "utf-8"))

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcpMessage")
	def test_on_gmcp_when_received_initial_hello(self, mockOn_gmcpMessage: Mock) -> None:
		# This might only happen if acting as GMCP server.
		package: str = "Core.Hello"
		jsonValue: str = json.dumps(
			self.telnetClient._gmcpClientInfo, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {jsonValue}", "utf-8")
		self.assertFalse(self.telnetServer.isGMCPInitialized)
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetServer.on_gmcp(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.assertTrue(self.telnetServer.isGMCPInitialized)
		mockOn_gmcpMessage.assert_not_called()

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcpMessage")
	def test_on_gmcp_when_received_multiple_hellos(self, mockOn_gmcpMessage: Mock) -> None:
		# This might only happen if acting as GMCP server.
		package: str = "Core.Hello"
		jsonValue: str = json.dumps(
			self.telnetClient._gmcpClientInfo, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {jsonValue}", "utf-8")
		self.assertFalse(self.telnetServer.isGMCPInitialized)
		self.telnetServer._isGMCPInitialized = True  # Indicate that Hello was previously received.
		with self.assertLogs(gmcpLogger, "WARNING"):
			self.telnetServer.on_gmcp(payload)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockOn_gmcpMessage.assert_not_called()

	@patch("mudproto.telnet.TelnetProtocol.will")
	def test_on_connectionMade_when_acting_as_server(self, mockWill: Mock) -> None:
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetServer.on_connectionMade()
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockWill.assert_called_once_with(GMCP)

	@patch("mudproto.telnet.TelnetProtocol.will")
	def test_on_connectionMade_when_acting_as_client(self, mockWill: Mock) -> None:
		self.telnetClient.on_connectionMade()
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockWill.assert_not_called()

	def test_on_enableLocal(self) -> None:
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.assertTrue(self.telnetServer.on_enableLocal(GMCP))
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))

	def test_on_disableLocal(self) -> None:
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetServer.on_disableLocal(GMCP)  # Should not throw an exception.
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))

	def test_on_enableRemote(self) -> None:
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.assertTrue(self.telnetClient.on_enableRemote(GMCP))
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))

	def test_on_disableRemote(self) -> None:
		with self.assertLogs(gmcpLogger, "DEBUG"):
			self.telnetClient.on_disableRemote(GMCP)  # Should not throw an exception.
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))

	@patch("mudproto.gmcp.GMCPMixIn.gmcpHello")
	def test_on_optionEnabled(self, mockGMCPHello: Mock) -> None:
		self.assertFalse(self.telnetClient.isGMCPInitialized)
		self.telnetClient.on_optionEnabled(GMCP)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		mockGMCPHello.assert_called_once()
		self.assertTrue(self.telnetClient.isGMCPInitialized)
