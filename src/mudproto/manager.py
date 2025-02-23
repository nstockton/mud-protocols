# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Protocol manager."""

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import inspect
import logging
from types import TracebackType
from typing import Any, Optional

# Third-party Modules:
from knickknacks.typedef import Self

# Local Modules:
from .connection import ConnectionInterface
from .telnet import escape_iac
from .telnet_constants import CR, CR_LF, CR_NULL, GA, IAC, LF
from .typedef import ConnectionReceiverType, ConnectionWriterType


logger: logging.Logger = logging.getLogger(__name__)


class Manager:
	"""Handles registering and unregistering protocol classes to a connection."""

	def __init__(
		self,
		writer: ConnectionWriterType,
		receiver: ConnectionReceiverType,
		*,
		is_client: bool,
		prompt_terminator: Optional[bytes] = None,
	) -> None:
		"""
		Defines the constructor.

		Args:
			writer: The object where output is written.
			receiver: The object where input is received.
			is_client: True if acting as a client, False if acting as a server.
			prompt_terminator: The byte sequence used to terminate a prompt. If None, IAC + GA is used.
		"""
		self._writer: ConnectionWriterType = writer
		self._receiver: ConnectionReceiverType = receiver
		self._is_client: bool = is_client
		self.prompt_terminator: bytes
		if prompt_terminator is None:
			self.prompt_terminator = IAC + GA
		else:
			self.prompt_terminator = (
				prompt_terminator.replace(CR_LF, LF)
				.replace(CR_NULL, CR)
				.replace(CR, CR_NULL)
				.replace(LF, CR_LF)
			)
		self._read_buffer: bytearray = bytearray()
		self._write_buffer: bytearray = bytearray()
		self._handlers: list[ConnectionInterface] = []
		self._is_connected: bool = False

	@property
	def is_client(self) -> bool:
		"""True if acting as a client, False otherwise."""
		return self._is_client

	@property
	def is_server(self) -> bool:
		"""True if acting as a server, False otherwise."""
		return not self._is_client

	@property
	def is_connected(self) -> bool:
		"""Connection status."""
		return self._is_connected

	def __enter__(self) -> Self:
		self.connect()
		return self

	def __exit__(
		self,
		exc_type: Optional[type[BaseException]],
		exc_value: Optional[BaseException],
		exc_traceback: Optional[TracebackType],
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
		if not self.is_connected:
			self._is_connected = True
			if self._read_buffer:
				data = bytes(self._read_buffer)
				self._read_buffer.clear()
				self.parse(data)
			if self._write_buffer:
				data = bytes(self._write_buffer)
				self._write_buffer.clear()
				self.write(data)

	def disconnect(self) -> None:
		"""Signals that peer has disconnected."""
		if self.is_connected:
			while self._handlers:
				self.unregister(self._handlers[0])
			self._is_connected = False

	def parse(self, data: bytes) -> None:
		"""
		Parses data from peer.

		If not connected, data will be buffered until `connect` is called.

		Args:
			data: The data to be parsed.
		"""
		if not self.is_connected or not self._handlers:
			self._read_buffer.extend(data)
			return
		if self._read_buffer:
			data = bytes(self._read_buffer + data)
			self._read_buffer.clear()
		if data:
			self._handlers[0].on_data_received(data)

	def write(self, data: bytes, *, escape: bool = False, prompt: bool = False) -> None:
		"""
		Writes data to peer.

		Args:
			data: The bytes to be written.
			escape: If True, escapes line endings and IAC characters.
			prompt: If True, appends the prompt terminator to the data.
		"""
		if escape:
			data = escape_iac(data).replace(CR, CR_NULL).replace(LF, CR_LF)
		if prompt:
			data += self.prompt_terminator
		if not self.is_connected or not self._handlers:
			self._write_buffer.extend(data)
			return
		if self._write_buffer:
			data = bytes(self._write_buffer + data)
			self._write_buffer.clear()
		if data:
			self._writer(data)

	def register(self, handler: type[ConnectionInterface], **kwargs: Any) -> None:
		"""
		Registers a protocol handler.

		Args:
			handler: The handler to be registered.
			**kwargs: Key word arguments to be passed to the handler's constructer.

		Raises:
			TypeError: Handler is an instance instead of a class.
			ValueError: Handler was already registered.
		"""
		if not inspect.isclass(handler):
			raise TypeError("Class required, not instance.")
		if any(i for i in self._handlers if isinstance(i, handler)):
			raise ValueError("Already registered.")
		instance: ConnectionInterface = handler(
			self.write, self._receiver, is_client=self._is_client, **kwargs
		)
		if self._handlers:
			self._handlers[-1]._receiver = instance.on_data_received  # NOQA: SLF001
		self._handlers.append(instance)
		instance.on_connection_made()

	def unregister(self, instance: ConnectionInterface) -> None:
		"""
		Unregisters a protocol handler.

		Args:
			instance: The handler instance to be unregistered.

		Raises:
			TypeError: Handler is a class instead of an instance.
			ValueError: Handler was never registered.
		"""
		if inspect.isclass(instance):
			raise TypeError("Instance required, not class.")
		if instance not in self._handlers:
			raise ValueError("Instance wasn't registered.")
		index = self._handlers.index(instance)
		self._handlers.remove(instance)
		if self._handlers and index > 0:
			self._handlers[index - 1]._receiver = instance._receiver  # NOQA: SLF001
		instance.on_connection_lost()
