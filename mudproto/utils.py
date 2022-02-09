# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import re
from collections.abc import Generator, Sequence
from typing import AnyStr

# Local Modules:
from .telnet_constants import IAC, IAC_IAC


ESCAPE_XML_STR_ENTITIES: tuple[tuple[str, str], ...] = (
	("&", "&amp;"),  # & must always be first when escaping.
	("<", "&lt;"),
	(">", "&gt;"),
)
UNESCAPE_XML_STR_ENTITIES: tuple[tuple[str, str], ...] = tuple(
	reversed(  # &amp; must always be last when unescaping.
		tuple((second, first) for first, second in ESCAPE_XML_STR_ENTITIES)
	)
)
ESCAPE_XML_BYTES_ENTITIES: tuple[tuple[bytes, bytes], ...] = tuple(
	(bytes(first, "us-ascii"), bytes(second, "us-ascii")) for first, second in ESCAPE_XML_STR_ENTITIES
)
UNESCAPE_XML_BYTES_ENTITIES: tuple[tuple[bytes, bytes], ...] = tuple(
	(bytes(first, "us-ascii"), bytes(second, "us-ascii")) for first, second in UNESCAPE_XML_STR_ENTITIES
)
UNESCAPE_XML_NUMERIC_BYTES_REGEX: re.Pattern[bytes] = re.compile(rb"&#(?P<hex>x?)(?P<value>[0-9a-zA-Z]+);")


def iterBytes(data: bytes) -> Generator[bytes, None, None]:
	"""
	A generator which yields each byte of a bytes-like object.

	Args:
		data: The data to process.

	Yields:
		Each byte of data as a bytes object.
	"""
	for i in range(len(data)):
		yield data[i : i + 1]


def escapeIAC(data: bytes) -> bytes:
	"""
	Escapes IAC bytes of a bytes-like object.

	Args:
		data: The data to be escaped.

	Returns:
		The data with IAC bytes escaped.
	"""
	return data.replace(IAC, IAC_IAC)


def multiReplace(data: AnyStr, replacements: Sequence[Sequence[bytes]] | Sequence[Sequence[str]]) -> AnyStr:
	"""
	Performs multiple replacement operations on a string or bytes-like object.

	Args:
		data: The text to perform the replacements on.
		replacements: A sequence of tuples, each containing the text to match and the replacement.

	Returns:
		The text with all the replacements applied.
	"""
	for item in replacements:
		data = data.replace(*item)
	return data


def escapeXMLString(text: str) -> str:
	"""
	Escapes XML entities in a string.

	Args:
		text: The string to escape.

	Returns:
		A copy of the string with XML entities escaped.
	"""
	return multiReplace(text, ESCAPE_XML_STR_ENTITIES)


def unescapeXMLBytes(data: bytes) -> bytes:
	"""
	Unescapes XML entities in a bytes-like object.

	Args:
		data: The data to unescape.

	Returns:
		A copy of the data with XML entities unescaped.
	"""

	def referenceToBytes(match: re.Match[bytes]) -> bytes:
		isHex: bytes = match.group("hex")
		value: bytes = match.group("value")
		return bytes((int(value, 16 if isHex else 10),))

	return multiReplace(
		UNESCAPE_XML_NUMERIC_BYTES_REGEX.sub(referenceToBytes, data), UNESCAPE_XML_BYTES_ENTITIES
	)
