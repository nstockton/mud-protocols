# Copyright (c) 2025 Nick Stockton
# Copyright (c) 2001-2020 Twisted Matrix Laboratories
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# Original Author: Jean-Paul Calderone

"""Telnet protocol."""

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

# Local Modules:
from .connection import ConnectionInterface
from .telnet_constants import (
	COMMAND_BYTES,
	CR,
	CR_LF,
	CR_NULL,
	DESCRIPTIONS,
	DO,
	DONT,
	IAC,
	LF,
	NEGOTIATION_BYTES,
	NULL,
	SB,
	SE,
	WILL,
	WONT,
)
from .typedef import TelnetCommandMapType, TelnetSubnegotiationMapType


IAC_IAC: bytes = IAC + IAC


logger: logging.Logger = logging.getLogger(__name__)


def escape_iac(data: bytes) -> bytes:
	"""
	Escapes IAC bytes of a bytes-like object.

	Args:
		data: The data to be escaped.

	Returns:
		The data with IAC bytes escaped.
	"""
	return data.replace(IAC, IAC_IAC)


class TelnetError(Exception):
	"""Implements the base class for Telnet exceptions."""


@dataclass(slots=True)
class OptionPerspective:
	"""
	Represents the state of an option on one side of the Telnet connection.

	Some options can be enabled on a particular side of the connection
	(RFC 1073 for example: only the client can have NAWS enabled).
	Other options can be enabled on either or both sides (such as RFC 1372: each
	side can have its own flow control state).
	"""

	enabled: bool = False
	"""Indicates whether or not this option is enabled on one side of the connection."""
	negotiating: bool = False
	"""Tracks whether negotiation about this option is in progress."""


@dataclass(slots=True)
class OptionState:
	"""Represents the state of an option on both sides of a Telnet connection."""

	us: OptionPerspective = field(default_factory=OptionPerspective)
	"""The state of the option on this side of the connection."""
	him: OptionPerspective = field(default_factory=OptionPerspective)
	"""The state of the option on the other side of the connection."""


class TelnetState(Enum):
	"""Valid states for the state machine."""

	DATA = auto()
	COMMAND = auto()
	NEWLINE = auto()
	NEGOTIATION = auto()
	SUBNEGOTIATION = auto()
	SUBNEGOTIATION_ESCAPED = auto()


class TelnetInterface(ConnectionInterface):
	"""Defines the interface for the Telnet protocol."""

	command_map: TelnetCommandMapType
	"""A mapping of command bytes to command handlers."""
	subnegotiation_map: TelnetSubnegotiationMapType
	"""A mapping of subnegotiation bytes to subnegotiation handlers."""

	@abstractmethod
	def will(self, option: bytes) -> None:
		"""
		Negotiates enabling a locally managed option.

		Args:
			option: The option to enable.
		"""

	@abstractmethod
	def wont(self, option: bytes) -> None:
		"""
		Negotiates disabling a locally managed option.

		Args:
			option: The option to disable.
		"""

	@abstractmethod
	def do(self, option: bytes) -> None:
		"""
		Negotiates enabling a Remotely managed option.

		Args:
			option: The option to enable.
		"""

	@abstractmethod
	def dont(self, option: bytes) -> None:
		"""
		Negotiates disabling a Remotely managed option.

		Args:
			option: The option to disable.
		"""

	@abstractmethod
	def get_option_state(self, option: bytes) -> OptionState:
		"""
		Retrieves the state of a Telnet option.

		Args:
			option: The option to get the state of.

		Returns:
			The option state.
		"""

	@abstractmethod
	def request_negotiation(self, option: bytes, data: bytes) -> None:
		"""
		Sends a subnegotiation message to the peer.

		Args:
			option: The subnegotiation option.
			data: The payload.
		"""

	@abstractmethod
	def on_command(self, command: bytes, option: bytes | None) -> None:
		"""
		Called when a 1 or 2 byte command is received.

		Args:
			command: The first byte in a 1 or 2 byte negotiation sequence.
			option: The second byte in a 2 byte negotiation sequence or None.
		"""

	@abstractmethod
	def on_subnegotiation(self, option: bytes, data: bytes) -> None:
		"""
		Called when a subnegotiation is received.

		Args:
			option: The subnegotiation option.
			data: The payload.
		"""

	@abstractmethod
	def on_unhandled_command(self, command: bytes, option: bytes | None) -> None:
		"""
		Called for commands for which no handler is installed.

		Args:
			command: The first byte in a 1 or 2 byte negotiation sequence.
			option: The second byte in a 2 byte negotiation sequence or None.
		"""

	@abstractmethod
	def on_unhandled_subnegotiation(self, option: bytes, data: bytes) -> None:
		"""
		Called for subnegotiations for which no handler is installed.

		Args:
			option: The subnegotiation option.
			data: The payload.
		"""

	@abstractmethod
	def on_enable_local(self, option: bytes) -> bool:
		"""
		Called to accept or reject the request for us to manage the option.

		Args:
			option: The option that peer requests us to handle.

		Returns:
			True if we will handle the option, False otherwise.
		"""
		return False  # Reject all options by default.

	@abstractmethod
	def on_disable_local(self, option: bytes) -> None:
		"""
		Disables a locally managed option.

		This method is called before we disable a
		locally enabled option, in order to perform any necessary cleanup.

		Note:
			If on_enable_local is overridden, this method must be overridden as well.

		Args:
			option: The option being disabled.
		"""
		raise NotImplementedError(f"Don't know how to disable local Telnet option {option!r}")

	@abstractmethod
	def on_enable_remote(self, option: bytes) -> bool:
		"""
		Called to accept or reject the request for peer to manage the option.

		Args:
			option: The option that peer wants to handle.

		Returns:
			True if we will allow peer to handle the option, False otherwise.
		"""
		return False  # Reject all options by default.

	@abstractmethod
	def on_disable_remote(self, option: bytes) -> None:
		"""
		Disables a remotely managed option.

		This method is called when peer disables a remotely enabled option,
		in order to perform any necessary cleanup on our end.

		Note:
			If on_enable_remote is overridden, this method must be overridden as well.

		Args:
			option: The option being disabled.
		"""
		raise NotImplementedError(f"Don't know how to disable remote Telnet option {option!r}")

	@abstractmethod
	def on_option_enabled(self, option: bytes) -> None:
		"""
		Called after an option has been fully enabled.

		Args:
			option: The option that has been enabled.
		"""


