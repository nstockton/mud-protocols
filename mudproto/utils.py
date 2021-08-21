# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
from typing import AnyStr, Generator, Sequence, Tuple, Union

# Local Modules:
from .telnet_constants import IAC, IAC_IAC


ESCAPE_XML_STR_ENTITIES: Tuple[Tuple[str, str], ...] = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"))
UNESCAPE_XML_STR_ENTITIES: Tuple[Tuple[str, str], ...] = tuple(
	(second, first) for first, second in ESCAPE_XML_STR_ENTITIES
)
ESCAPE_XML_BYTES_ENTITIES: Tuple[Tuple[bytes, bytes], ...] = tuple(
	(first.encode("us-ascii"), second.encode("us-ascii")) for first, second in ESCAPE_XML_STR_ENTITIES
)
UNESCAPE_XML_BYTES_ENTITIES: Tuple[Tuple[bytes, bytes], ...] = tuple(
	(second, first) for first, second in ESCAPE_XML_BYTES_ENTITIES
)


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


def multiReplace(
	data: AnyStr, replacements: Union[Sequence[Sequence[bytes]], Sequence[Sequence[str]]]
) -> AnyStr:
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
	return multiReplace(data, UNESCAPE_XML_BYTES_ENTITIES)
