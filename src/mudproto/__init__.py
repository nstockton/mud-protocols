# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Future Modules:
from __future__ import annotations

# Built-in Modules:
from contextlib import suppress
from typing import TYPE_CHECKING


__version__: str = "0.0.0"
if not TYPE_CHECKING:
	with suppress(ImportError):
		from ._version import __version__


__all__: list[str] = [
	"__version__",
]
