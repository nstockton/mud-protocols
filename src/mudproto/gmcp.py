"""
Generic MUD Communication Protocol.
"""


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import json
import logging
import re
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, Optional, Union

# Local Modules:
from .telnet import BaseTelnetProtocol, TelnetProtocol
from .telnet_constants import GMCP


GMCP_MESSAGE_REGEX: re.Pattern[bytes] = re.compile(rb"^\s*(?P<package>[\w.-]+)\s*(?P<value>.*?)\s*$")


logger: logging.Logger = logging.getLogger(__name__)


if TYPE_CHECKING:  # pragma: no cover
	Base = TelnetProtocol
else:  # pragma: no cover
	Base = BaseTelnetProtocol


class GMCPMixIn(Base):
	"""
	A GMCP mix in class for the Telnet protocol.
	"""

	def __init__(
		self,
		*args: Any,
		gmcpClientInfo: Optional[tuple[str, str]] = None,
		**kwargs: Any,
	) -> None:
		"""
		Defines the constructor for the mixin.

		Args:
			*args: Positional arguments to be passed to the parent constructor.
			gmcpClientInfo: A tuple containing client name and version to send peer during GMCP Hello.
			**kwargs: Key-word only arguments to be passed to the parent constructor.
		"""
		super().__init__(*args, **kwargs)
		self._gmcpClientInfo: dict[str, str] = {}
		if gmcpClientInfo is not None:
			client, version = gmcpClientInfo
			self._gmcpClientInfo["client"] = client
			self._gmcpClientInfo["version"] = version
		self._isGMCPInitialized: bool = False  # Is set to True after GMCP Hello.
		self._gmcpSupportedPackages: dict[str, int] = {}  # Keys are lower case.
		self.subnegotiationMap[GMCP] = self.on_gmcp

	@property
	def isGMCPInitialized(self) -> bool:
		"""True if GMCP Hello was negotiated, False otherwise."""
		return self._isGMCPInitialized

	def gmcpSend(self, package: str, value: Any, *, isSerialized: bool = False) -> None:
		"""
		Sends a GMCP negotiation to the peer.

		Args:
			package: The GMCP package name.
			value: the value to set.
			isSerialized: True if value has already been serialized to JSON, False otherwise.
		"""
		# According to the page at https://gammon.com.au/gmcp
		# """
		# Although JSON allows for multiple Unicode encodings, for GMCP all text within
		# the quotes is encoded in UTF-8 format. We do not recommend the \uXXXX notation
		# for Unicode characters, as there was some debate about their representation.
		# """
		# Because of this, we should pass ensure_ascii=False to json.dumps to prevent unicode escaping.
		packageAsBytes: bytes = bytes(package, "utf-8")
		jsonAsBytes: bytes
		if not isSerialized:
			jsonStr: str = json.dumps(value, ensure_ascii=False, indent=None, separators=(", ", ": "))
			jsonAsBytes = bytes(jsonStr, "utf-8")
		elif isinstance(value, str):
			jsonAsBytes = bytes(value, "utf-8")
		else:
			jsonAsBytes = bytes(value)
		payload: bytes = b"%b %b" % (packageAsBytes, jsonAsBytes)
		logger.debug(f"Sending GMCP payload: {payload!r}.")
		self.requestNegotiation(GMCP, payload)

	def gmcpHello(self) -> None:
		"""
		Sends a GMCP Hello to the peer.
		"""
		logger.debug("Sending GMCP Hello.")
		self.gmcpSend("Core.Hello", self._gmcpClientInfo)

	def gmcpSetPackages(self, packages: Mapping[str, int]) -> None:
		"""
		Tells the peer about supported packages, after clearing any existing list.

		Args:
			packages: The supported packages.
		"""
		self._gmcpSupportedPackages.clear()
		self._gmcpSupportedPackages.update(
			{package.lower(): version for package, version in packages.items()}
		)
		values: tuple[str, ...] = tuple(f"{package} {version}" for package, version in packages.items())
		self.gmcpSend("Core.Supports.Set", values)

	def gmcpAddPackages(self, packages: Mapping[str, int]) -> None:
		"""
		Tells the peer to append supported packages to an existing list.

		Args:
			packages: The supported packages.
		"""
		self._gmcpSupportedPackages.update(
			{package.lower(): version for package, version in packages.items()}
		)
		values: tuple[str, ...] = tuple(f"{package} {version}" for package, version in packages.items())
		self.gmcpSend("Core.Supports.Add", values)

	def gmcpRemovePackages(self, packages: Iterable[str]) -> None:
		"""
		Tells the peer to remove supported packages.

		Args:
			packages: The supported packages.
		"""
		values: list[str] = []
		for package in packages:
			if package.lower() not in self._gmcpSupportedPackages:
				logger.warning(f"Tried to remove nonexisting package: {package!r}")
			else:
				self._gmcpSupportedPackages.pop(package.lower())
				values.append(package)
		if values:
			self.gmcpSend("Core.Supports.Remove", tuple(values))

	def on_gmcpMessage(self, package: str, value: bytes) -> None:
		"""
		Called when a GMCP message is received from peer.

		This method should be overridden.

		Args:
			package: The GMCP package name in lower case.
			value: The package value.
		"""

	def on_gmcp(self, data: bytes) -> None:
		"""
		Called when a GMCP subnegotiation is received.

		Args:
			data: The payload.
		"""
		match: Union[re.Match[bytes], None] = GMCP_MESSAGE_REGEX.search(data)
		if match is None:
			logger.warning(f"Unknown GMCP negotiation from peer: {data!r}")
			return None
		package, value = match.groups()
		logger.debug(f"Received from Peer: GMCP Package: {package!r}, value: {value!r}.")
		packageAsStr: str = str(package, "utf-8").lower()
		if self.isServer:
			if packageAsStr == "core.hello":
				if self._isGMCPInitialized:  # GMCP Hello was already received.
					logger.warning("Received GMCP Hello from peer after initial Hello was already received.")
				else:  # Initial GMCP Hello.
					logger.debug("Received initial GMCP Hello from peer.")
					gmcpClientInfo: dict[str, str] = json.loads(value)
					self._gmcpClientInfo["client"] = gmcpClientInfo.get("client", "unknown")
					self._gmcpClientInfo["version"] = gmcpClientInfo.get("version", "0.0")
					self._isGMCPInitialized = True
				return None
			elif not self._isGMCPInitialized:  # Received GMCP before initial Hello.
				logger.warning("Received GMCP message from peer before initial Hello.")
		self.on_gmcpMessage(packageAsStr, value)

	def on_connectionMade(self) -> None:
		super().on_connectionMade()
		if self.isServer:
			logger.debug("We offer to enable GMCP.")
			self.will(GMCP)

	def on_enableLocal(self, option: bytes) -> bool:
		if option == GMCP:
			logger.debug("We enable GMCP.")
			return True
		return bool(super().on_enableLocal(option))  # pragma: no cover

	def on_disableLocal(self, option: bytes) -> None:
		if option == GMCP:
			logger.debug("We disable GMCP.")
			return None
		super().on_disableLocal(option)  # pragma: no cover

	def on_enableRemote(self, option: bytes) -> bool:
		if option == GMCP:
			logger.debug("Peer enables GMCP.")
			return True
		return bool(super().on_enableRemote(option))  # pragma: no cover

	def on_disableRemote(self, option: bytes) -> None:
		if option == GMCP:
			logger.debug("Peer disables GMCP.")
			return None
		super().on_disableRemote(option)  # pragma: no cover

	def on_optionEnabled(self, option: bytes) -> None:
		if option == GMCP:
			if self.isClient:
				# Hello should be the first thing sent before further GMCP negotiation.
				self.gmcpHello()
				self._isGMCPInitialized = True
			return None
		super().on_optionEnabled(option)  # pragma: no cover
