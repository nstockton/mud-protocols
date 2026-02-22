# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Future Modules:
from __future__ import annotations

# Built-in Modules:
from unittest import TestCase
from unittest.mock import Mock, patch

# MUD Protocol Modules:
from mudproto.telnet import OptionState, TelnetProtocol, TelnetState, escape_iac
from mudproto.telnet_constants import (
	COMMAND_BYTES,
	CR,
	CR_LF,
	CR_NULL,
	DO,
	DONT,
	ECHO,
	GA,
	IAC,
	LF,
	NEGOTIATION_BYTES,
	NULL,
	SB,
	SE,
	WILL,
	WONT,
)


class TestTelnet(TestCase):
	def test_escape_iac(self) -> None:
		sent: bytes = b"hello" + IAC + b"world"
		expected: bytes = b"hello" + IAC + IAC + b"world"
		self.assertEqual(escape_iac(sent), expected)


class TestTelnetProtocol(TestCase):
	def setUp(self) -> None:
		self.game_receives: bytearray = bytearray()
		self.player_receives: bytearray = bytearray()
		self.telnet: TelnetProtocol = TelnetProtocol(
			self.game_receives.extend, self.player_receives.extend, is_client=True
		)

	def tearDown(self) -> None:
		self.telnet.on_connection_lost()
		del self.telnet
		self.game_receives.clear()
		self.player_receives.clear()

	@staticmethod
	def new_mocked_option_state() -> Mock:
		state: Mock = Mock()
		state.us.enabled = False
		state.us.negotiating = False
		state.him.enabled = False
		state.him.negotiating = False
		return state

	def parse(self, data: bytes) -> tuple[bytes, bytes, TelnetState]:
		self.telnet.on_data_received(data)
		player_receives: bytes = bytes(self.player_receives)
		self.player_receives.clear()
		game_receives: bytes = bytes(self.game_receives)
		self.game_receives.clear()
		state: TelnetState = self.telnet.state
		self.telnet.state = TelnetState.DATA
		return player_receives, game_receives, state

	def get_option_states(self) -> dict[bytes, OptionState]:
		return getattr(self.telnet, "_TelnetProtocol__option_states", {})

	@patch("mudproto.telnet.logger")
	def test_telnet_will(self, mock_logger: Mock) -> None:
		state: Mock = self.new_mocked_option_state()
		self.get_option_states()[ECHO] = state
		us_negotiating_warning: str = (
			f"We are offering to enable option {ECHO!r}, "
			+ "but the option is already being negotiated by us."
		)
		him_negotiating_warning: str = (
			f"We are offering to enable option {ECHO!r}, "
			+ "but the option is already being negotiated by peer."
		)
		state.us.negotiating = True
		self.telnet.will(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(us_negotiating_warning)
		mock_logger.reset_mock()
		state.us.negotiating = False
		state.him.negotiating = True
		self.telnet.will(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(him_negotiating_warning)
		mock_logger.reset_mock()
		state.him.negotiating = False
		state.us.enabled = True
		self.telnet.will(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(
			f"Attempting to enable an already enabled option {ECHO!r}."
		)
		mock_logger.reset_mock()
		state.us.enabled = False
		self.telnet.will(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + WILL + ECHO))
		self.assertTrue(state.us.negotiating)

	@patch("mudproto.telnet.logger")
	def test_telnet_wont(self, mock_logger: Mock) -> None:
		state: Mock = self.new_mocked_option_state()
		self.get_option_states()[ECHO] = state
		us_negotiating_warning: str = (
			f"We are refusing to enable option {ECHO!r}, "
			+ "but the option is already being negotiated by us."
		)
		him_negotiating_warning: str = (
			f"We are refusing to enable option {ECHO!r}, "
			+ "but the option is already being negotiated by peer."
		)
		state.us.negotiating = True
		self.telnet.wont(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(us_negotiating_warning)
		mock_logger.reset_mock()
		state.us.negotiating = False
		state.him.negotiating = True
		self.telnet.wont(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(him_negotiating_warning)
		mock_logger.reset_mock()
		state.him.negotiating = False
		state.us.enabled = False
		self.telnet.wont(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(
			f"Attempting to disable an already disabled option {ECHO!r}."
		)
		mock_logger.reset_mock()
		state.us.enabled = True
		self.telnet.wont(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + WONT + ECHO))
		self.assertTrue(state.us.negotiating)

	@patch("mudproto.telnet.logger")
	def test_telnet_do(self, mock_logger: Mock) -> None:
		state: Mock = self.new_mocked_option_state()
		self.get_option_states()[ECHO] = state
		us_negotiating_warning: str = (
			f"We are requesting that peer enable option {ECHO!r}, "
			+ "but the option is already being negotiated by us."
		)
		him_negotiating_warning: str = (
			f"We are requesting that peer enable option {ECHO!r}, "
			+ "but the option is already being negotiated by peer."
		)
		state.us.negotiating = True
		self.telnet.do(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(us_negotiating_warning)
		mock_logger.reset_mock()
		state.us.negotiating = False
		state.him.negotiating = True
		self.telnet.do(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(him_negotiating_warning)
		mock_logger.reset_mock()
		state.him.negotiating = False
		state.him.enabled = True
		self.telnet.do(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(
			f"Requesting that peer enable an already enabled option {ECHO!r}."
		)
		mock_logger.reset_mock()
		state.him.enabled = False
		self.telnet.do(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + DO + ECHO))
		self.assertTrue(state.him.negotiating)

	@patch("mudproto.telnet.logger")
	def test_telnet_dont(self, mock_logger: Mock) -> None:
		state: Mock = self.new_mocked_option_state()
		self.get_option_states()[ECHO] = state
		us_negotiating_warning: str = (
			f"We are requesting that peer disable option {ECHO!r}, "
			+ "but the option is already being negotiated by us."
		)
		him_negotiating_warning: str = (
			f"We are requesting that peer disable option {ECHO!r}, "
			+ "but the option is already being negotiated by peer."
		)
		state.us.negotiating = True
		self.telnet.dont(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(us_negotiating_warning)
		mock_logger.reset_mock()
		state.us.negotiating = False
		state.him.negotiating = True
		self.telnet.dont(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(him_negotiating_warning)
		mock_logger.reset_mock()
		state.him.negotiating = False
		state.him.enabled = False
		self.telnet.dont(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		mock_logger.warning.assert_called_once_with(
			f"Requesting that peer disable an already disabled option {ECHO!r}."
		)
		mock_logger.reset_mock()
		state.him.enabled = True
		self.telnet.dont(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + DONT + ECHO))
		self.assertTrue(state.him.negotiating)

	def test_telnet_get_option_state(self) -> None:
		self.assertNotIn(ECHO, self.get_option_states())
		self.telnet.get_option_state(ECHO)
		self.assertIn(ECHO, self.get_option_states())

	def test_telnet_request_negotiation(self) -> None:
		data: bytes = IAC + b"hello"
		expected: bytes = IAC + SB + ECHO + escape_iac(data) + IAC + SE
		self.telnet.request_negotiation(ECHO, data)
		self.assertEqual(self.player_receives, b"")
		self.assertEqual(self.game_receives, expected)
		self.game_receives.clear()
		self.assertEqual(self.telnet.state, TelnetState.DATA)

	@patch("mudproto.telnet.logger")
	@patch("mudproto.telnet.TelnetProtocol.on_subnegotiation")
	@patch("mudproto.telnet.TelnetProtocol.on_command")
	def test_telnet_on_data_received(
		self,
		mock_on_command: Mock,
		mock_on_subnegotiation: Mock,
		mock_logger: Mock,
	) -> None:
		# 'data' state:
		data: bytes = b"Hello World!"
		self.telnet.on_connection_made()
		self.assertEqual(self.parse(data), (data, b"", TelnetState.DATA))
		self.assertEqual(self.parse(data + IAC), (data, b"", TelnetState.COMMAND))
		self.assertEqual(self.parse(data + CR), (data, b"", TelnetState.NEWLINE))
		self.assertEqual(self.parse(data + CR_LF), (data + LF, b"", TelnetState.DATA))
		self.assertEqual(self.parse(data + CR_NULL), (data + CR, b"", TelnetState.DATA))
		self.assertEqual(self.parse(data + CR + IAC), (data + CR, b"", TelnetState.COMMAND))
		# 'command' and 'negotiation' states:
		self.assertEqual(self.parse(data + IAC + IAC), (data + IAC, b"", TelnetState.DATA))
		self.assertEqual(self.parse(data + IAC + SE), (data, b"", TelnetState.DATA))
		mock_logger.warning.assert_called_once_with("IAC SE received outside of subnegotiation.")
		mock_logger.reset_mock()
		self.assertEqual(self.parse(data + IAC + SB), (data, b"", TelnetState.SUBNEGOTIATION))
		for byte in COMMAND_BYTES:
			self.assertEqual(self.parse(data + IAC + byte), (data, b"", TelnetState.DATA))
			mock_on_command.assert_called_once_with(byte, None)
			mock_on_command.reset_mock()
		for byte in NEGOTIATION_BYTES:
			self.assertEqual(self.parse(data + IAC + byte), (data, b"", TelnetState.NEGOTIATION))
			self.assertEqual(self.parse(data + IAC + byte + ECHO), (data, b"", TelnetState.DATA))
			mock_on_command.assert_called_once_with(byte, ECHO)
			mock_on_command.reset_mock()
		self.assertEqual(self.parse(data + IAC + NULL), (data, b"", TelnetState.DATA))
		mock_logger.warning.assert_called_once_with(f"Unknown Telnet command received {NULL!r}.")
		mock_logger.reset_mock()
		# 'newline' state:
		# This state is entered when a packet ends in CR (I.E. when new lines are broken over two packets).
		self.telnet.on_data_received(data + CR)
		self.assertEqual(self.parse(LF), (data + LF, b"", TelnetState.DATA))
		self.telnet.on_data_received(data + CR)
		self.assertEqual(self.parse(NULL), (data + CR, b"", TelnetState.DATA))
		self.telnet.on_data_received(data + CR)
		self.assertEqual(self.parse(IAC), (data + CR, b"", TelnetState.COMMAND))
		self.telnet.on_data_received(data + CR)
		self.assertEqual(self.parse(IAC + IAC), (data + CR + IAC, b"", TelnetState.DATA))
		self.telnet.on_data_received(data + CR)
		self.assertEqual(self.parse(ECHO), (data + CR + ECHO, b"", TelnetState.DATA))
		# 'subnegotiation' state:
		self.assertEqual(self.parse(data + IAC + SB + IAC), (data, b"", TelnetState.SUBNEGOTIATION_ESCAPED))
		self.assertEqual(self.parse(data + IAC + SB + b"something"), (data, b"", TelnetState.SUBNEGOTIATION))
		# Note the name mangling __commands becomes _TelnetProtocol__commands.
		commands: bytes = getattr(self.telnet, "_TelnetProtocol__received_subnegotiation_bytes", b"invalid")
		self.assertEqual(commands, b"something")
		# 'subnegotiation-escaped' state:
		self.assertEqual(self.parse(data + IAC + SB + IAC + SE), (data, b"", TelnetState.DATA))
		mock_on_subnegotiation.assert_not_called()
		mock_on_subnegotiation.reset_mock()
		self.assertEqual(
			self.parse(data + IAC + SB + ECHO + b"something" + IAC + SE), (data, b"", TelnetState.DATA)
		)
		mock_on_subnegotiation.assert_called_once_with(ECHO, b"something")
		mock_on_subnegotiation.reset_mock()
		self.assertEqual(
			self.parse(data + IAC + SB + ECHO + b"something" + IAC + IAC + IAC + SE),
			(data, b"", TelnetState.DATA),
		)
		mock_on_subnegotiation.assert_called_once_with(ECHO, b"something" + IAC)

	@patch("mudproto.telnet.TelnetProtocol.on_unhandled_command")
	def test_telnet_on_command(self, mockon_unhandled_command: Mock) -> None:
		mock_command_map_ga = Mock()
		self.telnet.command_map[GA] = mock_command_map_ga
		self.telnet.on_command(GA, NULL)
		mock_command_map_ga.assert_called_once_with(NULL)
		self.telnet.on_command(ECHO, NULL)
		mockon_unhandled_command.assert_called_once_with(ECHO, NULL)

	@patch("mudproto.telnet.TelnetProtocol.on_unhandled_subnegotiation")
	def test_telnet_on_subnegotiation(self, mockon_unhandled_subnegotiation: Mock) -> None:
		mock_subnegotiation_map_ga = Mock()
		self.telnet.subnegotiation_map[GA] = mock_subnegotiation_map_ga
		self.telnet.on_subnegotiation(GA, NULL)
		mock_subnegotiation_map_ga.assert_called_once_with(NULL)
		self.telnet.on_subnegotiation(ECHO, NULL)
		mockon_unhandled_subnegotiation.assert_called_once_with(ECHO, NULL)

	@patch("mudproto.telnet.TelnetProtocol.on_enable_remote")
	def test_telnet_on_will(self, mock_on_enable_remote: Mock) -> None:
		with self.assertRaises(AssertionError):
			self.telnet.on_will(None)
		state: Mock = self.new_mocked_option_state()
		self.get_option_states()[ECHO] = state
		# --------------------
		# not state.him.enabled and not state.him.negotiating:
		# --------------------
		self.assertFalse(state.him.enabled)
		self.assertFalse(state.him.negotiating)
		mock_on_enable_remote.return_value = True
		self.telnet.on_will(ECHO)
		self.assertTrue(state.him.enabled)
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + DO + ECHO))
		self.game_receives.clear()
		state.him.enabled = False
		mock_on_enable_remote.return_value = False
		self.telnet.on_will(ECHO)
		self.assertFalse(state.him.enabled)
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + DONT + ECHO))
		self.game_receives.clear()
		# --------------------
		# not state.him.enabled and state.him.negotiating:
		# --------------------
		state.him.negotiating = True
		mock_on_enable_remote.return_value = True
		self.telnet.on_will(ECHO)
		self.assertTrue(state.him.enabled)
		self.assertFalse(state.him.negotiating)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		state.him.enabled = False
		state.him.negotiating = True
		mock_on_enable_remote.return_value = False
		with self.assertRaises(AssertionError):
			self.telnet.on_will(ECHO)
		self.assertTrue(state.him.enabled)
		self.assertFalse(state.him.negotiating)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		# --------------------
		# state.him.enabled and not state.him.negotiating:
		# --------------------
		self.telnet.on_will(ECHO)
		self.assertTrue(state.him.enabled)
		self.assertFalse(state.him.negotiating)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		# --------------------
		# state.him.enabled and state.him.negotiating:
		# --------------------
		state.him.negotiating = True
		with self.assertRaises(AssertionError):
			self.telnet.on_will(ECHO)

	@patch("mudproto.telnet.logger")
	@patch("mudproto.telnet.TelnetProtocol.on_disable_remote")
	def test_telnet_on_wont(self, mock_on_disable_remote: Mock, mock_logger: Mock) -> None:
		with self.assertRaises(AssertionError):
			self.telnet.on_wont(None)
		state: Mock = self.new_mocked_option_state()
		self.get_option_states()[ECHO] = state
		# --------------------
		# not state.him.enabled and not state.him.negotiating:
		# --------------------
		self.assertFalse(state.him.enabled)
		self.assertFalse(state.him.negotiating)
		self.telnet.on_wont(ECHO)
		self.assertFalse(state.him.enabled)
		self.assertFalse(state.him.negotiating)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		# --------------------
		# not state.him.enabled and state.him.negotiating:
		# --------------------
		state.him.negotiating = True
		self.telnet.on_wont(ECHO)
		self.assertFalse(state.him.negotiating)
		mock_logger.debug.assert_called_once()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		# --------------------
		# state.him.enabled and not state.him.negotiating:
		# --------------------
		state.him.enabled = True
		self.telnet.on_wont(ECHO)
		self.assertFalse(state.him.enabled)
		mock_on_disable_remote.assert_called_once()
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + DONT + ECHO))
		self.game_receives.clear()
		# --------------------
		# state.him.enabled and state.him.negotiating:
		# --------------------
		state.him.enabled = True
		state.him.negotiating = True
		mock_on_disable_remote.reset_mock()
		self.telnet.on_wont(ECHO)
		self.assertFalse(state.him.enabled)
		self.assertFalse(state.him.negotiating)
		mock_on_disable_remote.assert_called_once()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	@patch("mudproto.telnet.TelnetProtocol.on_enable_local")
	def test_telnet_on_do(self, mock_on_enable_local: Mock) -> None:
		with self.assertRaises(AssertionError):
			self.telnet.on_do(None)
		state: Mock = self.new_mocked_option_state()
		self.get_option_states()[ECHO] = state
		# --------------------
		# not state.us.enabled and not state.us.negotiating:
		# --------------------
		self.assertFalse(state.us.enabled)
		self.assertFalse(state.us.negotiating)
		mock_on_enable_local.return_value = True
		self.telnet.on_do(ECHO)
		self.assertTrue(state.us.enabled)
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + WILL + ECHO))
		self.game_receives.clear()
		state.us.enabled = False
		mock_on_enable_local.return_value = False
		self.telnet.on_do(ECHO)
		self.assertFalse(state.us.enabled)
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + WONT + ECHO))
		self.game_receives.clear()
		# --------------------
		# not state.us.enabled and state.us.negotiating:
		# --------------------
		state.us.negotiating = True
		mock_on_enable_local.reset_mock()
		self.telnet.on_do(ECHO)
		self.assertTrue(state.us.enabled)
		self.assertFalse(state.us.negotiating)
		mock_on_enable_local.assert_called_once()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		# --------------------
		# state.us.enabled and not state.us.negotiating:
		# --------------------
		self.telnet.on_do(ECHO)
		self.assertTrue(state.us.enabled)
		self.assertFalse(state.us.negotiating)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		# --------------------
		# state.us.enabled and state.us.negotiating:
		# --------------------
		state.us.negotiating = True
		with self.assertRaises(AssertionError):
			self.telnet.on_do(ECHO)

	@patch("mudproto.telnet.logger")
	@patch("mudproto.telnet.TelnetProtocol.on_disable_local")
	def test_telnet_on_dont(self, mock_on_disable_local: Mock, mock_logger: Mock) -> None:
		with self.assertRaises(AssertionError):
			self.telnet.on_dont(None)
		state: Mock = self.new_mocked_option_state()
		self.get_option_states()[ECHO] = state
		# --------------------
		# not state.us.enabled and not state.us.negotiating:
		# --------------------
		self.assertFalse(state.us.enabled)
		self.assertFalse(state.us.negotiating)
		self.telnet.on_dont(ECHO)
		self.assertFalse(state.us.enabled)
		self.assertFalse(state.us.negotiating)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		# --------------------
		# not state.us.enabled and state.us.negotiating:
		# --------------------
		state.us.negotiating = True
		self.telnet.on_dont(ECHO)
		self.assertFalse(state.us.negotiating)
		mock_logger.debug.assert_called_once()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
		# --------------------
		# state.us.enabled and not state.us.negotiating:
		# --------------------
		state.us.enabled = True
		self.telnet.on_dont(ECHO)
		self.assertFalse(state.us.enabled)
		mock_on_disable_local.assert_called_once()
		self.assertEqual((self.player_receives, self.game_receives), (b"", IAC + WONT + ECHO))
		self.game_receives.clear()
		# --------------------
		# state.us.enabled and state.us.negotiating:
		# --------------------
		state.us.enabled = True
		state.us.negotiating = True
		mock_on_disable_local.reset_mock()
		self.telnet.on_dont(ECHO)
		self.assertFalse(state.us.enabled)
		self.assertFalse(state.us.negotiating)
		mock_on_disable_local.assert_called_once()
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_telnet_on_unhandled_command(self) -> None:
		self.telnet.on_unhandled_command(ECHO, NULL)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_telnet_on_unhandled_subnegotiation(self) -> None:
		self.telnet.on_unhandled_subnegotiation(ECHO, NULL)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_telnet_on_enable_local(self) -> None:
		self.assertFalse(self.telnet.on_enable_local(ECHO))
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_telnet_on_enable_remote(self) -> None:
		self.assertFalse(self.telnet.on_enable_remote(ECHO))
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_telnet_on_disable_local(self) -> None:
		with self.assertRaises(NotImplementedError):
			self.telnet.on_disable_local(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))

	def test_telnet_on_disable_remote(self) -> None:
		with self.assertRaises(NotImplementedError):
			self.telnet.on_disable_remote(ECHO)
		self.assertEqual((self.player_receives, self.game_receives), (b"", b""))
