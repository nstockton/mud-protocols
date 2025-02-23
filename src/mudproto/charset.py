# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Charset protocol."""

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import codecs
import logging
from contextlib import suppress
from typing import Any, Union

# Local Modules:
from .telnet import TelnetInterface
from .telnet_constants import CHARSET, CHARSET_ACCEPTED, CHARSET_REJECTED, CHARSET_REQUEST


logger: logging.Logger = logging.getLogger(__name__)


class CharsetMixIn(TelnetInterface):
	"""A charset mix in class for the Telnet protocol."""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		"""
		Defines the constructor.

		Args:
			*args: Positional arguments to be passed to the parent constructor.
			**kwargs: Key-word only arguments to be passed to the parent constructor.
		"""
		super().__init__(*args, **kwargs)
		self.subnegotiation_map[CHARSET] = self.on_charset
		self._charsets: tuple[bytes, ...] = (b"US-ASCII",)
		self._charset: bytes = self._charsets[0]

	@property
	def charset(self) -> str:
		"""The currently used character set."""
		return str(self._charset, "us-ascii")

	def negotiate_charset(self, name: Union[bytes, str]) -> None:
		"""
		Negotiates changing the character set.

		Args:
			name: The name of the character set to use.
		"""
		separator: bytes = b";"
		if not isinstance(name, str):
			name = str(name, "us-ascii")
		try:
			target = codecs.lookup(name).name
		except LookupError:
			logger.warning(f"'{name}' not a valid codec")
			return
		for item in self._charsets:
			if target == codecs.lookup(str(item, "us-ascii")).name:
				logger.debug(f"Tell peer we would like to use the {item!r} charset.")
				self.request_negotiation(CHARSET, CHARSET_REQUEST + separator + item)
				return
		logger.warning(f"Could not find any charsets which target '{target}'")

	@staticmethod
	def parse_supported_charsets(response: bytes) -> tuple[bytes, ...]:
		"""
		Parses the supported character sets from peer.

		Args:
			response: The response from peer, containing the supported character sets.

		Returns:
			The character sets supported by peer, with duplicate aliases removed.
		"""
		charsets: list[bytes] = []
		names: set[str] = set()
		separator, response = response[:1], response[1:]
		for item in response.split(separator):
			with suppress(LookupError):
				name = codecs.lookup(str(item, "us-ascii")).name
				if name not in names:
					charsets.append(item)
					names.add(name)
		return tuple(charsets)

	def on_charset(self, data: bytes) -> None:
		"""
		Called when a charset subnegotiation is received.

		Args:
			data: The payload.
		"""
		status, response = data[:1], data[1:]
		if status == CHARSET_REQUEST:
			self._charsets = self.parse_supported_charsets(response)
			logger.debug(f"Peer responds: Supported charsets: {self._charsets!r}.")
			self.negotiate_charset(self._charset)
		elif status == CHARSET_ACCEPTED:
			logger.debug(f"Peer responds: Charset {response!r} accepted.")
			self._charset = response
		elif status == CHARSET_REJECTED:
			logger.warning("Peer responds: Charset rejected.")
		else:
			logger.warning(f"Unknown charset negotiation response from peer: {data!r}")
			self.wont(CHARSET)

	def on_enable_local(self, option: bytes) -> bool:  # NOQA: D102
		if option == CHARSET:
			logger.debug("Charset negotiation enabled.")
			return True
		return bool(super().on_enable_local(option))  # pragma: no cover

	def on_disable_local(self, option: bytes) -> None:  # NOQA: D102
		if option == CHARSET:
			logger.debug("Charset negotiation disabled.")
			return
		super().on_disable_local(option)  # type: ignore[safe-super]  # pragma: no cover
