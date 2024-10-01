"""
Telnet protocol.
"""


# Copyright (c) 2001-2020 Twisted Matrix Laboratories.

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

# Author: Jean-Paul Calderone
# Author: Nick Stockton

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
from abc import abstractmethod
from enum import Enum, auto
from typing import Any, Union

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
from .typedef import TELNET_COMMAND_MAP_TYPE, TELNET_SUBNEGOTIATION_MAP_TYPE


IAC_IAC: bytes = IAC + IAC


logger: logging.Logger = logging.getLogger(__name__)


def escapeIAC(data: bytes) -> bytes:
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


class _Perspective:
	"""
	Represents the state of an option on one side of the Telnet connection.

	Some options can be enabled on a particular side of the connection
	(RFC 1073 for example: only the client can have NAWS enabled).
	Other options can be enabled on either or both sides (such as RFC 1372: each
	side can have its own flow control state).

	Attributes:
		enabled: Indicates whether or not this option is enabled on one side of the connection.
		negotiating: Tracks whether negotiation about this option is in progress.
	"""

	enabled: bool = False
	negotiating: bool = False

	def __str__(self) -> str:
		return f"Enabled: {self.enabled}, Negotiating: {self.negotiating}"


class _OptionState:
	"""
	Represents the state of an option on both sides of a Telnet connection.

	Attributes:
		us: The state of the option on this side of the connection.
		him: The state of the option on the other side of the connection.
	"""

	def __init__(self) -> None:
		self.us: _Perspective = _Perspective()
		self.him: _Perspective = _Perspective()

	def __repr__(self) -> str:
		return f"<_OptionState us={self.us} him={self.him}>"


class TelnetState(Enum):
	"""
	Valid states for the state machine.
	"""

	DATA = auto()
	COMMAND = auto()
	NEWLINE = auto()
	NEGOTIATION = auto()
	SUBNEGOTIATION = auto()
	SUBNEGOTIATION_ESCAPED = auto()


class TelnetInterface(ConnectionInterface):
	commandMap: TELNET_COMMAND_MAP_TYPE
	"""A mapping of bytes to callables."""
	subnegotiationMap: TELNET_SUBNEGOTIATION_MAP_TYPE
	"""A mapping of bytes to callables."""

	@abstractmethod
	def will(self, option: bytes) -> None:
		"""
		Indicates our willingness to enable an option.

		Args:
			option: The option to accept.
		"""

	@abstractmethod
	def wont(self, option: bytes) -> None:
		"""
		Indicates we are not willing to enable an option.

		Args:
			option: The option to reject.
		"""

	@abstractmethod
	def do(self, option: bytes) -> None:
		"""
		Requests that the peer enable an option.

		Args:
			option: The option to enable.
		"""

	@abstractmethod
	def dont(self, option: bytes) -> None:
		"""
		Requests that the peer disable an option.

		Args:
			option: The option to disable.
		"""

	@abstractmethod
	def getOptionState(self, option: bytes) -> _OptionState:
		"""
		Gets the state of a Telnet option.

		Args:
			option: The option to get state.

		Returns:
			An object containing the option state.
		"""

	@abstractmethod
	def requestNegotiation(self, option: bytes, data: bytes) -> None:
		"""
		Sends a subnegotiation message to the peer.

		Args:
			option: The subnegotiation option.
			data: The payload.
		"""

	@abstractmethod
	def on_command(self, command: bytes, option: Union[bytes, None]) -> None:
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
	def on_unhandledCommand(self, command: bytes, option: Union[bytes, None]) -> None:
		"""
		Called for commands for which no handler is installed.

		Args:
			command: The first byte in a 1 or 2 byte negotiation sequence.
			option: The second byte in a 2 byte negotiation sequence or None.
		"""

	@abstractmethod
	def on_unhandledSubnegotiation(self, option: bytes, data: bytes) -> None:
		"""
		Called for subnegotiations for which no handler is installed.

		Args:
			option: The subnegotiation option.
			data: The payload.
		"""

	@abstractmethod
	def on_enableLocal(self, option: bytes) -> bool:
		"""
		Called to accept or reject the request for us to manage the option.

		Args:
			option: The option that peer requests us to handle.

		Returns:
			True if we will handle the option, False otherwise.
		"""
		return False  # Reject all options by default.

	@abstractmethod
	def on_disableLocal(self, option: bytes) -> None:
		"""
		Disables a locally managed option.

		This method is called before we disable a
		locally enabled option, in order to perform any necessary cleanup.

		Note:
			If on_enableLocal is overridden, this method must be overridden as well.

		Args:
			option: The option being disabled.
		"""
		raise NotImplementedError(f"Don't know how to disable local Telnet option {option!r}")

	@abstractmethod
	def on_enableRemote(self, option: bytes) -> bool:
		"""
		Called to accept or reject the request for peer to manage the option.

		Args:
			option: The option that peer wants to handle.

		Returns:
			True if we will allow peer to handle the option, False otherwise.
		"""
		return False  # Reject all options by default.

	@abstractmethod
	def on_disableRemote(self, option: bytes) -> None:
		"""
		Disables a remotely managed option.

		This method is called when peer disables a remotely enabled option,
		in order to perform any necessary cleanup on our end.

		Note:
			If on_enableRemote is overridden, this method must be overridden as well.

		Args:
			option: The option being disabled.
		"""
		raise NotImplementedError(f"Don't know how to disable remote Telnet option {option!r}")

	@abstractmethod
	def on_optionEnabled(self, option: bytes) -> None:
		"""
		Called after an option has been fully enabled.

		Args:
			option: The option that has been enabled.
		"""


