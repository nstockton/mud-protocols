"""
Mume Remote Editing Protocol.
"""


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
from enum import Enum, auto
from typing import Any, Union

# Local Modules:
from .connection import ConnectionInterface
from .telnet_constants import CR, LF
from .typedef import MPI_COMMAND_MAP_TYPE


MPI_INIT: bytes = b"~$#E"


logger: logging.Logger = logging.getLogger(__name__)


class MPIState(Enum):
	"""
	Valid states for the state machine.
	"""

	DATA = auto()
	NEWLINE = auto()
	INIT = auto()
	COMMAND = auto()
	LENGTH = auto()
	BODY = auto()


class MPIProtocol(ConnectionInterface):
	"""
	Implements support for the Mume remote editing protocol.

	Attributes:
		commandMap: A mapping of bytes to callables.
		editor: The program to use for editing received text.
		pager: The program to use for viewing received read-only text.
	"""

	def __init__(self, *args: Any, outputFormat: str, **kwargs: Any) -> None:
		self.outputFormat: str = outputFormat
		super().__init__(*args, **kwargs)
		self.state: MPIState = MPIState.DATA
		"""The state of the state machine."""
		self._MPIBuffer: bytearray = bytearray()
		self._MPIThreads: list[threading.Thread] = []
		self.commandMap: MPI_COMMAND_MAP_TYPE = {
			b"E": self.edit,
			b"V": self.view,
		}
		editors: dict[str, str] = {
			"win32": "notepad.exe",
		}
		pagers: dict[str, str] = {
			"win32": "notepad.exe",
		}
		defaultEditor: str = editors.get(sys.platform, "nano")
		defaultPager: str = pagers.get(sys.platform, "less")
		editor: Union[str, None] = shutil.which(os.getenv("VISUAL", "") or os.getenv("EDITOR", defaultEditor))
		pager: Union[str, None] = shutil.which(os.getenv("PAGER", defaultPager))
		self._isWordWrapping: bool = False
		if editor is None:  # pragma: no cover
			raise ValueError("MPI editor executable not found.")
		if pager is None:  # pragma: no cover
			raise ValueError("MPI pager executable not found.")
		self.editor: str = editor
		self.pager: str = pager

	@property
	def isWordWrapping(self) -> bool:
		"""Specifies whether text should be word wrapped during editing or not."""
		return self._isWordWrapping

	@isWordWrapping.setter
	def isWordWrapping(self, value: bool) -> None:
		self._isWordWrapping = value

	def edit(self, data: bytes) -> None:
		"""
		Edits text using the program defined in `editor`.

		Args:
			data: Received data from Mume, containing the session, description, and body of the text.
		"""
		# Use windows line endings when editing the file.
		newline: str = "\r\n"
		# The MUME server sends the MPI data encoded in Latin-1.
		session, description, body = str(data, "latin-1")[1:].split("\n", 2)
		with tempfile.NamedTemporaryFile(
			"w", encoding="utf-8", newline=newline, prefix="mume_editing_", suffix=".txt", delete=False
		) as tempFileObj:
			fileName = tempFileObj.name
			tempFileObj.write(body)
		lastModified = os.path.getmtime(fileName)
		if self.outputFormat == "tintin":
			print(f"MPICOMMAND:{self.editor} {fileName}:MPICOMMAND")
			input("Continue:")
		else:
			subprocess.run((*self.editor.split(), fileName))
		response: str
		if os.path.getmtime(fileName) == lastModified:
			# The user closed the text editor without saving. Cancel the editing session.
			response = f"C{session}\n"
		else:
			if self.isWordWrapping:
				with open(fileName, "r", encoding="utf-8", newline=newline) as fileObj:
					text: str = fileObj.read()
				text = self.postprocess(text)
				with open(fileName, "w", encoding="utf-8", newline=newline) as fileObj:
					fileObj.write(text)
			with open(fileName, "r", encoding="utf-8", newline=newline) as fileObj:
				response = f"E{session}\n{fileObj.read().strip()}\n"
		os.remove(fileName)
		# MUME requires that output body be encoded in Latin-1 with Unix line endings.
		output: bytes = bytes(response, "latin-1").replace(CR, b"")
		self.write(MPI_INIT + b"E" + b"%d" % len(output) + LF + output)

	def view(self, data: bytes) -> None:
		"""
		Views text using the program defined in `pager`.

		Args:
			data: Received data from Mume, containing the text.
		"""
		# Use windows line endings when viewing the file.
		newline: str = "\r\n"
		# The MUME server sends the MPI data encoded in Latin-1.
		body: str = str(data, "latin-1")
		with tempfile.NamedTemporaryFile(
			"w", encoding="utf-8", newline=newline, prefix="mume_viewing_", suffix=".txt", delete=False
		) as fileObj:
			fileName = fileObj.name
			fileObj.write(body)
		if self.outputFormat == "tintin":
			print(f"MPICOMMAND:{self.pager} {fileName}:MPICOMMAND")
		else:
			subprocess.run((*self.pager.split(), fileName))
			os.remove(fileName)

	def on_dataReceived(self, data: bytes) -> None:  # NOQA: C901
		appDataBuffer: bytearray = bytearray()
		while data:
			if self.state is MPIState.DATA:
				appData, separator, data = data.partition(LF)
				appDataBuffer.extend(appData + separator)
				if separator:
					self.state = MPIState.NEWLINE
			elif self.state is MPIState.NEWLINE:
				if MPI_INIT.startswith(data[: len(MPI_INIT)]):
					# Data starts with some or all of the MPI_INIT sequence.
					self.state = MPIState.INIT
				else:
					self.state = MPIState.DATA
			elif self.state is MPIState.INIT:
				remaining = len(MPI_INIT) - len(self._MPIBuffer)
				self._MPIBuffer.extend(data[:remaining])
				data = data[remaining:]
				if self._MPIBuffer == MPI_INIT:
					# The final byte in the MPI_INIT sequence has been reached.
					if appDataBuffer:
						super().on_dataReceived(bytes(appDataBuffer))
						appDataBuffer.clear()
					self._MPIBuffer.clear()
					self.state = MPIState.COMMAND
				elif not MPI_INIT.startswith(self._MPIBuffer):
					# The Bytes in the buffer are not part of an MPI init sequence.
					data = bytes(self._MPIBuffer) + data
					self._MPIBuffer.clear()
					self.state = MPIState.DATA
			elif self.state is MPIState.COMMAND:
				# The MPI command is a single byte.
				self._command, data = data[:1], data[1:]
				self.state = MPIState.LENGTH
			elif self.state is MPIState.LENGTH:
				length, separator, data = data.partition(LF)
				self._MPIBuffer.extend(length)
				if not self._MPIBuffer.isdigit():
					logger.warning(f"Invalid data {self._MPIBuffer!r} in MPI length. Digit expected.")
					data = MPI_INIT + self._command + bytes(self._MPIBuffer) + separator + data
					del self._command
					self._MPIBuffer.clear()
					self.state = MPIState.DATA
				elif separator:
					# The buffer contains the length of subsequent bytes to be received.
					self._length = int(self._MPIBuffer)
					self._MPIBuffer.clear()
					self.state = MPIState.BODY
			elif self.state is MPIState.BODY:
				remaining = self._length - len(self._MPIBuffer)
				self._MPIBuffer.extend(data[:remaining])
				data = data[remaining:]
				if len(self._MPIBuffer) == self._length:
					# The final byte in the expected MPI data has been received.
					self.on_command(self._command, bytes(self._MPIBuffer))
					del self._command
					del self._length
					self._MPIBuffer.clear()
					self.state = MPIState.DATA
		if appDataBuffer:
			super().on_dataReceived(bytes(appDataBuffer))

	def on_command(self, command: bytes, data: bytes) -> None:
		"""
		Called when an MPI command is received.

		Args:
			command: The MPI command, consisting of a single byte.
			data: The payload.
		"""
		if command not in self.commandMap:
			logger.warning(f"Invalid MPI command {command!r}.")
			self.on_unhandledCommand(command, data)
		elif self.commandMap[command] is not None:
			thread = threading.Thread(target=self.commandMap[command], args=(data,), daemon=True)
			self._MPIThreads.append(thread)
			thread.start()

	def on_connectionMade(self) -> None:
		# Identify for Mume Remote Editing.
		self.write(MPI_INIT + b"I" + LF)

	def on_connectionLost(self) -> None:
		# Clean up any active editing sessions.
		for thread in self._MPIThreads:
			thread.join()
		self._MPIThreads.clear()

	def on_unhandledCommand(self, command: bytes, data: bytes) -> None:
		"""
		Called for commands for which no handler is installed.

		Args:
			command: The MPI command, consisting of a single byte.
			data: The payload.
		"""
		super().on_dataReceived(MPI_INIT + command + b"%d" % len(data) + LF + data)

	def postprocess(self, text: str) -> str:
		"""
		Reformats text before it is sent to the game when wordwrapping is enabled.

		Args:
			text: The text to be processed.

		Returns:
			The text with formatting applied.
		"""
		paragraphs: list[str] = self.getParagraphs(text)
		for i, paragraph in enumerate(paragraphs):
			if not self.isComment(paragraph):
				paragraph = self.collapseSpaces(paragraph)
				paragraph = self.capitalise(paragraph)
				paragraph = self.wordwrap(paragraph)
				paragraphs[i] = paragraph
		return "\n".join(paragraphs)

	def getParagraphs(self, text: str) -> list[str]:
		"""
		Extracts paragraphs from a string.

		Args:
			text: The text to analyze.

		Returns:
			The extracted paragraphs.
		"""
		lines: list[str] = text.splitlines()
		lineno: int = 0
		while lineno < len(lines):
			if self.isComment(lines[lineno]):
				if lineno > 0:
					lines[lineno] = "\0" + lines[lineno]
				if lineno + 1 < len(lines):
					lines[lineno] += "\0"
			lineno += 1
		text = "\n".join(lines)
		text = re.sub(r"\0\n\0?", "\0", text)
		lines = [line.rstrip() for line in text.split("\0")]
		return [line for line in lines if line]

	def isComment(self, line: str) -> bool:
		"""
		Determines whether a line is a comment.

		Args:
			line: The line to analyze.

		Returns:
			True if the line is a comment, False otherwise.
		"""
		return line.lstrip().startswith("#")

	def collapseSpaces(self, text: str) -> str:
		"""
		Collapses all consecutive space and tab characters of a string to a single space character.

		Args:
			text: The text to perform the operation on.

		Returns:
			The text with consecutive space and tab characters collapsed.
		"""
		# replace consecutive newlines with a null placeholder
		text = text.replace("\n", "\0")
		# collapse all runs of whitespace into a single space
		text = re.sub(r"[ \t]+", " ", text.strip())
		# reinsert consecutive newlines
		return text.replace("\0", "\n")

	def capitalise(self, text: str) -> str:
		"""
		Capitalizes each sentence in a string.

		Args:
			text: The text to perform sentence capitalization on.

		Returns:
			The text after each sentence has been capitalized.
		"""
		return ". ".join(sentence.capitalize() for sentence in text.split(". "))

	def wordwrap(self, text: str) -> str:
		"""
		Wordwraps text using module-specific settings.

		Args:
			text: The text to be wordwrapped.

		Returns:
			The text with wordwrapping applied.
		"""
		return textwrap.fill(
			text, width=79, drop_whitespace=True, break_long_words=False, break_on_hyphens=False
		)
