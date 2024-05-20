"""
Charset protocol.
"""


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import codecs
import logging
from contextlib import suppress
from typing import Any

# Local Modules:
from .telnet import TelnetInterface
from .telnet_constants import CHARSET, CHARSET_ACCEPTED, CHARSET_REJECTED, CHARSET_REQUEST


logger: logging.Logger = logging.getLogger(__name__)


class CharsetMixIn(TelnetInterface):
	"""A charset mix in class for the Telnet protocol."""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self.subnegotiationMap[CHARSET] = self.on_charset
		self._charsets: tuple[bytes, ...] = (b"US-ASCII",)
		self._charset: bytes = self._charsets[0]

	@property
	def charset(self) -> bytes:
		"""The character set to be used."""
		return self._charset

	@charset.setter
	def charset(self, value: bytes) -> None:
		value = value.upper()
		if value not in self._charsets:
			raise ValueError(f"'{value!r}' not in {self._charsets!r}")
		self._charset = value

	def negotiateCharset(self, name: bytes) -> None:
		"""
		Negotiates changing the character set.

		Args:
			name: The name of the character set to use.
		"""
		separator: bytes = b";"
		try:
			self.charset = name
		except ValueError:
			logger.warning(f"Invalid charset {name!r}: falling back to {self.charset!r}.")
		else:
			logger.debug(f"Tell peer we would like to use the {name!r} charset.")
			self.requestNegotiation(CHARSET, CHARSET_REQUEST + separator + name)

	def parseSupportedCharsets(self, response: bytes) -> tuple[bytes, ...]:
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
			self._charsets = self.parseSupportedCharsets(response)
			logger.debug(f"Peer responds: Supported charsets: {self._charsets!r}.")
			self.negotiateCharset(self.charset)
		elif status == CHARSET_ACCEPTED:
			logger.debug(f"Peer responds: Charset {response!r} accepted.")
			self.charset = response
		elif status == CHARSET_REJECTED:
			logger.warning("Peer responds: Charset rejected.")
		else:
			logger.warning(f"Unknown charset negotiation response from peer: {data!r}")
			self.wont(CHARSET)

	def on_enableLocal(self, option: bytes) -> bool:
		if option == CHARSET:
			logger.debug("Charset negotiation enabled.")
			return True
		return bool(super().on_enableLocal(option))  # pragma: no cover

	def on_disableLocal(self, option: bytes) -> None:
		if option == CHARSET:
			logger.debug("Charset negotiation disabled.")
			return None
		super().on_disableLocal(option)  # pragma: no cover
