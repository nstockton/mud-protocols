# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations

# Built-in Modules:
import sys
from typing import Dict, Tuple, Union


if sys.version_info < (3, 10):  # pragma: no cover
	from typing_extensions import TypeAlias
else:  # pragma: no cover
	from typing import TypeAlias

if sys.version_info < (3, 9):  # pragma: no cover
	from typing import Callable, Match, Pattern
else:  # pragma: no cover
	from collections.abc import Callable
	from re import Match, Pattern


REGEX_MATCH: TypeAlias = Union[Match[str], None]
REGEX_PATTERN: TypeAlias = Pattern[str]
REGEX_BYTES_MATCH: TypeAlias = Union[Match[bytes], None]
REGEX_BYTES_PATTERN: TypeAlias = Pattern[bytes]
PROTOCOL_WRITER_TYPE: TypeAlias = Callable[[bytes], None]
PROTOCOL_RECEIVER_TYPE: TypeAlias = Callable[[bytes], None]
TELNET_COMMAND_MAP_VALUE_TYPE: TypeAlias = Callable[[Union[bytes, None]], None]
TELNET_COMMAND_MAP_TYPE: TypeAlias = Dict[bytes, TELNET_COMMAND_MAP_VALUE_TYPE]
TELNET_SUBNEGOTIATION_MAP_VALUE_TYPE: TypeAlias = Callable[[bytes], None]
TELNET_SUBNEGOTIATION_MAP_TYPE: TypeAlias = Dict[bytes, TELNET_SUBNEGOTIATION_MAP_VALUE_TYPE]
MPI_COMMAND_MAP_VALUE_TYPE: TypeAlias = Callable[[bytes], None]
MPI_COMMAND_MAP_TYPE: TypeAlias = Dict[bytes, MPI_COMMAND_MAP_VALUE_TYPE]
GMCP_CLIENT_INFO_TYPE: TypeAlias = Tuple[str, str]
