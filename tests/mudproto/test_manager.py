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
	def on_connectionMade(self) -> None:
		return super().on_connectionMade()

	def on_connectionLost(self) -> None:
		return super().on_connectionLost()

	def on_dataReceived(self, data: bytes) -> None:
		return super().on_dataReceived(data)


class MockProtocol(ConnectionInterface):
	on_connectionMade: Mock = Mock()
	on_connectionLost: Mock = Mock()
	on_dataReceived: Mock = Mock()

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self._receiver: Mock = Mock()


class TestManager(TestCase):
	def setUp(self) -> None:
		self.gameReceives: bytearray = bytearray()
		self.playerReceives: bytearray = bytearray()
		self.manager: Manager = Manager(
			self.gameReceives.extend, self.playerReceives.extend, isClient=True, promptTerminator=CR_LF
		)

	def tearDown(self) -> None:
		self.manager.disconnect()
		del self.manager
		self.gameReceives.clear()
		self.playerReceives.clear()

	def parse(self, data: bytes) -> tuple[bytes, bytes]:
		self.manager.parse(data)
		playerReceives = bytes(self.playerReceives)
		self.playerReceives.clear()
		gameReceives = bytes(self.gameReceives)
		self.gameReceives.clear()
		return playerReceives, gameReceives

	def testManagerInit(self) -> None:
		manager: Manager = Manager(
			lambda *args: None, lambda *args: None, isClient=True, promptTerminator=None
		)
		self.assertEqual(manager.promptTerminator, IAC + GA)
		del manager

	def testManagerIsClient(self) -> None:
		self.assertEqual(self.manager.isClient, self.manager._isClient)

	def testManagerIsServer(self) -> None:
		self.assertEqual(self.manager.isServer, not self.manager._isClient)

	@patch("mudproto.manager.Manager.disconnect")
	@patch("mudproto.manager.Manager.connect")
	def testManagerAsContextManager(self, mockConnect: Mock, mockDisconnect: Mock) -> None:
		with self.manager:
			mockConnect.assert_called_once()
		mockDisconnect.assert_called_once()

	@patch("mudproto.manager.Manager.disconnect")
	def testManagerClose(self, mockDisconnect: Mock) -> None:
		self.manager.close()
		mockDisconnect.assert_called_once()

	def testManagerParse(self) -> None:
		data: bytes = b"Hello World!"
		bufferedData: bytes = b"Some buffered data."
		# Make sure that any data passed to Manager.parse before calling Manager.connect() gets buffered.
		self.assertEqual(self.parse(bufferedData), (b"", b""))
		self.manager.connect()
		# Make sure that any data passed to Manager.parse before registering a protocol gets buffered.
		self.assertEqual(self.parse(bufferedData), (b"", b""))
		self.manager.register(FakeProtocol)
		self.assertEqual(self.parse(data), (bufferedData + bufferedData + data, b""))
		# If the protocol is registered and connected, calling parse with some data should not buffer.
		self.assertEqual(self.parse(data), (data, b""))

	def testManagerWrite(self) -> None:
		data: bytes = b"Hello World!"
		bufferedData: bytes = b"Some buffered data."
		# Make sure that any data passed to Manager.write before calling Manager.connect() gets buffered.
		self.manager.write(bufferedData)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.manager.connect()
		# Make sure that any data passed to Manager.write before registering a protocol gets buffered.
		self.manager.write(bufferedData)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
		self.manager.register(FakeProtocol)
		self.manager.write(data)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", bufferedData + bufferedData + data))
		self.gameReceives.clear()
		# Make sure IAC bytes are escaped and line endings are normalized if the escape argument is True.
		self.manager.write(data + IAC + LF + CR, escape=True)
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", data + IAC + IAC + CR_LF + CR_NULL))
		self.gameReceives.clear()
		# Make sure prompt terminator is appended to bytes if the prompt argument is True.
		self.manager.write(data, prompt=True)
		self.assertEqual(
			(self.playerReceives, self.gameReceives), (b"", data + self.manager.promptTerminator)
		)

	def testManagerRegister(self) -> None:
		with self.assertRaises(ValueError):
			# Handler class required, not instance.
			self.manager.register(
				FakeProtocol(lambda *args: None, lambda *args: None, isClient=True)  # type: ignore[arg-type]
			)
		self.manager.register(FakeProtocol)
		with self.assertRaises(ValueError):
			self.manager.register(FakeProtocol)
		self.assertIsNot(self.manager._handlers[0]._receiver, MockProtocol.on_dataReceived)
		self.manager.register(MockProtocol)
		self.assertIs(self.manager._handlers[0]._receiver, self.manager._handlers[1].on_dataReceived)
		mockOn_connectionMade: Mock = MockProtocol.on_connectionMade
		mockOn_connectionMade.assert_called_once()

	def testManagerUnregister(self) -> None:
		self.manager.register(FakeProtocol)
		with self.assertRaises(ValueError):
			# Handler instance required, not class.
			self.manager.unregister(FakeProtocol)  # type: ignore[arg-type]
		with self.assertRaises(ValueError):
			# Calling Manager.unregister on an instance that was not registered.
			self.manager.unregister(MockProtocol(lambda *args: None, lambda *args: None, isClient=True))
		self.manager.register(MockProtocol)
		instance: ConnectionInterface = self.manager._handlers[-1]
		self.assertIsNot(self.manager._handlers[0]._receiver, instance._receiver)
		mockOn_connectionLost: Mock
		with patch.object(instance, "on_connectionLost") as mockOn_connectionLost:
			self.manager.unregister(instance)
			self.assertIs(self.manager._handlers[0]._receiver, instance._receiver)
			mockOn_connectionLost.assert_called_once()
