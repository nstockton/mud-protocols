# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""MUD connection."""

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
from abc import ABC, abstractmethod
from typing import Any

# Local Modules:
from .typedef import ConnectionReceiverType, ConnectionWriterType


logger: logging.Logger = logging.getLogger(__name__)


class ConnectionInterface(ABC):
	"""Input and output to a MUD client or server."""

	def __init__(
		self,
		writer: ConnectionWriterType,
		receiver: ConnectionReceiverType,
		*,
		is_client: bool,
		**kwargs: Any,
	) -> None:
		"""
		Defines the constructor.

		Args:
			writer: The object where output is written.
			receiver: The object where input is received.
			is_client: True if acting as a client, False if acting as a server.
			**kwargs: Key-word only arguments (currently unused).
		"""
		self._writer: ConnectionWriterType = writer
		self._receiver: ConnectionReceiverType = receiver
		self._is_client: bool = is_client

	@property
	def is_client(self) -> bool:
		"""True if acting as a client, False otherwise."""
		return self._is_client

	@property
	def is_server(self) -> bool:
		"""True if acting as a server, False otherwise."""
		return not self._is_client

	def write(self, data: bytes) -> None:
		"""
		Writes data to peer.

		Args:
			data: The bytes to be written.
		"""
		self._writer(data)

	@abstractmethod
	def on_connection_made(self) -> None:
		"""Called by `connect` when a connection to peer has been established."""

	@abstractmethod
	def on_connection_lost(self) -> None:
		"""Called by `disconnect` when a connection to peer has been lost."""

	@abstractmethod
	def on_data_received(self, data: bytes) -> None:
		"""
		Called by `parse` when data is received.

		Args:
			data: The received data.
		"""
		self._receiver(data)
