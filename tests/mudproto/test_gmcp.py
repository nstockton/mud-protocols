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
from mudproto.gmcp import logger as gmcp_logger
from mudproto.telnet import TelnetProtocol
from mudproto.telnet_constants import GMCP


class Telnet(GMCPMixIn, TelnetProtocol):
	"""Telnet protocol with GMCP support."""


class TestGMCPMixIn(TestCase):
	def setUp(self) -> None:
		self.game_receives: bytearray = bytearray()
		self.player_receives: bytearray = bytearray()
		self.telnet_client: Telnet = Telnet(
			self.game_receives.extend,
			self.player_receives.extend,
			gmcp_client_info=("test", "1.0"),
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
	def test_gmcp_send_when_value_is_object(self, mock_request_negotiation: Mock) -> None:
		package: str = "Core.Hello"
		json_value: str = json.dumps(
			self.telnet_client._gmcp_client_info, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {json_value}", "utf-8")
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_client.gmcp_send("Core.Hello", self.telnet_client._gmcp_client_info)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_request_negotiation.assert_called_once_with(GMCP, payload)

	@patch("mudproto.telnet.TelnetProtocol.request_negotiation")
	def test_gmcp_send_when_value_is_string(self, mock_request_negotiation: Mock) -> None:
		package: str = "Core.Hello"
		json_value: str = json.dumps(
			self.telnet_client._gmcp_client_info, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {json_value}", "utf-8")
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_client.gmcp_send("Core.Hello", json_value, is_serialized=True)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_request_negotiation.assert_called_once_with(GMCP, payload)

	@patch("mudproto.telnet.TelnetProtocol.request_negotiation")
	def test_gmcp_send_when_value_is_bytes(self, mock_request_negotiation: Mock) -> None:
		package: str = "Core.Hello"
		json_value: str = json.dumps(
			self.telnet_client._gmcp_client_info, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {json_value}", "utf-8")
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_client.gmcp_send("Core.Hello", bytes(json_value, "utf-8"), is_serialized=True)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_request_negotiation.assert_called_once_with(GMCP, payload)

	@patch("mudproto.gmcp.GMCPMixIn.gmcp_send")
	def test_gmcp_hello(self, mock_gmcp_send: Mock) -> None:
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_client.gmcp_hello()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_gmcp_send.assert_called_once_with("Core.Hello", self.telnet_client._gmcp_client_info)

	@patch("mudproto.gmcp.GMCPMixIn.gmcp_send")
	def test_gmcp_set_packages(self, mock_gmcp_send: Mock) -> None:
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 0)
		packages: dict[str, int] = {"Char": 1, "Room": 1}
		self.telnet_client.gmcp_set_packages(packages)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 2)
		mock_gmcp_send.assert_called_once_with("Core.Supports.Set", ("Char 1", "Room 1"))
		mock_gmcp_send.reset_mock()
		# Sending set after previously called should clear old values before adding new values.
		new_packages: dict[str, int] = {"Char": 2, "Client": 1, "External": 1}
		self.telnet_client.gmcp_set_packages(new_packages)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 3)
		mock_gmcp_send.assert_called_once_with("Core.Supports.Set", ("Char 2", "Client 1", "External 1"))

	@patch("mudproto.gmcp.GMCPMixIn.gmcp_send")
	def test_gmcp_add_packages(self, mock_gmcp_send: Mock) -> None:
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 0)
		packages: dict[str, int] = {"Char": 1, "Room": 1}
		self.telnet_client.gmcp_add_packages(packages)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 2)
		mock_gmcp_send.assert_called_once_with("Core.Supports.Add", ("Char 1", "Room 1"))
		mock_gmcp_send.reset_mock()
		# Sending Add after previously called should append/update values without clearing existing values.
		new_packages: dict[str, int] = {"Char": 2, "Client": 1, "External": 1}
		self.telnet_client.gmcp_add_packages(new_packages)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 4)
		self.assertEqual(self.telnet_client._gmcp_supported_packages["char"], 2)
		mock_gmcp_send.assert_called_once_with("Core.Supports.Add", ("Char 2", "Client 1", "External 1"))

	@patch("mudproto.gmcp.GMCPMixIn.gmcp_send")
	def test_gmcp_remove_packages_when_existing_value(self, mock_gmcp_send: Mock) -> None:
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 0)
		self.telnet_client._gmcp_supported_packages["char"] = 1
		self.telnet_client._gmcp_supported_packages["external"] = 1
		self.telnet_client._gmcp_supported_packages["room"] = 1
		self.telnet_client.gmcp_remove_packages(("Char", "External"))
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 1)
		mock_gmcp_send.assert_called_once_with("Core.Supports.Remove", ("Char", "External"))

	@patch("mudproto.gmcp.GMCPMixIn.gmcp_send")
	def test_gmcp_remove_packages_when_both_existing_and_nonexisting_values(
		self, mock_gmcp_send: Mock
	) -> None:
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 0)
		self.telnet_client._gmcp_supported_packages["char"] = 1
		self.telnet_client._gmcp_supported_packages["external"] = 1
		self.telnet_client._gmcp_supported_packages["room"] = 1
		with self.assertLogs(gmcp_logger, "WARNING"):
			self.telnet_client.gmcp_remove_packages(("Char", "**junk**"))
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 2)
		mock_gmcp_send.assert_called_once_with("Core.Supports.Remove", ("Char",))

	@patch("mudproto.gmcp.GMCPMixIn.gmcp_send")
	def test_gmcp_remove_packages_when_not_existing_value(self, mock_gmcp_send: Mock) -> None:
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 0)
		self.telnet_client._gmcp_supported_packages["char"] = 1
		self.telnet_client._gmcp_supported_packages["external"] = 1
		self.telnet_client._gmcp_supported_packages["room"] = 1
		with self.assertLogs(gmcp_logger, "WARNING"):
			self.telnet_client.gmcp_remove_packages(("**junk**",))
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertEqual(len(self.telnet_client._gmcp_supported_packages), 3)
		mock_gmcp_send.assert_not_called()

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcp_message")
	def test_on_gmcp(self, mock_on_gmcp_message: Mock) -> None:
		# Test invalid data.
		with self.assertLogs(gmcp_logger, "WARNING"):
			self.telnet_client.on_gmcp(b"**junk**")
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_on_gmcp_message.assert_not_called()
		# Test valid data.
		package: str = "Char.Name"
		value: dict[str, str] = {"name": "Gandalf", "fullname": "Gandalf the Grey"}
		json_value: str = json.dumps(value, ensure_ascii=False, indent=None, separators=(", ", ": "))
		payload: bytes = bytes(f"{package} {json_value}", "utf-8")
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_client.on_gmcp(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_on_gmcp_message.assert_called_once_with(package.lower(), bytes(json_value, "utf-8"))
		mock_on_gmcp_message.reset_mock()
		# Test received valid data, but before initial GMCP Hello as server.
		self.assertFalse(self.telnet_server.is_gmcp_initialized)
		with self.assertLogs(gmcp_logger, "WARNING"):
			self.telnet_server.on_gmcp(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_on_gmcp_message.assert_called_once_with(package.lower(), bytes(json_value, "utf-8"))
		mock_on_gmcp_message.reset_mock()
		# Test received initial GMCP Hello as server.
		package = "Core.Hello"
		json_value = json.dumps(
			self.telnet_client._gmcp_client_info, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload = bytes(f"{package} {json_value}", "utf-8")
		self.assertFalse(self.telnet_server.is_gmcp_initialized)
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_server.on_gmcp(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertTrue(self.telnet_server.is_gmcp_initialized)
		mock_on_gmcp_message.assert_not_called()
		# Test received a second GMCP Hello as server.
		self.assertTrue(self.telnet_server.is_gmcp_initialized)
		with self.assertLogs(gmcp_logger, "WARNING"):
			self.telnet_server.on_gmcp(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_on_gmcp_message.assert_not_called()

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcp_message")
	def test_on_gmcp_when_invalid_data(self, mock_on_gmcp_message: Mock) -> None:
		with self.assertLogs(gmcp_logger, "WARNING"):
			self.telnet_client.on_gmcp(b"**junk**")
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_on_gmcp_message.assert_not_called()

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcp_message")
	def test_on_gmcp_when_valid_data(self, mock_on_gmcp_message: Mock) -> None:
		package: str = "Char.Name"
		value: dict[str, str] = {"name": "Gandalf", "fullname": "Gandalf the Grey"}
		json_value: str = json.dumps(value, ensure_ascii=False, indent=None, separators=(", ", ": "))
		payload: bytes = bytes(f"{package} {json_value}", "utf-8")
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_client.on_gmcp(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_on_gmcp_message.assert_called_once_with(package.lower(), bytes(json_value, "utf-8"))

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcp_message")
	def test_on_gmcp_when_valid_data_before_initial_hello(self, mock_on_gmcp_message: Mock) -> None:
		# This might only happen if acting as GMCP server.
		package: str = "Char.Name"
		value: dict[str, str] = {"name": "Gandalf", "fullname": "Gandalf the Grey"}
		json_value: str = json.dumps(value, ensure_ascii=False, indent=None, separators=(", ", ": "))
		payload: bytes = bytes(f"{package} {json_value}", "utf-8")
		self.assertFalse(self.telnet_server.is_gmcp_initialized)
		with self.assertLogs(gmcp_logger, "WARNING"):
			self.telnet_server.on_gmcp(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_on_gmcp_message.assert_called_once_with(package.lower(), bytes(json_value, "utf-8"))

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcp_message")
	def test_on_gmcp_when_received_initial_hello(self, mock_on_gmcp_message: Mock) -> None:
		# This might only happen if acting as GMCP server.
		package: str = "Core.Hello"
		json_value: str = json.dumps(
			self.telnet_client._gmcp_client_info, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {json_value}", "utf-8")
		self.assertFalse(self.telnet_server.is_gmcp_initialized)
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_server.on_gmcp(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.assertTrue(self.telnet_server.is_gmcp_initialized)
		mock_on_gmcp_message.assert_not_called()

	@patch("mudproto.gmcp.GMCPMixIn.on_gmcp_message")
	def test_on_gmcp_when_received_multiple_hellos(self, mock_on_gmcp_message: Mock) -> None:
		# This might only happen if acting as GMCP server.
		package: str = "Core.Hello"
		json_value: str = json.dumps(
			self.telnet_client._gmcp_client_info, ensure_ascii=False, indent=None, separators=(", ", ": ")
		)
		payload: bytes = bytes(f"{package} {json_value}", "utf-8")
		self.assertFalse(self.telnet_server.is_gmcp_initialized)
		self.telnet_server._is_gmcp_initialized = True  # Indicate that Hello was previously received.
		with self.assertLogs(gmcp_logger, "WARNING"):
			self.telnet_server.on_gmcp(payload)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_on_gmcp_message.assert_not_called()

	@patch("mudproto.telnet.TelnetProtocol.will")
	def test_on_connection_made_when_acting_as_server(self, mock_will: Mock) -> None:
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_server.on_connection_made()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_will.assert_called_once_with(GMCP)

	@patch("mudproto.telnet.TelnetProtocol.will")
	def test_on_connection_made_when_acting_as_client(self, mock_will: Mock) -> None:
		self.telnet_client.on_connection_made()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_will.assert_not_called()

	def test_on_enable_local(self) -> None:
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.assertTrue(self.telnet_server.on_enable_local(GMCP))
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_on_disable_local(self) -> None:
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_server.on_disable_local(GMCP)  # Should not throw an exception.
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_on_enable_remote(self) -> None:
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.assertTrue(self.telnet_client.on_enable_remote(GMCP))
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_on_disable_remote(self) -> None:
		with self.assertLogs(gmcp_logger, "DEBUG"):
			self.telnet_client.on_disable_remote(GMCP)  # Should not throw an exception.
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	@patch("mudproto.gmcp.GMCPMixIn.gmcp_hello")
	def test_on_option_enabled(self, mockgmcp_hello: Mock) -> None:
		self.assertFalse(self.telnet_client.is_gmcp_initialized)
		self.telnet_client.on_option_enabled(GMCP)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mockgmcp_hello.assert_called_once()
		self.assertTrue(self.telnet_client.is_gmcp_initialized)
