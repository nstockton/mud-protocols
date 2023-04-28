# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
from typing import Any
from unittest import TestCase
from unittest.mock import patch
from zlib import DEFLATED, MAX_WBITS, Z_DEFAULT_COMPRESSION, Z_FINISH, Z_SYNC_FLUSH, compressobj

# MUD Protocol Modules:
from mudproto.mccp import MCCPMixIn
from mudproto.mccp import logger as mccpLogger
from mudproto.telnet import TelnetProtocol
from mudproto.telnet_constants import (
	COMMAND_BYTES,
	CR,
	CR_LF,
	ECHO,
	IAC,
	IAC_IAC,
	MCCP1,
	MCCP2,
	NEGOTIATION_BYTES,
	NULL,
	SB,
	SE,
	WILL,
)


class Telnet(MCCPMixIn, TelnetProtocol):
	"""
	Telnet protocol with MCCP support.
	"""


class TestMCCPMixIn(TestCase):
	def setUp(self) -> None:
		self.gameReceives: bytearray = bytearray()
		self.playerReceives: bytearray = bytearray()
		self.telnet: Telnet = Telnet(self.gameReceives.extend, self.playerReceives.extend, isClient=True)

	def tearDown(self) -> None:
		del self.telnet
		self.gameReceives.clear()
		self.playerReceives.clear()

	def parse(self, data: bytes) -> tuple[bytes, bytes]:
		# We need to bypass TelnetProtocol.on_dataReceived when testing.
		with patch.object(
			TelnetProtocol, "on_dataReceived", side_effect=lambda d: self.playerReceives.extend(d)
		):
			self.telnet.on_dataReceived(data)
		playerReceives: bytes = bytes(self.playerReceives)
		self.playerReceives.clear()
		gameReceives: bytes = bytes(self.gameReceives)
		self.gameReceives.clear()
		self.telnet._compressedInputBuffer.clear()
		return playerReceives, gameReceives

	def test_on_dataReceived(self) -> None:
		# Insure uncompressed data is passed on.
		data: bytes = b"Hello World!"
		self.assertEqual(self.parse(data + CR_LF), (data + CR_LF, b""))
		# Note that the IAC is buffered while looking for MCCP negotiations.
		self.assertEqual(self.parse(data + IAC), (data, b""))
		self.assertEqual(self.parse(data + CR + IAC), (data + CR, b""))
		self.assertEqual(self.parse(data + CR + IAC_IAC), (data + CR + IAC_IAC, b""))
		# IAC command and negotiation sequences:
		self.assertEqual(self.parse(data + IAC_IAC), (data + IAC_IAC, b""))
		# IAC + SE outside of subnegotiation.
		self.assertEqual(self.parse(data + IAC + SE), (data + IAC + SE, b""))
		self.assertEqual(self.parse(data + IAC + SB), (data, b""))  # Buffered while looking for MCCP.
		for byte in COMMAND_BYTES:
			self.assertEqual(self.parse(data + IAC + byte), (data + IAC + byte, b""))
		for byte in NEGOTIATION_BYTES:
			self.assertEqual(self.parse(data + IAC + byte), (data + IAC + byte, b""))
			self.assertEqual(self.parse(data + IAC + byte + ECHO), (data + IAC + byte + ECHO, b""))
		self.assertEqual(self.parse(data + IAC + NULL), (data + IAC + NULL, b""))
		# Partial subnegotiation sequences:
		# Note that these are buffered.
		self.assertEqual(self.parse(data + IAC + SB + IAC), (data, b""))
		self.assertEqual(self.parse(data + IAC + SB + b"something"), (data, b""))
		# Complete subnegotiations:
		self.assertEqual(
			self.parse(data + IAC + SB + ECHO + b"something" + IAC + SE),
			(data + IAC + SB + ECHO + b"something" + IAC + SE, b""),
		)
		self.assertEqual(
			self.parse(data + IAC + SB + ECHO + b"something" + IAC_IAC + IAC + SE),
			(data + IAC + SB + ECHO + b"something" + IAC_IAC + IAC + SE, b""),
		)
		# Insure compression is enabled on our end when enabled by the server.
		self.assertFalse(self.telnet._isCompressed)
		with self.assertLogs(mccpLogger, "DEBUG"):
			self.assertEqual(self.parse(data + IAC + SB + MCCP1 + WILL + SE), (data, b""))
		self.assertTrue(self.telnet._isCompressed)
		self.telnet._isCompressed = False
		with self.assertLogs(mccpLogger, "DEBUG"):
			self.assertEqual(self.parse(data + IAC + SB + MCCP2 + IAC + SE), (data, b""))
		self.assertTrue(self.telnet._isCompressed)
		# Insure we can actually decompress the data.
		compressor: Any = compressobj(Z_DEFAULT_COMPRESSION, DEFLATED, MAX_WBITS)
		compressed: bytes = compressor.compress(data)
		self.assertEqual(self.parse(compressed + compressor.flush(Z_SYNC_FLUSH)), (data, b""))
		# Insure that decompression is disabled when Z_FINISH is sent by the server.
		with self.assertLogs(mccpLogger, "DEBUG"):
			self.assertEqual(self.parse(compressor.flush(Z_FINISH) + data), (data, b""))
		self.assertFalse(self.telnet._isCompressed)

	def test_on_enableRemote(self) -> None:
		self.assertFalse(self.telnet._usingMCCp1)
		self.assertFalse(self.telnet._usingMCCp2)
		# MCCP1 is only allowed if MCCP2 wasn't previously negotiated.
		with self.assertLogs(mccpLogger, "DEBUG"):
			self.assertTrue(self.telnet.on_enableRemote(MCCP1))
			self.assertFalse(self.telnet.on_enableRemote(MCCP2))
		self.telnet._usingMCCp1 = False
		# MCCP2 is only allowed if MCCP1 wasn't previously negotiated.
		with self.assertLogs(mccpLogger, "DEBUG"):
			self.assertTrue(self.telnet.on_enableRemote(MCCP2))
			self.assertFalse(self.telnet.on_enableRemote(MCCP1))
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))

	def test_on_disableRemote(self) -> None:
		with self.assertLogs(mccpLogger, "DEBUG"):
			self.telnet.on_disableRemote(MCCP1)  # Should not throw an exception.
			self.telnet.on_disableRemote(MCCP2)  # Should not throw an exception.
		self.assertEqual((self.playerReceives, self.gameReceives), (b"", b""))
