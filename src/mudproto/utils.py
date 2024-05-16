# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import codecs
import re
from collections.abc import Generator, Sequence
from contextlib import suppress
from typing import Union

# Local Modules:
from .telnet_constants import IAC, IAC_IAC
from .typedef import REGEX_BYTES_PATTERN, BytesOrStr


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
UNESCAPE_XML_NUMERIC_BYTES_REGEX: REGEX_BYTES_PATTERN = re.compile(rb"&#(?P<hex>x?)(?P<value>[0-9a-zA-Z]+);")
# Latin-1 replacement values taken from the MUME help page.
# https://mume.org/help/latin1
LATIN_ENCODING_REPLACEMENTS: dict[str, bytes] = {
	"\u00a0": b" ",
	"\u00a1": b"!",
	"\u00a2": b"c",
	"\u00a3": b"L",
	"\u00a4": b"$",
	"\u00a5": b"Y",
	"\u00a6": b"|",
	"\u00a7": b"P",
	"\u00a8": b'"',
	"\u00a9": b"C",
	"\u00aa": b"a",
	"\u00ab": b"<",
	"\u00ac": b",",
	"\u00ad": b"-",
	"\u00ae": b"R",
	"\u00af": b"-",
	"\u00b0": b"d",
	"\u00b1": b"+",
	"\u00b2": b"2",
	"\u00b3": b"3",
	"\u00b4": b"'",
	"\u00b5": b"u",
	"\u00b6": b"P",
	"\u00b7": b"*",
	"\u00b8": b",",
	"\u00b9": b"1",
	"\u00ba": b"o",
	"\u00bb": b">",
	"\u00bc": b"4",
	"\u00bd": b"2",
	"\u00be": b"3",
	"\u00bf": b"?",
	"\u00c0": b"A",
	"\u00c1": b"A",
	"\u00c2": b"A",
	"\u00c3": b"A",
	"\u00c4": b"A",
	"\u00c5": b"A",
	"\u00c6": b"A",
	"\u00c7": b"C",
	"\u00c8": b"E",
	"\u00c9": b"E",
	"\u00ca": b"E",
	"\u00cb": b"E",
	"\u00cc": b"I",
	"\u00cd": b"I",
	"\u00ce": b"I",
	"\u00cf": b"I",
	"\u00d0": b"D",
	"\u00d1": b"N",
	"\u00d2": b"O",
	"\u00d3": b"O",
	"\u00d4": b"O",
	"\u00d5": b"O",
	"\u00d6": b"O",
	"\u00d7": b"*",
	"\u00d8": b"O",
	"\u00d9": b"U",
	"\u00da": b"U",
	"\u00db": b"U",
	"\u00dc": b"U",
	"\u00dd": b"Y",
	"\u00de": b"T",
	"\u00df": b"s",
	"\u00e0": b"a",
	"\u00e1": b"a",
	"\u00e2": b"a",
	"\u00e3": b"a",
	"\u00e4": b"a",
	"\u00e5": b"a",
	"\u00e6": b"a",
	"\u00e7": b"c",
	"\u00e8": b"e",
	"\u00e9": b"e",
	"\u00ea": b"e",
	"\u00eb": b"e",
	"\u00ec": b"i",
	"\u00ed": b"i",
	"\u00ee": b"i",
	"\u00ef": b"i",
	"\u00f0": b"d",
	"\u00f1": b"n",
	"\u00f2": b"o",
	"\u00f3": b"o",
	"\u00f4": b"o",
	"\u00f5": b"o",
	"\u00f6": b"o",
	"\u00f7": b"/",
	"\u00f8": b"o",
	"\u00f9": b"u",
	"\u00fa": b"u",
	"\u00fb": b"u",
	"\u00fc": b"u",
	"\u00fd": b"y",
	"\u00fe": b"t",
	"\u00ff": b"y",
}
LATIN_DECODING_REPLACEMENTS: dict[int, str] = {
	ord(k): str(v, "us-ascii") for k, v in LATIN_ENCODING_REPLACEMENTS.items()
}


def latin2ascii(error: UnicodeError) -> tuple[Union[bytes, str], int]:
	if isinstance(error, UnicodeEncodeError):
		# Return value can be bytes or a string.
		return LATIN_ENCODING_REPLACEMENTS.get(error.object[error.start], b"?"), error.start + 1
	elif isinstance(error, UnicodeDecodeError):
		# Return value must be a string.
		return LATIN_DECODING_REPLACEMENTS.get(error.object[error.start], "?"), error.start + 1
	else:  # Probably UnicodeTranslateError.
		raise NotImplementedError("How'd you manage this?") from error


codecs.register_error("latin2ascii", latin2ascii)


def decodeBytes(data: bytes) -> str:
	"""
	Decodes bytes into a string.

	If data contains Latin-1 characters, they will be replaced with ASCII equivalents.

	Args:
		data: The data to be decoded.

	Returns:
		The decoded string.
	"""
	# Try to decode ASCII first, for speed.
	with suppress(UnicodeDecodeError):
		return str(data, "us-ascii")
	# Translate non-ASCII characters to their ASCII equivalents.
	try:
		# If UTF-8, re-encode the data before decoding because of multi-byte code points.
		return data.decode("utf-8").encode("us-ascii", "latin2ascii").decode("us-ascii")
	except UnicodeDecodeError:
		# Assume data is Latin-1.
		return str(data, "us-ascii", "latin2ascii")


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
	data: BytesOrStr, replacements: Union[Sequence[Sequence[bytes]], Sequence[Sequence[str]]]
) -> BytesOrStr:
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
