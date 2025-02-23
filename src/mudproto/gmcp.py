# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Generic MUD Communication Protocol."""

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import json
import logging
import re
from collections.abc import Iterable, Mapping
from typing import Any, Optional

# Third-party Modules:
from knickknacks.typedef import ReBytesMatchType, ReBytesPatternType

# Local Modules:
from .telnet import TelnetInterface
from .telnet_constants import GMCP
from .typedef import GMCPClientInfoType


GMCP_MESSAGE_REGEX: ReBytesPatternType = re.compile(rb"^\s*(?P<package>[\w.-]+)\s*(?P<value>.*?)\s*$")


logger: logging.Logger = logging.getLogger(__name__)


class GMCPMixIn(TelnetInterface):
	"""A GMCP mix in class for the Telnet protocol."""

	def __init__(
		self,
		*args: Any,
		gmcp_client_info: Optional[GMCPClientInfoType] = None,
		**kwargs: Any,
	) -> None:
		"""
		Defines the constructor.

		Args:
			*args: Positional arguments to be passed to the parent constructor.
			gmcp_client_info: A tuple containing client name and version to send peer during GMCP Hello.
			**kwargs: Key-word only arguments to be passed to the parent constructor.
		"""
		super().__init__(*args, **kwargs)
		self._gmcp_client_info: dict[str, str] = {}
		if gmcp_client_info is not None:
			client, version = gmcp_client_info
			self._gmcp_client_info["client"] = client
			self._gmcp_client_info["version"] = version
		self._is_gmcp_initialized: bool = False  # Is set to True after GMCP Hello.
		self._gmcp_supported_packages: dict[str, int] = {}  # Keys are lower case.
		self.subnegotiation_map[GMCP] = self.on_gmcp

	@property
	def is_gmcp_initialized(self) -> bool:
		"""True if GMCP Hello was negotiated, False otherwise."""
		return self._is_gmcp_initialized

	def gmcp_send(self, package: str, value: Any, *, is_serialized: bool = False) -> None:
		"""
		Sends a GMCP negotiation to the peer.

		Args:
			package: The GMCP package name.
			value: the value to set.
			is_serialized: True if value has already been serialized to JSON, False otherwise.
		"""
		# According to the page at gammon.com.au/gmcp
		# Although JSON allows for multiple Unicode encodings, for GMCP all text within
		# the quotes is encoded in UTF-8 format. We do not recommend the \uXXXX notation
		# for Unicode characters, as there was some debate about their representation.
		# Because of this, we should turn off ensure_ascii when dumping to prevent unicode escaping.
		package_as_bytes: bytes = bytes(package, "utf-8")
		json_as_bytes: bytes
		if not is_serialized:
			json_str: str = json.dumps(value, ensure_ascii=False, indent=None, separators=(", ", ": "))
			json_as_bytes = bytes(json_str, "utf-8")
		elif isinstance(value, str):
			json_as_bytes = bytes(value, "utf-8")
		else:
			json_as_bytes = bytes(value)
		payload: bytes = b"%b %b" % (package_as_bytes, json_as_bytes)
		logger.debug(f"Sending GMCP payload: {payload!r}.")
		self.request_negotiation(GMCP, payload)

	def gmcp_hello(self) -> None:
		"""Sends a GMCP Hello to the peer."""
		logger.debug("Sending GMCP Hello.")
		self.gmcp_send("Core.Hello", self._gmcp_client_info)

	def gmcp_set_packages(self, packages: Mapping[str, int]) -> None:
		"""
		Tells the peer about supported packages, after clearing any existing list.

		Args:
			packages: The supported packages.
		"""
		self._gmcp_supported_packages.clear()
		self._gmcp_supported_packages.update(
			{package.lower(): version for package, version in packages.items()}
		)
		values: tuple[str, ...] = tuple(f"{package} {version}" for package, version in packages.items())
		self.gmcp_send("Core.Supports.Set", values)

	def gmcp_add_packages(self, packages: Mapping[str, int]) -> None:
		"""
		Tells the peer to append supported packages to an existing list.

		Args:
			packages: The supported packages.
		"""
		self._gmcp_supported_packages.update(
			{package.lower(): version for package, version in packages.items()}
		)
		values: tuple[str, ...] = tuple(f"{package} {version}" for package, version in packages.items())
		self.gmcp_send("Core.Supports.Add", values)

	def gmcp_remove_packages(self, packages: Iterable[str]) -> None:
		"""
		Tells the peer to remove supported packages.

		Args:
			packages: The supported packages.
		"""
		values: list[str] = []
		for package in packages:
			if package.lower() not in self._gmcp_supported_packages:
				logger.warning(f"Tried to remove nonexisting package: {package!r}")
			else:
				self._gmcp_supported_packages.pop(package.lower())
				values.append(package)
		if values:
			self.gmcp_send("Core.Supports.Remove", tuple(values))

	def on_gmcp_message(self, package: str, value: bytes) -> None:
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
		match: ReBytesMatchType = GMCP_MESSAGE_REGEX.search(data)
		if match is None:
			logger.warning(f"Unknown GMCP negotiation from peer: {data!r}")
			return
		package, value = match.groups()
		logger.debug(f"Received from Peer: GMCP Package: {package!r}, value: {value!r}.")
		package_as_str: str = str(package, "utf-8").lower()
		if self.is_server:
			if package_as_str == "core.hello":
				if self._is_gmcp_initialized:  # GMCP Hello was already received.
					logger.warning("Received GMCP Hello from peer after initial Hello was already received.")
				else:  # Initial GMCP Hello.
					logger.debug("Received initial GMCP Hello from peer.")
					gmcp_client_info: dict[str, str] = json.loads(value)
					self._gmcp_client_info["client"] = gmcp_client_info.get("client", "unknown")
					self._gmcp_client_info["version"] = gmcp_client_info.get("version", "0.0")
					self._is_gmcp_initialized = True
				return
			if not self._is_gmcp_initialized:  # Received GMCP before initial Hello.
				logger.warning("Received GMCP message from peer before initial Hello.")
		self.on_gmcp_message(package_as_str, value)

	def on_connection_made(self) -> None:  # NOQA: D102
		super().on_connection_made()  # type: ignore[safe-super]
		if self.is_server:
			logger.debug("We offer to enable GMCP.")
			self.will(GMCP)

	def on_enable_local(self, option: bytes) -> bool:  # NOQA: D102
		if option == GMCP:
			logger.debug("We enable GMCP.")
			return True
		return bool(super().on_enable_local(option))  # pragma: no cover

	def on_disable_local(self, option: bytes) -> None:  # NOQA: D102
		if option == GMCP:
			logger.debug("We disable GMCP.")
			return
		super().on_disable_local(option)  # type: ignore[safe-super]  # pragma: no cover

	def on_enable_remote(self, option: bytes) -> bool:  # NOQA: D102
		if option == GMCP:
			logger.debug("Peer enables GMCP.")
			return True
		return bool(super().on_enable_remote(option))  # pragma: no cover

	def on_disable_remote(self, option: bytes) -> None:  # NOQA: D102
		if option == GMCP:
			logger.debug("Peer disables GMCP.")
			return
		super().on_disable_remote(option)  # type: ignore[safe-super]  # pragma: no cover

	def on_option_enabled(self, option: bytes) -> None:  # NOQA: D102
		if option == GMCP:
			if self.is_client:
				# Hello should be the first thing sent before further GMCP negotiation.
				self.gmcp_hello()
				self._is_gmcp_initialized = True
			return
		super().on_option_enabled(option)  # type: ignore[safe-super]  # pragma: no cover
