# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
from abc import abstractmethod
from typing import Any
from typing import Protocol as TypeProtocol

# Local Modules:
from .typedef import CONNECTION_RECEIVER_TYPE, CONNECTION_WRITER_TYPE


logger: logging.Logger = logging.getLogger(__name__)


class BaseConnectionInterface(TypeProtocol):
	@property
	@abstractmethod
	def isClient(self) -> bool:
		"""True if acting as a client, False otherwise."""

	@property
	@abstractmethod
	def isServer(self) -> bool:
		"""True if acting as a server, False otherwise."""

	@abstractmethod
	def write(self, data: bytes) -> None:
		"""
		Writes data to peer.

		Args:
			data: The bytes to be written.
		"""

	@abstractmethod
	def on_connectionMade(self) -> None:
		"""Called by `connect` when a connection to peer has been established."""

	@abstractmethod
	def on_connectionLost(self) -> None:
		"""Called by `disconnect` when a connection to peer has been lost."""

	@abstractmethod
	def on_dataReceived(self, data: bytes) -> None:
		"""
		Called by `parse` when data is received.

		Args:
			data: The received data.
		"""


class BaseConnection(BaseConnectionInterface):
	def __init__(
		self,
		writer: CONNECTION_WRITER_TYPE,
		receiver: CONNECTION_RECEIVER_TYPE,
		*,
		isClient: bool,
		**kwargs: Any,
	) -> None:
		self._writer: CONNECTION_WRITER_TYPE = writer
		self._receiver: CONNECTION_RECEIVER_TYPE = receiver
		self._isClient: bool = isClient

	@property
	def isClient(self) -> bool:
		return self._isClient

	@property
	def isServer(self) -> bool:
		return not self._isClient

	def write(self, data: bytes) -> None:
		self._writer(data)

	def on_dataReceived(self, data: bytes) -> None:
		self._receiver(data)
