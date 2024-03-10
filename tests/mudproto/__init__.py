# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# Future Modules:
from __future__ import annotations


if "unittest.util" in __import__("sys").modules:
	# Show full diff in self.assertEqual.
	# https://stackoverflow.com/questions/43842675/how-to-prevent-truncating-of-string-in-unit-test-python
	__import__("sys").modules["unittest.util"]._MAX_LENGTH = 1000000000
