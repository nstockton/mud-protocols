# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Shared type definitions."""

# Future Modules:
from __future__ import annotations

# Built-in Modules:
from collections.abc import Callable
from typing import Union

# Third-party Modules:
from knickknacks.typedef import TypeAlias


ConnectionReceiverType: TypeAlias = Callable[[bytes], None]
ConnectionWriterType: TypeAlias = Callable[[bytes], None]
GMCPClientInfoType: TypeAlias = tuple[str, str]
MPICommandMapValueType: TypeAlias = Callable[[bytes], None]
MPICommandMapType: TypeAlias = dict[bytes, MPICommandMapValueType]
TelnetCommandMapValueType: TypeAlias = Callable[[Union[bytes, None]], None]
TelnetCommandMapType: TypeAlias = dict[bytes, TelnetCommandMapValueType]
TelnetSubnegotiationMapValueType: TypeAlias = Callable[[bytes], None]
TelnetSubnegotiationMapType: TypeAlias = dict[bytes, TelnetSubnegotiationMapValueType]


__all__: list[str] = [
	"ConnectionReceiverType",
	"ConnectionWriterType",
	"GMCPClientInfoType",
	"MPICommandMapType",
	"MPICommandMapValueType",
	"TelnetCommandMapType",
	"TelnetCommandMapValueType",
	"TelnetSubnegotiationMapType",
	"TelnetSubnegotiationMapValueType",
]
