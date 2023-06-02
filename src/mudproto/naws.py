"""
Negotiate About Window Sys (NAWS).
"""


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
from typing import TYPE_CHECKING, Any

# Local Modules:
from .telnet import BaseTelnetProtocol, TelnetProtocol
from .telnet_constants import NAWS


logger: logging.Logger = logging.getLogger(__name__)


if TYPE_CHECKING:  # pragma: no cover
	Base = TelnetProtocol
else:  # pragma: no cover
	Base = BaseTelnetProtocol


class NAWSMixIn(Base):
	"""
	A NAWS mix in class for the Telnet protocol.
	"""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		"""
		Defines the constructor for the mixin.

		Args:
			*args: Positional arguments to be passed to the parent constructor.
			**kwargs: Key-word only arguments to be passed to the parent constructor.
		"""
		super().__init__(*args, **kwargs)
		self.subnegotiationMap[NAWS] = self.on_naws
		self._nawsDimensions: tuple[int, int] = (0, 0)  # Width, height.

	@property
	def nawsDimensions(self) -> tuple[int, int]:
		return self._nawsDimensions

	@nawsDimensions.setter
	def nawsDimensions(self, value: tuple[int, int]) -> None:
		if value[0] < 0 or value[1] < 0:
			raise ValueError("Width and height must not be less than 0.")
		self._nawsDimensions = value
		if self.isClient:
			# NAWS is negotiated with 16-bit words.
			width: bytes = int.to_bytes(value[0], length=2, byteorder="big", signed=False)
			height: bytes = int.to_bytes(value[1], length=2, byteorder="big", signed=False)
			payload: bytes = width + height
			logger.debug(f"Sending NAWS payload: {payload!r}.")
			self.requestNegotiation(NAWS, payload)

	def on_naws(self, data: bytes) -> None:
		"""
		Called when a NAWS subnegotiation is received.

		Args:
			data: The payload.
		"""
		if self.isClient:
			logger.warning("Received NAWS subnegotiation while running in client mode.")
		elif len(data) != 4:
			logger.warning(f"Invalid NAWS sequence: {data!r}.")
		else:
			# NAWS is negotiated with 16-bit words.
			width: int = int.from_bytes(data[:2], byteorder="big", signed=False)
			height: int = int.from_bytes(data[2:], byteorder="big", signed=False)
			logger.debug(f"Received window size from peer: width = {width}, height = {height}.")
			self.nawsDimensions = (width, height)

	def on_connectionMade(self) -> None:
		super().on_connectionMade()
		if self.isServer:
			logger.debug("We ask peer to enable NAWS.")
			self.do(NAWS)

	def on_enableLocal(self, option: bytes) -> bool:
		if self.isClient and option == NAWS:
			logger.debug("We enable NAWS.")
			return True
		return bool(super().on_enableLocal(option))  # pragma: no cover

	def on_disableLocal(self, option: bytes) -> None:
		if self.isClient and option == NAWS:
			logger.debug("We disable NAWS.")
			return None
		super().on_disableLocal(option)  # pragma: no cover

	def on_enableRemote(self, option: bytes) -> bool:
		if self.isServer and option == NAWS:
			logger.debug("Peer enables NAWS.")
			return True
		return bool(super().on_enableRemote(option))  # pragma: no cover

	def on_disableRemote(self, option: bytes) -> None:
		if self.isServer and option == NAWS:
			logger.debug("Peer disables NAWS.")
			return None
		super().on_disableRemote(option)  # pragma: no cover
