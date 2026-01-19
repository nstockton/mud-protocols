# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mume Remote Editing Protocol."""

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import logging
import os
import re
import shutil
import subprocess  # NOQA: S404
import sys
import tempfile
import textwrap
import threading
from enum import Enum, auto
from pathlib import Path
from typing import Any, Union

# Local Modules:
from .connection import ConnectionInterface
from .telnet_constants import CR, LF
from .typedef import MPICommandMapType


MPI_INIT: bytes = b"~$#E"


logger: logging.Logger = logging.getLogger(__name__)


class MPIState(Enum):
	"""Valid states for the state machine."""

	DATA = auto()
	NEWLINE = auto()
	INIT = auto()
	COMMAND = auto()
	LENGTH = auto()
	BODY = auto()


class MPIProtocol(ConnectionInterface):
	"""Implements support for the Mume remote editing protocol."""

	def __init__(self, *args: Any, output_format: str, **kwargs: Any) -> None:
		"""
		Defines the constructor.

		Args:
			*args: Positional arguments to be passed to the parent constructor.
			output_format: The output format to be used.
			**kwargs: Key-word only arguments to be passed to the parent constructor.

		Raises:
			ValueError: Editor or pager not found.
		"""
		self.output_format: str = output_format
		super().__init__(*args, **kwargs)
		self.state: MPIState = MPIState.DATA
		"""The state of the state machine."""
		self._mpi_buffer: bytearray = bytearray()
		self._mpi_threads: list[threading.Thread] = []
		self.command_map: MPICommandMapType = {
			b"E": self.edit,
			b"V": self.view,
		}
		"""A mapping of bytes to callables."""
		editors: dict[str, str] = {
			"win32": "notepad.exe",
		}
		pagers: dict[str, str] = {
			"win32": "notepad.exe",
		}
		default_editor: str = editors.get(sys.platform, "nano")
		default_pager: str = pagers.get(sys.platform, "less")
		editor: Union[str, None] = shutil.which(
			os.getenv("VISUAL", "") or os.getenv("EDITOR", default_editor)
		)
		pager: Union[str, None] = shutil.which(os.getenv("PAGER", default_pager))
		self._is_word_wrapping: bool = False
		if editor is None:  # pragma: no cover
			raise ValueError("MPI editor executable not found.")
		if pager is None:  # pragma: no cover
			raise ValueError("MPI pager executable not found.")
		self.editor: str = editor
		"""The program to use for editing received text."""
		self.pager: str = pager
		"""The program to use for viewing received read-only text."""

	@property
	def is_word_wrapping(self) -> bool:
		"""Specifies whether text should be word wrapped during editing or not."""
		return self._is_word_wrapping

	@is_word_wrapping.setter
	def is_word_wrapping(self, value: bool) -> None:
		self._is_word_wrapping = value

	def edit(self, data: bytes) -> None:
		"""
		Edits text using the program defined in `editor`.

		Args:
			data: Received data from Mume, containing the session, description, and body of the text.
		"""
		# Use windows line endings when editing the file.
		newline: str = "\r\n"
		# The MUME server sends the MPI data encoded in Latin-1.
		session, _, body = str(data, "latin-1")[1:].split("\n", 2)
		with tempfile.NamedTemporaryFile(
			"w", encoding="utf-8", newline=newline, prefix="mume_editing_", suffix=".txt", delete=False
		) as temp_file_obj:
			file_path = Path(temp_file_obj.name)
			temp_file_obj.write(body)
		last_modified = file_path.stat().st_mtime
		if self.output_format == "tintin":
			print(f"MPICOMMAND:{self.editor} {file_path}:MPICOMMAND")
			input("Continue:")
		else:
			subprocess.run((*self.editor.split(), str(file_path)))  # NOQA: PLW1510, S603
		response: str
		if file_path.stat().st_mtime == last_modified:
			# The user closed the text editor without saving. Cancel the editing session.
			response = f"C{session}\n"
		else:
			if self.is_word_wrapping:
				with file_path.open(encoding="utf-8", newline=newline) as file_obj:
					text: str = file_obj.read()
				text = self.postprocess(text)
				with file_path.open("w", encoding="utf-8", newline=newline) as file_obj:
					file_obj.write(text)
			with file_path.open(encoding="utf-8", newline=newline) as file_obj:
				response = f"E{session}\n{file_obj.read().strip()}\n"
		file_path.unlink(missing_ok=True)
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
		) as file_obj:
			file_path = Path(file_obj.name)
			file_obj.write(body)
		if self.output_format == "tintin":
			print(f"MPICOMMAND:{self.pager} {file_path}:MPICOMMAND")
		else:
			subprocess.run((*self.pager.split(), str(file_path)))  # NOQA: PLW1510, S603
			file_path.unlink(missing_ok=True)

	def on_data_received(self, data: bytes) -> None:  # NOQA: C901, D102, PLR0912, PLR0915
		app_data_buffer: bytearray = bytearray()
		while data:
			if self.state is MPIState.DATA:
				app_data, separator, data = data.partition(LF)
				app_data_buffer.extend(app_data + separator)
				if separator:
					self.state = MPIState.NEWLINE
			elif self.state is MPIState.NEWLINE:
				if MPI_INIT.startswith(data[: len(MPI_INIT)]):
					# Data starts with some or all of the MPI_INIT sequence.
					self.state = MPIState.INIT
				else:
					self.state = MPIState.DATA
			elif self.state is MPIState.INIT:
				remaining = len(MPI_INIT) - len(self._mpi_buffer)
				self._mpi_buffer.extend(data[:remaining])
				data = data[remaining:]
				if self._mpi_buffer == MPI_INIT:
					# The final byte in the MPI_INIT sequence has been reached.
					if app_data_buffer:
						super().on_data_received(bytes(app_data_buffer))
						app_data_buffer.clear()
					self._mpi_buffer.clear()
					self.state = MPIState.COMMAND
				elif not MPI_INIT.startswith(self._mpi_buffer):
					# The Bytes in the buffer are not part of an MPI init sequence.
					data = bytes(self._mpi_buffer) + data
					self._mpi_buffer.clear()
					self.state = MPIState.DATA
			elif self.state is MPIState.COMMAND:
				# The MPI command is a single byte.
				self._command, data = data[:1], data[1:]
				self.state = MPIState.LENGTH
			elif self.state is MPIState.LENGTH:
				length, separator, data = data.partition(LF)
				self._mpi_buffer.extend(length)
				if not self._mpi_buffer.isdigit():
					logger.warning(f"Invalid data {self._mpi_buffer!r} in MPI length. Digit expected.")
					data = MPI_INIT + self._command + bytes(self._mpi_buffer) + separator + data
					del self._command
					self._mpi_buffer.clear()
					self.state = MPIState.DATA
				elif separator:
					# The buffer contains the length of subsequent bytes to be received.
					self._length = int(self._mpi_buffer)
					self._mpi_buffer.clear()
					self.state = MPIState.BODY
			elif self.state is MPIState.BODY:
				remaining = self._length - len(self._mpi_buffer)
				self._mpi_buffer.extend(data[:remaining])
				data = data[remaining:]
				if len(self._mpi_buffer) == self._length:
					# The final byte in the expected MPI data has been received.
					self.on_command(self._command, bytes(self._mpi_buffer))
					del self._command
					del self._length
					self._mpi_buffer.clear()
					self.state = MPIState.DATA
		if app_data_buffer:
			super().on_data_received(bytes(app_data_buffer))

	def on_command(self, command: bytes, data: bytes) -> None:
		"""
		Called when an MPI command is received.

		Args:
			command: The MPI command, consisting of a single byte.
			data: The payload.
		"""
		if command not in self.command_map:
			logger.warning(f"Invalid MPI command {command!r}.")
			self.on_unhandled_command(command, data)
		elif self.command_map[command] is not None:
			thread = threading.Thread(target=self.command_map[command], args=(data,), daemon=True)
			self._mpi_threads.append(thread)
			thread.start()

	def on_connection_made(self) -> None:  # NOQA: D102
		# Identify for Mume Remote Editing.
		self.write(MPI_INIT + b"I" + LF)

	def on_connection_lost(self) -> None:  # NOQA: D102
		# Clean up any active editing sessions.
		for thread in self._mpi_threads:
			thread.join()
		self._mpi_threads.clear()

	def on_unhandled_command(self, command: bytes, data: bytes) -> None:
		"""
		Called for commands for which no handler is installed.

		Args:
			command: The MPI command, consisting of a single byte.
			data: The payload.
		"""
		super().on_data_received(MPI_INIT + command + b"%d" % len(data) + LF + data)

	def postprocess(self, text: str) -> str:
		"""
		Reformats text before it is sent to the game when wordwrapping is enabled.

		Args:
			text: The text to be processed.

		Returns:
			The text with formatting applied.
		"""
		paragraphs: list[str] = self.get_paragraphs(text)
		for i, paragraph in enumerate(paragraphs):
			if not self.is_comment(paragraph):
				paragraphs[i] = self.word_wrap(self.capitalise(self.collapse_spaces(paragraph)))
		return "\n".join(paragraphs)

	def get_paragraphs(self, text: str) -> list[str]:
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
			if self.is_comment(lines[lineno]):
				if lineno > 0:
					lines[lineno] = "\0" + lines[lineno]
				if lineno + 1 < len(lines):
					lines[lineno] += "\0"
			lineno += 1
		text = "\n".join(lines)
		text = re.sub(r"\0\n\0?", "\0", text)
		lines = [line.rstrip() for line in text.split("\0")]
		return [line for line in lines if line]

	@staticmethod
	def is_comment(line: str) -> bool:
		"""
		Determines whether a line is a comment.

		Args:
			line: The line to analyze.

		Returns:
			True if the line is a comment, False otherwise.
		"""
		return line.lstrip().startswith("#")

	@staticmethod
	def collapse_spaces(text: str) -> str:
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

	@staticmethod
	def capitalise(text: str) -> str:
		"""
		Capitalizes each sentence in a string.

		Args:
			text: The text to perform sentence capitalization on.

		Returns:
			The text after each sentence has been capitalized.
		"""
		return ". ".join(sentence.capitalize() for sentence in text.split(". "))

	@staticmethod
	def word_wrap(text: str) -> str:
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
