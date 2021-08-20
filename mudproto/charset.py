"""
Charset protocol.
"""


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
from typing import Any, Tuple

# Local Modules:
from .base import Protocol
from .telnet_constants import CHARSET, CHARSET_ACCEPTED, CHARSET_REJECTED, CHARSET_REQUEST


logger: logging.Logger = logging.getLogger(__name__)


class CharsetMixIn(Protocol):
	"""A charset mix in class for the Telnet protocol."""

	charsets: Tuple[bytes, ...] = (
		b"US-ASCII",
		b"ISO-8859-1",
		b"UTF-8",
	)
	"""Supported character sets."""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)  # type: ignore[misc]
		self.subnegotiationMap[CHARSET] = self.on_charset  # type: ignore[misc, attr-defined]
		self._charset: bytes = self.charsets[0]

	@property
	def charset(self) -> bytes:
		"""The character set to be used."""
		return self._charset

	@charset.setter
	def charset(self, value: bytes) -> None:
		value = value.upper()
		if value not in self.charsets:
			raise ValueError(f"'{value!r}' not in {self.charsets!r}")
		self._charset = value

	def negotiateCharset(self, name: bytes) -> None:
		"""
		Negotiates changing the character set.

		Args:
			name: The name of the character set to use.
		"""
		self._oldCharset = self.charset
		try:
			self.charset = name
		except ValueError:
			logger.warning(f"Invalid charset {name!r}: falling back to {self.charset!r}.")
			name = self.charset
		separator = b";"
		logger.debug(f"Tell peer we would like to use the {name!r} charset.")
		self.requestNegotiation(CHARSET, CHARSET_REQUEST + separator + name)  # type: ignore[attr-defined]

	def on_charset(self, data: bytes) -> None:
		"""
		Called when a charset subnegotiation is received.

		Args:
			data: The payload.
		"""
		status, response = data[:1], data[1:]
		if status == CHARSET_ACCEPTED:
			logger.debug(f"Peer responds: Charset {response!r} accepted.")
		elif status == CHARSET_REJECTED:
			logger.warning("Peer responds: Charset rejected.")
			if self.charset == self._oldCharset:
				logger.warning(f"Unable to fall back to {self._oldCharset!r}. Old and new charsets match.")
			else:
				logger.debug(f"Falling back to {self._oldCharset!r}.")
				self.charset = self._oldCharset
		else:
			logger.warning(f"Unknown charset negotiation response from peer: {data!r}")
			self.charset = self._oldCharset
			self.wont(CHARSET)  # type: ignore[attr-defined]
		del self._oldCharset

	def on_connectionMade(self) -> None:
		super().on_connectionMade()
		logger.debug("Request that peer let us handle charset.")
		self.will(CHARSET)  # type: ignore[attr-defined]

	def on_enableLocal(self, option: bytes) -> bool:
		if option == CHARSET:
			logger.debug("Charset negotiation enabled.")
			self.negotiateCharset(self.charset)
			return True
		return bool(super().on_enableLocal(option))  # type: ignore[misc] # pragma: no cover

	def on_disableLocal(self, option: bytes) -> None:
		if option == CHARSET:
			logger.debug("Charset negotiation disabled.")
			return None
		super().on_disableLocal(option)  # type: ignore[misc] # pragma: no cover
