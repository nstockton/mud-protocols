# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
from unittest import TestCase

# MUD Protocol Modules:
from mudproto import utils
from mudproto.telnet_constants import IAC


class TestUtils(TestCase):
	def test_latin2ascii(self) -> None:
		with self.assertRaises(NotImplementedError):
			utils.latin2ascii(UnicodeError("junk"))

	def test_decodeBytes(self) -> None:
		asciiChars: str = "".join(chr(i) for i in range(128))
		latinChars: str = "".join(chr(i) for i in range(128, 256))
		latinReplacements: str = "".join(
			utils.LATIN_DECODING_REPLACEMENTS.get(ord(char), "?") for char in latinChars
		)
		self.assertEqual(utils.decodeBytes(bytes(asciiChars, "us-ascii")), asciiChars)
		self.assertEqual(utils.decodeBytes(bytes(latinChars, "latin-1")), latinReplacements)
		self.assertEqual(utils.decodeBytes(bytes(latinChars, "utf-8")), latinReplacements)

	def test_iterBytes(self) -> None:
		sent: bytes = b"hello"
		expected: tuple[bytes, ...] = (b"h", b"e", b"l", b"l", b"o")
		self.assertEqual(tuple(utils.iterBytes(sent)), expected)

	def test_escapeIAC(self) -> None:
		sent: bytes = b"hello" + IAC + b"world"
		expected: bytes = b"hello" + IAC + IAC + b"world"
		self.assertEqual(utils.escapeIAC(sent), expected)

	def test_multiReplace(self) -> None:
		replacements: tuple[tuple[str, str], ...] = (("ll", "yy"), ("h", "x"), ("o", "z"))
		text: str = "hello world"
		expectedOutput: str = "xeyyz wzrld"
		self.assertEqual(utils.multiReplace(text, replacements), expectedOutput)
		self.assertEqual(utils.multiReplace(text, ()), text)

	def test_escapeXMLString(self) -> None:
		originalString: str = "<one&two'\">three"
		expectedString: str = "&lt;one&amp;two'\"&gt;three"
		self.assertEqual(utils.escapeXMLString(originalString), expectedString)

	def test_unescapeXMLBytes(self) -> None:
		originalBytes: bytes = b"&lt;'\"one&amp;gt;two&gt;three&#35;four&#x5F;&#x5f;five&amp;#35;six"
		expectedBytes: bytes = b"<'\"one&gt;two>three#four__five&#35;six"
		self.assertEqual(utils.unescapeXMLBytes(originalBytes), expectedBytes)
