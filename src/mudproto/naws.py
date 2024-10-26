"""Negotiate About Window Sys (NAWS)."""


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Union

# Third-party Modules:
from knickknacks.typedef import Self

# Local Modules:
from .telnet import TelnetInterface
from .telnet_constants import NAWS


UINT16_MAX: int = 0xFFFF


logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Dimensions:
	"""Represents the dimensions of a window."""

	width: int
	"""The window width."""
	height: int
	"""The window height."""

	def __post_init__(self) -> None:
		"""
		Performs additional processing after dataclass initialization.

		Raises:
			ValueError: Invalid width or height values were given.
		"""
		if not 0 <= self.width <= UINT16_MAX or not 0 <= self.height <= UINT16_MAX:
			raise ValueError(f"{self!r}: Values must be in range 0 - {UINT16_MAX}.")

	@classmethod
	def fromBytes(cls: type[Self], data: bytes) -> Self:
		"""
		Creates a new Dimensions instance from NAWS bytes.

		Args:
			data: The bytes with the encoded width and height values.

		Returns:
			A Dimensions instance using the new values.
		"""
		if len(data) != 4:
			raise ValueError(f"Invalid NAWS sequence: {data!r}.")
		# NAWS is negotiated with 16-bit words.
		width: int = int.from_bytes(data[:2], byteorder="big", signed=False)
		height: int = int.from_bytes(data[2:], byteorder="big", signed=False)
		return cls(width=width, height=height)

	def toBytes(self) -> bytes:
		"""
		Converts the width and height to NAWS bytes.

		Returns:
			The encoded width and height as bytes.
		"""
		# NAWS is negotiated with 16-bit words.
		width: bytes = int.to_bytes(self.width, length=2, byteorder="big", signed=False)
		height: bytes = int.to_bytes(self.height, length=2, byteorder="big", signed=False)
		return width + height


class NAWSMixIn(TelnetInterface):
	"""A NAWS mix in class for the Telnet protocol."""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		"""
		Defines the constructor for the mixin.

		Args:
			*args: Positional arguments to be passed to the parent constructor.
			**kwargs: Key-word only arguments to be passed to the parent constructor.
		"""
		super().__init__(*args, **kwargs)
		self.subnegotiationMap[NAWS] = self.on_naws
		self._nawsDimensions: Dimensions = Dimensions(width=0, height=0)

	@property
	def nawsDimensions(self) -> Dimensions:
		"""The window dimensions."""
		return self._nawsDimensions

	@nawsDimensions.setter
	def nawsDimensions(self, value: Union[Dimensions, Sequence[int]]) -> None:
		self._nawsDimensions = value if isinstance(value, Dimensions) else Dimensions(*value)
		if self.isClient:
			payload: bytes = self._nawsDimensions.toBytes()
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
			return
		try:
			dimensions: Dimensions = Dimensions.fromBytes(data)
			logger.debug(
				f"Received window size from peer: width = {dimensions.width}, height = {dimensions.height}."
			)
			self.nawsDimensions = dimensions
		except ValueError as e:
			logger.warning(repr(e))

	def on_connectionMade(self) -> None:  # NOQA: D102
		super().on_connectionMade()  # type: ignore[safe-super]
		if self.isServer:
			logger.debug("We ask peer to enable NAWS.")
			self.do(NAWS)

	def on_enableLocal(self, option: bytes) -> bool:  # NOQA: D102
		if self.isClient and option == NAWS:
			logger.debug("We enable NAWS.")
			return True
		return bool(super().on_enableLocal(option))  # pragma: no cover

	def on_disableLocal(self, option: bytes) -> None:  # NOQA: D102
		if self.isClient and option == NAWS:
			logger.debug("We disable NAWS.")
			return
		super().on_disableLocal(option)  # type: ignore[safe-super]  # pragma: no cover

	def on_enableRemote(self, option: bytes) -> bool:  # NOQA: D102
		if self.isServer and option == NAWS:
			logger.debug("Peer enables NAWS.")
			return True
		return bool(super().on_enableRemote(option))  # pragma: no cover

	def on_disableRemote(self, option: bytes) -> None:  # NOQA: D102
		if self.isServer and option == NAWS:
			logger.debug("Peer disables NAWS.")
			return
		super().on_disableRemote(option)  # type: ignore[safe-super]  # pragma: no cover