class TelnetProtocol(TelnetInterface):
	"""
	Implements the Telnet protocol.
	"""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self.state: TelnetState = TelnetState.DATA
		"""The state of the state machine."""
		self._options: dict[bytes, _OptionState] = {}
		"""A mapping of option bytes to their current state."""
		# When a Telnet command is received, the command byte
		# (the first byte after IAC) is looked up in the commandMap dictionary.
		# If a callable is found, it is invoked with the argument of the command,
		# or None if the command takes no argument.  Values should be added to
		# this dictionary if commands wish to be handled.  By default,
		# only WILL, WONT, DO, and DONT are handled.  These should not
		# be overridden, as this class handles them correctly and
		# provides an API for interacting with them.
		self.commandMap: TELNET_COMMAND_MAP_TYPE = {
			WILL: self.on_will,
			WONT: self.on_wont,
			DO: self.on_do,
			DONT: self.on_dont,
		}
		# When a subnegotiation command is received, the option byte (the
		# first byte after SB) is looked up in the subnegotiationMap dictionary.  If
		# a callable is found, it is invoked with the argument of the
		# subnegotiation.  Values should be added to this dictionary if
		# subnegotiations are to be handled.  By default, no values are
		# handled.
		self.subnegotiationMap: TELNET_SUBNEGOTIATION_MAP_TYPE = {}

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

	def will(self, option: bytes) -> None:
		state = self.getOptionState(option)
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

	def wont(self, option: bytes) -> None:
		state = self.getOptionState(option)
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

	def do(self, option: bytes) -> None:
		state = self.getOptionState(option)
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

	def dont(self, option: bytes) -> None:
		state = self.getOptionState(option)
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

	def getOptionState(self, option: bytes) -> _OptionState:
		if option not in self._options:
			self._options[option] = _OptionState()
		return self._options[option]

	def requestNegotiation(self, option: bytes, data: bytes) -> None:
		self.write(IAC + SB + option + escapeIAC(data) + IAC + SE)

	def on_connectionMade(self) -> None:
		return super().on_connectionMade()

	def on_connectionLost(self) -> None:
		return super().on_connectionLost()

	def on_dataReceived(self, data: bytes) -> None:  # NOQA: C901
		appDataBuffer: bytearray = bytearray()
		while data:
			if self.state is TelnetState.DATA:
				appData, separator, data = data.partition(IAC)
				if separator:
					self.state = TelnetState.COMMAND
				elif appData.endswith(CR):
					self.state = TelnetState.NEWLINE
					appData = appData[:-1]
				appDataBuffer.extend(appData.replace(CR_LF, LF).replace(CR_NULL, CR))
				continue
			byte, data = data[:1], data[1:]
			if self.state is TelnetState.COMMAND:
				if byte == IAC:
					# Escaped IAC.
					appDataBuffer.extend(byte)
					self.state = TelnetState.DATA
				elif byte == SE:
					self.state = TelnetState.DATA
					logger.warning("IAC SE received outside of subnegotiation.")
				elif byte == SB:
					self.state = TelnetState.SUBNEGOTIATION
					self._commands: bytearray = bytearray()
				elif byte in COMMAND_BYTES:
					self.state = TelnetState.DATA
					if appDataBuffer:
						super().on_dataReceived(bytes(appDataBuffer))
						appDataBuffer.clear()
					logger.debug(f"Received from peer: IAC {DESCRIPTIONS[byte]}")
					self.on_command(byte, None)
				elif byte in NEGOTIATION_BYTES:
					self.state = TelnetState.NEGOTIATION
					self._command = byte
				else:
					self.state = TelnetState.DATA
					logger.warning(f"Unknown Telnet command received {byte!r}.")
			elif self.state is TelnetState.NEGOTIATION:
				self.state = TelnetState.DATA
				command = self._command
				del self._command
				if appDataBuffer:
					super().on_dataReceived(bytes(appDataBuffer))
					appDataBuffer.clear()
				logger.debug(
					f"Received from peer: IAC {DESCRIPTIONS[command]} {DESCRIPTIONS.get(byte, repr(byte))}"
				)
				self.on_command(command, byte)
			elif self.state is TelnetState.NEWLINE:
				self.state = TelnetState.DATA
				if byte == LF:
					appDataBuffer.extend(byte)
				elif byte == NULL:
					appDataBuffer.extend(CR)
				elif byte == IAC:
					# IAC isn't really allowed after CR, according to the
					# RFC, but handling it this way is less surprising than
					# delivering the IAC to the app as application data.
					# The purpose of the restriction is to allow terminals
					# to unambiguously interpret the behavior of the CR
					# after reading only one more byte.  CR + LF is supposed
					# to mean one thing (cursor to next line, first column),
					# CR + NUL another (cursor to first column).  Absent the
					# NUL, it still makes sense to interpret this as CR and
					# then apply all the usual interpretation to the IAC.
					appDataBuffer.extend(CR)
					self.state = TelnetState.COMMAND
				else:
					appDataBuffer.extend(CR + byte)
			elif self.state is TelnetState.SUBNEGOTIATION:
				if byte == IAC:
					self.state = TelnetState.SUBNEGOTIATION_ESCAPED
				else:
					self._commands.extend(byte)
			elif self.state is TelnetState.SUBNEGOTIATION_ESCAPED:
				if byte == SE:
					self.state = TelnetState.DATA
					commands = bytes(self._commands)
					del self._commands
					if appDataBuffer:
						super().on_dataReceived(bytes(appDataBuffer))
						appDataBuffer.clear()
					option, commands = commands[:1], commands[1:]
					logger.debug(
						f"Received from peer: IAC SB {DESCRIPTIONS.get(option, repr(option))} "
						+ f"{commands!r} IAC SE"
					)
					self.on_subnegotiation(option, commands)
				else:
					self.state = TelnetState.SUBNEGOTIATION
					self._commands.extend(byte)
		if appDataBuffer:
			super().on_dataReceived(bytes(appDataBuffer))

	def on_command(self, command: bytes, option: Union[bytes, None]) -> None:
		if command in self.commandMap:
			self.commandMap[command](option)
		else:
			self.on_unhandledCommand(command, option)

	def on_subnegotiation(self, option: bytes, data: bytes) -> None:
		if option in self.subnegotiationMap:
			self.subnegotiationMap[option](data)
		else:
			self.on_unhandledSubnegotiation(option, data)

	def on_will(self, option: Union[bytes, None]) -> None:
		"""
		Called when an IAC + WILL + option is received.

		Args:
			option: The received option.
		"""
		if option is None:
			raise AssertionError("Option must not be None in this context.")
		state = self.getOptionState(option)
		if not state.him.enabled and not state.him.negotiating:
			# Peer is unilaterally offering to enable an option.
			if self.on_enableRemote(option):
				state.him.enabled = True
				self._do(option)
				self.on_optionEnabled(option)
			else:
				self._dont(option)
		elif not state.him.enabled and state.him.negotiating:
			# Peer agreed to enable an option in response to our request.
			state.him.enabled = True
			state.him.negotiating = False
			if not self.on_enableRemote(option):
				raise AssertionError(f"enableRemote must return True in this context (for option {option!r})")
			self.on_optionEnabled(option)
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

	def on_wont(self, option: Union[bytes, None]) -> None:
		"""
		Called when an IAC + WONT + option is received.

		Args:
			option: The received option.
		"""
		if option is None:
			raise AssertionError("Option must not be None in this context.")
		state = self.getOptionState(option)
		if not state.him.enabled and not state.him.negotiating:
			# Peer is unilaterally demanding that an already-disabled option be/remain disabled.
			# Ignore this (although we could record it and refuse subsequent enable attempts
			# from our side, peer could refuse them again, so we won't).
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
			self.on_disableRemote(option)
			self._dont(option)
		elif state.him.enabled and state.him.negotiating:
			# Peer agreed to disable an option at our request.
			state.him.enabled = False
			state.him.negotiating = False
			self.on_disableRemote(option)

	def on_do(self, option: Union[bytes, None]) -> None:
		"""
		Called when an IAC + DO + option is received.

		Args:
			option: The received option.
		"""
		if option is None:
			raise AssertionError("Option must not be None in this context.")
		state = self.getOptionState(option)
		if not state.us.enabled and not state.us.negotiating:
			# Peer is unilaterally requesting that we enable an option.
			if self.on_enableLocal(option):
				state.us.enabled = True
				self._will(option)
				self.on_optionEnabled(option)
			else:
				self._wont(option)
		elif not state.us.enabled and state.us.negotiating:
			# Peer agreed to allow us to enable an option at our request.
			state.us.enabled = True
			state.us.negotiating = False
			self.on_enableLocal(option)
			self.on_optionEnabled(option)
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

	def on_dont(self, option: Union[bytes, None]) -> None:
		"""
		Called when an IAC + DONT + option is received.

		Args:
			option: The received option.
		"""
		if option is None:
			raise AssertionError("Option must not be None in this context.")
		state = self.getOptionState(option)
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
			self.on_disableLocal(option)
			self._wont(option)
		elif state.us.enabled and state.us.negotiating:
			# Peer acknowledged our notice that we will disable an option.
			state.us.enabled = False
			state.us.negotiating = False
			self.on_disableLocal(option)

	def on_unhandledCommand(self, command: bytes, option: Union[bytes, None]) -> None:
		return super().on_unhandledCommand(command, option)

	def on_unhandledSubnegotiation(self, option: bytes, data: bytes) -> None:
		return super().on_unhandledSubnegotiation(option, data)

	def on_enableLocal(self, option: bytes) -> bool:
		return super().on_enableLocal(option)

	def on_disableLocal(self, option: bytes) -> None:
		return super().on_disableLocal(option)

	def on_enableRemote(self, option: bytes) -> bool:
		return super().on_enableRemote(option)

	def on_disableRemote(self, option: bytes) -> None:
		return super().on_disableRemote(option)

	def on_optionEnabled(self, option: bytes) -> None:
		return super().on_optionEnabled(option)