class TelnetProtocol(TelnetInterface):  # NOQA: PLR0904
	"""Implements the Telnet protocol."""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		"""
		Defines the constructor.

		Args:
			*args: Positional arguments to be passed to the parent constructor.
			**kwargs: Key-word only arguments to be passed to the parent constructor.
		"""
		super().__init__(*args, **kwargs)
		self.__app_data_buffer: bytearray = bytearray()
		self.__received_command_byte: bytes = b""
		self.__received_subnegotiation_bytes: bytearray = bytearray()
		self.__option_states: dict[bytes, OptionState] = {}
		"""A mapping of option bytes to their current state."""
		self.state: TelnetState = TelnetState.DATA
		"""The state of the state machine."""
		# When a Telnet command is received, the command byte,
		# the first byte after IAC, is looked up in the commandMap dictionary.
		# If a callable is found, it is invoked with the argument of the command,
		# or None if the command takes no argument.  Values should be added to
		# this dictionary if commands wish to be handled.  By default,
		# only WILL, WONT, DO, and DONT are handled.  These should not
		# be overridden, as this class handles them correctly and
		# provides an API for interacting with them.
		self.command_map: TelnetCommandMapType = {
			WILL: self.on_will,
			WONT: self.on_wont,
			DO: self.on_do,
			DONT: self.on_dont,
		}
		# When a subnegotiation command is received, the option byte, the
		# first byte after SB, is looked up in the subnegotiationMap dictionary.  If
		# a callable is found, it is invoked with the argument of the
		# subnegotiation.  Values should be added to this dictionary if
		# subnegotiations are to be handled.  By default, no values are
		# handled.
		self.subnegotiation_map: TelnetSubnegotiationMapType = {}

	def _do(self, option: bytes) -> None:
		"""
		Sends IAC DO option to the peer.

		Args:
			option: The option to send.
		"""
		logger.debug(f"Send to peer: IAC DO {DESCRIPTIONS.get(option, repr(option))}")
		self.write(IAC + DO + option)

	def _dont(self, option: bytes) -> None:
		"""
		Sends IAC DONT option to the peer.

		Args:
			option: The option to send.
		"""
		logger.debug(f"Send to peer: IAC DONT {DESCRIPTIONS.get(option, repr(option))}")
		self.write(IAC + DONT + option)

	def _will(self, option: bytes) -> None:
		"""
		Sends IAC WILL option to the peer.

		Args:
			option: The option to send.
		"""
		logger.debug(f"Send to peer: IAC WILL {DESCRIPTIONS.get(option, repr(option))}")
		self.write(IAC + WILL + option)

	def _wont(self, option: bytes) -> None:
		"""
		Sends IAC WONT option to the peer.

		Args:
			option: The option to send.
		"""
		logger.debug(f"Send to peer: IAC WONT {DESCRIPTIONS.get(option, repr(option))}")
		self.write(IAC + WONT + option)

	def will(self, option: bytes) -> None:  # NOQA: D102
		state = self.get_option_state(option)
		if state.us.negotiating or state.him.negotiating:
			logger.warning(
				f"We are offering to enable option {option!r}, but the option is "
				+ f"already being negotiated by {'us' if state.us.negotiating else 'peer'}."
			)
		elif state.us.enabled:
			logger.warning(f"Attempting to enable an already enabled option {option!r}.")
		else:
			state.us.negotiating = True
			self._will(option)

	def wont(self, option: bytes) -> None:  # NOQA: D102
		state = self.get_option_state(option)
		if state.us.negotiating or state.him.negotiating:
			logger.warning(
				f"We are refusing to enable option {option!r}, but the option is "
				+ f"already being negotiated by {'us' if state.us.negotiating else 'peer'}."
			)
		elif not state.us.enabled:
			logger.warning(f"Attempting to disable an already disabled option {option!r}.")
		else:
			state.us.negotiating = True
			self._wont(option)

	def do(self, option: bytes) -> None:  # NOQA: D102
		state = self.get_option_state(option)
		if state.us.negotiating or state.him.negotiating:
			logger.warning(
				f"We are requesting that peer enable option {option!r}, but the option is "
				+ f"already being negotiated by {'us' if state.us.negotiating else 'peer'}."
			)
		elif state.him.enabled:
			logger.warning(f"Requesting that peer enable an already enabled option {option!r}.")
		else:
			state.him.negotiating = True
			self._do(option)

	def dont(self, option: bytes) -> None:  # NOQA: D102
		state = self.get_option_state(option)
		if state.us.negotiating or state.him.negotiating:
			logger.warning(
				f"We are requesting that peer disable option {option!r}, but the option is "
				+ f"already being negotiated by {'us' if state.us.negotiating else 'peer'}."
			)
		elif not state.him.enabled:
			logger.warning(f"Requesting that peer disable an already disabled option {option!r}.")
		else:
			state.him.negotiating = True
			self._dont(option)

	def get_option_state(self, option: bytes) -> OptionState:  # NOQA: D102
		if option not in self.__option_states:
			self.__option_states[option] = OptionState()
		return self.__option_states[option]

	def request_negotiation(self, option: bytes, data: bytes) -> None:  # NOQA: D102
		self.write(IAC + SB + option + escape_iac(data) + IAC + SE)

	def on_connection_made(self) -> None:  # NOQA: D102
		return super().on_connection_made()  # type: ignore[safe-super]

	def on_connection_lost(self) -> None:  # NOQA: D102
		return super().on_connection_lost()  # type: ignore[safe-super]

	def __flush_app_data(self) -> None:
		if self.__app_data_buffer:
			super().on_data_received(bytes(self.__app_data_buffer))
			self.__app_data_buffer.clear()

	def __process_data_state(self, data: bytes) -> bytes:
		app_data, separator, data = data.partition(IAC)
		if separator:
			self.state = TelnetState.COMMAND
		elif app_data.endswith(CR):
			self.state = TelnetState.NEWLINE
			app_data = app_data[:-1]
		self.__app_data_buffer.extend(app_data.replace(CR_LF, LF).replace(CR_NULL, CR))
		return data

	def __process_command_state(self, byte: bytes) -> None:
		if byte == IAC:
			# Escaped IAC.
			self.__app_data_buffer.extend(byte)
			self.state = TelnetState.DATA
		elif byte == SE:
			self.state = TelnetState.DATA
			logger.warning("IAC SE received outside of subnegotiation.")
		elif byte == SB:
			self.state = TelnetState.SUBNEGOTIATION
			self.__received_subnegotiation_bytes.clear()
		elif byte in COMMAND_BYTES:
			self.state = TelnetState.DATA
			self.__flush_app_data()
			logger.debug(f"Received from peer: IAC {DESCRIPTIONS[byte]}")
			self.on_command(byte, None)
		elif byte in NEGOTIATION_BYTES:
			self.state = TelnetState.NEGOTIATION
			self.__received_command_byte = byte
		else:
			self.state = TelnetState.DATA
			logger.warning(f"Unknown Telnet command received {byte!r}.")

	def __process_negotiation_state(self, byte: bytes) -> None:
		self.state = TelnetState.DATA
		command = self.__received_command_byte
		self.__received_command_byte = b""
		self.__flush_app_data()
		logger.debug(f"Received from peer: IAC {DESCRIPTIONS[command]} {DESCRIPTIONS.get(byte, repr(byte))}")
		self.on_command(command, byte)

	def __process_newline_state(self, byte: bytes) -> None:
		self.state = TelnetState.DATA
		if byte == LF:
			self.__app_data_buffer.extend(byte)
		elif byte == NULL:
			self.__app_data_buffer.extend(CR)
		elif byte == IAC:
			# IAC isn't really allowed after CR, according to the
			# RFC, but handling it this way is less surprising than
			# delivering the IAC to the app as application data.
			# The purpose of the restriction is to allow terminals
			# to unambiguously interpret the behavior of the CR
			# after reading only one more byte.  CR + LF is supposed
			# to mean one thing, cursor to next line, first column,
			# CR + NUL another, cursor to first column.  Absent the
			# NUL, it still makes sense to interpret this as CR and
			# then apply all the usual interpretation to the IAC.
			self.__app_data_buffer.extend(CR)
			self.state = TelnetState.COMMAND
		else:
			self.__app_data_buffer.extend(CR + byte)

	def __process_subnegotiation_state(self, byte: bytes) -> None:
		if byte == IAC:
			self.state = TelnetState.SUBNEGOTIATION_ESCAPED
		else:
			self.__received_subnegotiation_bytes.extend(byte)

	def __process_subnegotiation_escaped_state(self, byte: bytes) -> None:
		if byte == SE:
			self.state = TelnetState.DATA
			self.__flush_app_data()
			commands = bytes(self.__received_subnegotiation_bytes)
			self.__received_subnegotiation_bytes.clear()
			if not commands:
				logger.warning("Empty subnegotiation received.")
				return
			option, commands = commands[:1], commands[1:]
			logger.debug(
				f"Received from peer: IAC SB {DESCRIPTIONS.get(option, repr(option))} "
				+ f"{commands!r} IAC SE"
			)
			self.on_subnegotiation(option, commands)
		else:
			self.state = TelnetState.SUBNEGOTIATION
			self.__received_subnegotiation_bytes.extend(byte)

	def on_data_received(self, data: bytes) -> None:  # NOQA: D102
		while data:
			if self.state is TelnetState.DATA:
				# Process data as chunks for speed.
				data = self.__process_data_state(data)
				continue
			# All other states require iterating 1 byte at a time.
			byte, data = data[:1], data[1:]
			if self.state is TelnetState.COMMAND:
				self.__process_command_state(byte)
			elif self.state is TelnetState.NEGOTIATION:
				self.__process_negotiation_state(byte)
			elif self.state is TelnetState.NEWLINE:
				self.__process_newline_state(byte)
			elif self.state is TelnetState.SUBNEGOTIATION:
				self.__process_subnegotiation_state(byte)
			elif self.state is TelnetState.SUBNEGOTIATION_ESCAPED:
				self.__process_subnegotiation_escaped_state(byte)
		self.__flush_app_data()

	def on_command(self, command: bytes, option: bytes | None) -> None:  # NOQA: D102
		if command in self.command_map:
			self.command_map[command](option)
		else:
			self.on_unhandled_command(command, option)

	def on_subnegotiation(self, option: bytes, data: bytes) -> None:  # NOQA: D102
		if option in self.subnegotiation_map:
			self.subnegotiation_map[option](data)
		else:
			self.on_unhandled_subnegotiation(option, data)

	def on_will(self, option: bytes | None) -> None:
		"""
		Called when an IAC + WILL + option is received.

		Args:
			option: The received option.
		"""  # NOQA: DOC501
		if option is None:
			raise AssertionError("Option must not be None in this context.")
		state = self.get_option_state(option)
		if not state.him.enabled and not state.him.negotiating:
			# Peer is unilaterally offering to enable an option.
			if self.on_enable_remote(option):
				state.him.enabled = True
				self._do(option)
				self.on_option_enabled(option)
			else:
				self._dont(option)
		elif not state.him.enabled and state.him.negotiating:
			# Peer agreed to enable an option in response to our request.
			state.him.enabled = True
			state.him.negotiating = False
			if not self.on_enable_remote(option):
				raise AssertionError(f"enableRemote must return True in this context (for option {option!r})")
			self.on_option_enabled(option)
		elif state.him.enabled and not state.him.negotiating:
			# Peer is unilaterally offering to enable an already-enabled option.
			# Ignore this.
			pass
		elif state.him.enabled and state.him.negotiating:
			# This is a bogus state.  It is here for completeness.  It will
			# never be entered.
			raise AssertionError(
				"him.enabled and him.negotiating cannot be True at the same time. "
				+ f"state: {state!r}, option: {option!r}"
			)

	def on_wont(self, option: bytes | None) -> None:
		"""
		Called when an IAC + WONT + option is received.

		Args:
			option: The received option.
		"""  # NOQA: DOC501
		if option is None:
			raise AssertionError("Option must not be None in this context.")
		state = self.get_option_state(option)
		if not state.him.enabled and not state.him.negotiating:
			# Peer is unilaterally demanding that an already-disabled option be/remain disabled.
			# Ignore this, although we could record it and refuse subsequent enable attempts
			# from our side, peer could refuse them again, so we won't.
			pass
		elif not state.him.enabled and state.him.negotiating:
			# Peer refused to enable an option in response to our request.
			state.him.negotiating = False
			logger.debug(
				f"Peer refuses to enable option {DESCRIPTIONS.get(option, repr(option))} "
				+ "in response to our request."
			)
		elif state.him.enabled and not state.him.negotiating:
			# Peer is unilaterally demanding that an option be disabled.
			state.him.enabled = False
			self.on_disable_remote(option)
			self._dont(option)
		elif state.him.enabled and state.him.negotiating:
			# Peer agreed to disable an option at our request.
			state.him.enabled = False
			state.him.negotiating = False
			self.on_disable_remote(option)

	def on_do(self, option: bytes | None) -> None:
		"""
		Called when an IAC + DO + option is received.

		Args:
			option: The received option.
		"""  # NOQA: DOC501
		if option is None:
			raise AssertionError("Option must not be None in this context.")
		state = self.get_option_state(option)
		if not state.us.enabled and not state.us.negotiating:
			# Peer is unilaterally requesting that we enable an option.
			if self.on_enable_local(option):
				state.us.enabled = True
				self._will(option)
				self.on_option_enabled(option)
			else:
				self._wont(option)
		elif not state.us.enabled and state.us.negotiating:
			# Peer agreed to allow us to enable an option at our request.
			state.us.enabled = True
			state.us.negotiating = False
			self.on_enable_local(option)
			self.on_option_enabled(option)
		elif state.us.enabled and not state.us.negotiating:
			# Peer is unilaterally requesting us to enable an already-enabled option.
			# Ignore this.
			pass
		elif state.us.enabled and state.us.negotiating:
			# This is a bogus state.  It is here for completeness.  It will never be
			# entered.
			raise AssertionError(
				"us.enabled and us.negotiating cannot be True at the same time. "
				+ f"state: {state!r}, option: {option!r}"
			)

	def on_dont(self, option: bytes | None) -> None:
		"""
		Called when an IAC + DONT + option is received.

		Args:
			option: The received option.
		"""  # NOQA: DOC501
		if option is None:
			raise AssertionError("Option must not be None in this context.")
		state = self.get_option_state(option)
		if not state.us.enabled and not state.us.negotiating:
			# Peer is unilaterally demanding us to disable an already-disabled option.
			# Ignore this.
			pass
		elif not state.us.enabled and state.us.negotiating:
			# Offered option was refused.
			state.us.negotiating = False
			logger.debug(f"Peer rejects our offer to enable option {DESCRIPTIONS.get(option, repr(option))}.")
		elif state.us.enabled and not state.us.negotiating:
			# Peer is unilaterally demanding we disable an option.
			state.us.enabled = False
			self.on_disable_local(option)
			self._wont(option)
		elif state.us.enabled and state.us.negotiating:
			# Peer acknowledged our notice that we will disable an option.
			state.us.enabled = False
			state.us.negotiating = False
			self.on_disable_local(option)

	def on_unhandled_command(self, command: bytes, option: bytes | None) -> None:  # NOQA: D102
		return super().on_unhandled_command(command, option)  # type: ignore[safe-super]

	def on_unhandled_subnegotiation(self, option: bytes, data: bytes) -> None:  # NOQA: D102
		return super().on_unhandled_subnegotiation(option, data)  # type: ignore[safe-super]

	def on_enable_local(self, option: bytes) -> bool:  # NOQA: D102
		return super().on_enable_local(option)

	def on_disable_local(self, option: bytes) -> None:  # NOQA: D102
		return super().on_disable_local(option)  # type: ignore[safe-super]

	def on_enable_remote(self, option: bytes) -> bool:  # NOQA: D102
		return super().on_enable_remote(option)

	def on_disable_remote(self, option: bytes) -> None:  # NOQA: D102
		return super().on_disable_remote(option)  # type: ignore[safe-super]

	def on_option_enabled(self, option: bytes) -> None:  # NOQA: D102
		return super().on_option_enabled(option)  # type: ignore[safe-super]
