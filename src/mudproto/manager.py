# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import inspect
import logging
from collections.abc import Callable
from types import TracebackType
from typing import Any, Optional

# Local Modules:
from .base import Protocol
from .telnet_constants import CR, CR_LF, CR_NULL, GA, IAC, LF
from .utils import escapeIAC


logger: logging.Logger = logging.getLogger(__name__)


class Manager(object):
	def __init__(
		self,
		writer: Callable[[bytes], None],
		receiver: Callable[[bytes], None],
		*,
		promptTerminator: Optional[bytes] = None,
	) -> None:
		self._writer: Callable[[bytes], None] = writer
		self._receiver: Callable[[bytes], None] = receiver
		self.promptTerminator: bytes
		if promptTerminator is None:
			self.promptTerminator = IAC + GA
		else:
			self.promptTerminator = (
				promptTerminator.replace(CR_LF, LF)
				.replace(CR_NULL, CR)
				.replace(CR, CR_NULL)
				.replace(LF, CR_LF)
			)
		self._readBuffer: list[bytes] = []
		self._writeBuffer: list[bytes] = []
		self._handlers: list[Protocol] = []
		self._isConnected: bool = False

	@property
	def isConnected(self) -> bool:
		"""Connection status."""
		return self._isConnected

	def __enter__(self) -> Manager:
		self.connect()
		return self

	def __exit__(
		self,
		excType: Optional[type[BaseException]],
		excValue: Optional[BaseException],
		excTraceback: Optional[TracebackType],
	) -> None:
		self.disconnect()

	def __del__(self) -> None:
		self.disconnect()

	def close(self) -> None:
		"""Calls `disconnect`."""
		self.disconnect()

	def connect(self) -> None:
		"""
		Signals that peer is connected.

		If data was buffered while not connected, `parse` will be called with the data.
		"""
		data: bytes
		if not self.isConnected:
			self._isConnected = True
			if self._readBuffer:
				data = b"".join(self._readBuffer)
				self._readBuffer.clear()
				self.parse(data)
			if self._writeBuffer:
				data = b"".join(self._writeBuffer)
				self._writeBuffer.clear()
				self.write(data)

	def disconnect(self) -> None:
		"""Signals that peer has disconnected."""
		if self.isConnected:
			while self._handlers:
				self.unregister(self._handlers[0])
			self._isConnected = False

	def parse(self, data: bytes) -> None:
		"""
		Parses data from peer.

		If not connected, data will be buffered until `connect` is called.

		Args:
			data: The data to be parsed.
		"""
		if not self.isConnected or not self._handlers:
			self._readBuffer.append(data)
		elif self._readBuffer:
			data = b"".join(self._readBuffer) + data
			self._readBuffer.clear()
			self._handlers[0].on_dataReceived(data)
		elif data:
			self._handlers[0].on_dataReceived(data)

	def write(self, data: bytes, *, escape: bool = False, prompt: bool = False) -> None:
		"""
		Writes data to peer.

		Args:
			data: The bytes to be written.
			escape: If True, escapes line endings and IAC characters.
			prompt: If True, appends the prompt terminator to the data.
		"""
		if escape:
			data = escapeIAC(data).replace(CR, CR_NULL).replace(LF, CR_LF)
		if prompt:
			data += self.promptTerminator
		if not self.isConnected or not self._handlers:
			self._writeBuffer.append(data)
		elif self._writeBuffer:
			data = b"".join(self._writeBuffer) + data
			self._writeBuffer.clear()
			self._writer(data)
		elif data:
			self._writer(data)

	def register(self, handler: type[Protocol], **kwargs: Any) -> None:
		"""
		Registers a protocol handler.

		Args:
			handler: The handler to be registered.
			**kwargs: Key word arguments to be passed to the handler's constructer.
		"""
		if not inspect.isclass(handler):
			raise ValueError("Class required, not instance.")
		for i in self._handlers:
			if isinstance(i, handler):  # type: ignore[misc]
				raise ValueError("Already registered.")
		instance: Protocol = handler(self.write, self._receiver, **kwargs)  # type: ignore[misc]
		if self._handlers:
			self._handlers[-1]._receiver = instance.on_dataReceived
		self._handlers.append(instance)
		instance.on_connectionMade()

	def unregister(self, instance: Protocol) -> None:
		"""
		Unregisters a protocol handler.

		Args:
			instance: The handler instance to be unregistered.
		"""
		if inspect.isclass(instance):
			raise ValueError("Instance required, not class.")
		elif instance not in self._handlers:
			raise ValueError("Instance wasn't registered.")
		index = self._handlers.index(instance)
		self._handlers.remove(instance)
		if self._handlers and index > 0:
			self._handlers[index - 1]._receiver = instance._receiver
		instance.on_connectionLost()
