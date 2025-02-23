# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Future Modules:
from __future__ import annotations

# Built-in Modules:
from typing import Any
from unittest import TestCase
from unittest.mock import Mock, patch

# MUD Protocol Modules:
from mudproto.connection import ConnectionInterface
from mudproto.manager import Manager
from mudproto.telnet_constants import CR, CR_LF, CR_NULL, GA, IAC, LF


class FakeProtocol(ConnectionInterface):
	def on_connection_made(self) -> None:
		return super().on_connection_made()  # type: ignore[safe-super]

	def on_connection_lost(self) -> None:
		return super().on_connection_lost()  # type: ignore[safe-super]

	def on_data_received(self, data: bytes) -> None:
		return super().on_data_received(data)


class MockProtocol(ConnectionInterface):
	on_connection_made: Mock = Mock()
	on_connection_lost: Mock = Mock()
	on_data_received: Mock = Mock()

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self._receiver: Mock = Mock()


class TestManager(TestCase):
	def setUp(self) -> None:
		self.game_receives: bytearray = bytearray()
		self.player_receives: bytearray = bytearray()
		self.manager: Manager = Manager(
			self.game_receives.extend, self.player_receives.extend, is_client=True, prompt_terminator=CR_LF
		)

	def tearDown(self) -> None:
		self.manager.disconnect()
		del self.manager
		self.game_receives.clear()
		self.player_receives.clear()

	def parse(self, data: bytes) -> tuple[bytes, bytes]:
		self.manager.parse(data)
		player_receives = bytes(self.player_receives)
		self.player_receives.clear()
		game_receives = bytes(self.game_receives)
		self.game_receives.clear()
		return player_receives, game_receives

	def test_manager_init(self) -> None:
		manager: Manager = Manager(
			lambda *args: None, lambda *args: None, is_client=True, prompt_terminator=None
		)
		self.assertEqual(manager.prompt_terminator, IAC + GA)
		del manager

	def test_manager_is_client(self) -> None:
		self.assertEqual(self.manager.is_client, self.manager._is_client)

	def test_manager_is_server(self) -> None:
		self.assertEqual(self.manager.is_server, not self.manager._is_client)

	@patch("mudproto.manager.Manager.disconnect")
	@patch("mudproto.manager.Manager.connect")
	def test_manager_as_context_manager(self, mock_connect: Mock, mock_disconnect: Mock) -> None:
		with self.manager:
			mock_connect.assert_called_once()
		mock_disconnect.assert_called_once()

	@patch("mudproto.manager.Manager.disconnect")
	def test_manager_close(self, mock_disconnect: Mock) -> None:
		self.manager.close()
		mock_disconnect.assert_called_once()

	def test_manager_parse(self) -> None:
		data: bytes = b"Hello World!"
		buffered_data: bytes = b"Some buffered data."
		# Make sure that any data passed to Manager.parse before calling Manager.connect() gets buffered.
		self.assertEqual(self.parse(buffered_data), (b"", b""))
		self.manager.connect()
		# Make sure that any data passed to Manager.parse before registering a protocol gets buffered.
		self.assertEqual(self.parse(buffered_data), (b"", b""))
		self.manager.register(FakeProtocol)
		self.assertEqual(self.parse(data), (buffered_data + buffered_data + data, b""))
		# If the protocol is registered and connected, calling parse with some data should not buffer.
		self.assertEqual(self.parse(data), (data, b""))

	def test_manager_write(self) -> None:
		data: bytes = b"Hello World!"
		buffered_data: bytes = b"Some buffered data."
		# Make sure that any data passed to Manager.write before calling Manager.connect() gets buffered.
		self.manager.write(buffered_data)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.manager.connect()
		# Make sure that any data passed to Manager.write before registering a protocol gets buffered.
		self.manager.write(buffered_data)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		self.manager.register(FakeProtocol)
		self.manager.write(data)
		self.assertEqual(
			(self.player_receives, self.game_receives), (b"", buffered_data + buffered_data + data)
		)
		self.game_receives.clear()
		# Make sure IAC bytes are escaped and line endings are normalized if the escape argument is True.
		self.manager.write(data + IAC + LF + CR, escape=True)
		self.assertEqual(
			(self.player_receives, self.game_receives), (b"", data + IAC + IAC + CR_LF + CR_NULL)
		)
		self.game_receives.clear()
		# Make sure prompt terminator is appended to bytes if the prompt argument is True.
		self.manager.write(data, prompt=True)
		self.assertEqual(
			(self.player_receives, self.game_receives), (b"", data + self.manager.prompt_terminator)
		)

	def test_manager_register(self) -> None:
		with self.assertRaises(TypeError):
			# Handler class required, not instance.
			self.manager.register(
				FakeProtocol(lambda *args: None, lambda *args: None, is_client=True)  # type: ignore[arg-type]
			)
		self.manager.register(FakeProtocol)
		with self.assertRaises(ValueError):
			self.manager.register(FakeProtocol)
		self.assertIsNot(self.manager._handlers[0]._receiver, MockProtocol.on_data_received)
		self.manager.register(MockProtocol)
		self.assertIs(self.manager._handlers[0]._receiver, self.manager._handlers[1].on_data_received)
		mock_on_connection_made: Mock = MockProtocol.on_connection_made
		mock_on_connection_made.assert_called_once()

	def test_manager_unregister(self) -> None:
		self.manager.register(FakeProtocol)
		with self.assertRaises(TypeError):
			# Handler instance required, not class.
			self.manager.unregister(FakeProtocol)  # type: ignore[arg-type]
		with self.assertRaises(ValueError):
			# Calling Manager.unregister on an instance that was not registered.
			self.manager.unregister(MockProtocol(lambda *args: None, lambda *args: None, is_client=True))
		self.manager.register(MockProtocol)
		instance: ConnectionInterface = self.manager._handlers[-1]
		self.assertIsNot(self.manager._handlers[0]._receiver, instance._receiver)
		mock_on_connection_lost: Mock
		with patch.object(instance, "on_connection_lost") as mock_on_connection_lost:
			self.manager.unregister(instance)
			self.assertIs(self.manager._handlers[0]._receiver, instance._receiver)
			mock_on_connection_lost.assert_called_once()
