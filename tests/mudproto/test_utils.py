# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
from typing import Tuple
from unittest import TestCase

# MUD Protocol Modules:
from mudproto import utils
from mudproto.telnet_constants import IAC


class TestUtils(TestCase):
	def test_iterBytes(self) -> None:
		sent: bytes = b"hello"
		expected: Tuple[bytes, ...] = (b"h", b"e", b"l", b"l", b"o")
		self.assertEqual(tuple(utils.iterBytes(sent)), expected)

	def test_escapeIAC(self) -> None:
		sent: bytes = b"hello" + IAC + b"world"
		expected: bytes = b"hello" + IAC + IAC + b"world"
		self.assertEqual(utils.escapeIAC(sent), expected)

	def test_multiReplace(self) -> None:
		replacements: Tuple[Tuple[str, str], ...] = (("ll", "yy"), ("h", "x"), ("o", "z"))
		text: str = "hello world"
		expectedOutput: str = "xeyyz wzrld"
		self.assertEqual(utils.multiReplace(text, replacements), expectedOutput)
		self.assertEqual(utils.multiReplace(text, ()), text)

	def test_escapeXMLString(self) -> None:
		originalString: str = "<one&two>three"
		expectedString: str = "&lt;one&amp;two&gt;three"
		self.assertEqual(utils.escapeXMLString(originalString), expectedString)

	def test_unescapeXMLBytes(self) -> None:
		originalBytes: bytes = b"&lt;one&amp;two&gt;three"
		expectedBytes: bytes = b"<one&two>three"
		self.assertEqual(utils.unescapeXMLBytes(originalBytes), expectedBytes)
