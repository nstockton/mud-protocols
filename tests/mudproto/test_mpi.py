# Copyright (c) 2025 Nick Stockton
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Future Modules:
from __future__ import annotations

# Built-in Modules:
import re
from collections.abc import Callable
from unittest import TestCase
from unittest.mock import Mock, _Call, call, mock_open, patch
from uuid import uuid4

# MUD Protocol Modules:
from mudproto.mpi import MPI_INIT, MPIProtocol, MPIState
from mudproto.telnet_constants import LF


BODY: bytes = b"Hello World!"
SAMPLE_TEXTS: tuple[str, ...] = (
	"",
	".",
	"..",
	"....",
	"\n",
	"\n\n",
	"\t  \t \n \n",
	(
		"Long, wavey strands of grass flutter over the tops of wildly growing crops. A\n"
		+ "barren, rocky ridge rises southwards, casting a long, pointed shadow over this\n"
		+ "field. A decrepit stone wall appears to have been built over what was once the\n"
		+ "tail end of the ridge, but has now been reduced to little more than a bump in\n"
		+ "the field. To the east and north, the field continues, while in the west it\n"
		+ "comes to an abrupt end at an erradic line of scattered rocks and clumps of\n"
		+ "dirt.\n"
	),
	(
		"A round clearing, Measuring the length of a bow shot from one side to the other, is neatly trimmed "
		+ "out of a circle of hedges In the middle, the grass and soil, in turn, give way to a balding patch "
		+ "of rock swelling up from the Earth. Uncovered to the heights of the sky, the "
		+ "swelling mound peaks at an unusual shrine of stones that look as if they naturally grew "
		+ "out of the mound itself. Green, flowering ivy clothes the shrine, and "
		+ "drapes down the crevices in the rock like long, elaborate braids. "
		+ "Where the mound comes level with the clearing, a circle of majestic trees rises above, "
		+ "crowning the mound with a green ring of broad leaves."
	),
	(
		"A lightly wooded hill divides the Bree forest in the east from the \n"
		+ "road to\n"
		+ "Fornost in the west. Not quite rising to the heights of\n"
		+ " the trees at the base of the hill, "
		+ "this hill offers little view other than a passing glimps of those\n"
		+ "travelling the road directly to the west. Beyond the road, rising above \n"
		+ "the tree canapy, a barren ridge forms a straight line across the horizon. Remnents\n"
		+ "of food stuffs and miscellaneous trifles are scattered around the hilltop,\n"
		+ "although no sign of habitation can be seen.\n"
	),
	(
		"living thing protrudes. In the south, the ground continues without "
		+ "change before falling down to yet more fields, while in the west, the ground levels\n"
	),
	"#",
	"#x.",
	"  #x.",
	"..\n#x",
	"#x\ny",
	"\nt\n",
	"A\nB\n#C\n#d\ne\nf\ng\n#h\\#i\\j",
	"A\nB\nC\n#d\n#e\nf\\g\\#h\\#i\\j",
	(
		"Long, wavey strands of grass flutter over the tops of wildly growing crops. A\n"
		+ "barren, rocky ridge rises southwards, casting a long, pointed shadow over this\n"
		+ "#* eat food\n"
		+ "# you eat the mushroom\n"
		+ "field. A decrepit stone wall appears to have been built over what was once the\n"
		+ "tail end of the ridge, but has now been reduced to little more than a bump in\n"
		+ "the field. To the east and north, the field continues, while in the west it\n"
		+ "comes to an abrupt end at an erradic line of scattered rocks and clumps of\n"
		+ "dirt.\n"
	),
	(
		"A round clearing, Measuring the length of a bow shot from one side to the other, is neatly trimmed "
		+ "out of a circle of hedges In the middle, the grass and soil, in turn, give way to a balding patch "
		+ "of rock swelling up from the Earth. Uncovered to the heights of the sky, the "
		+ "swelling mound peaks at an unusual shrine of stones that look as if they naturally grew "
		+ "out of the mound itself. Green, flowering ivy clothes the shrine, and "
		+ "drapes down the crevices in the rock like long, elaborate braids. "
		+ "Where the mound comes level with the clearing, a circle of majestic trees rises above, "
		+ "crowning the mound with a green ring of broad leaves."
	),
	(
		"A lightly wooded hill divides the Bree forest in the east from the \n"
		+ "road to\n"
		+ "Fornost in the west. Not quite rising to the heights of\n"
		+ "# comment  the trees at the base of the hill, this hill offers little "
		+ "view other than a passing glimps of those\n"
		+ "travelling the road directly to the west. Beyond the road, rising above \n"
		+ "the tree canapy, a barren ridge forms a straight line across the horizon. Remnents\n"
		+ "# another comment of food stuffs and miscellaneous trifles are scattered around the hilltop,\n"
		+ "although no sign of habitation can be seen.\n"
	),
)


class TestMPIProtocol(TestCase):
	def setUp(self) -> None:
		self.game_receives: bytearray = bytearray()
		self.player_receives: bytearray = bytearray()
		self.mpi: MPIProtocol = MPIProtocol(
			self.game_receives.extend, self.player_receives.extend, output_format="normal", is_client=True
		)

	def tearDown(self) -> None:
		self.mpi.on_connection_lost()
		del self.mpi
		self.game_receives.clear()
		self.player_receives.clear()

	def parse(self, data: bytes) -> tuple[bytes, bytes, MPIState]:
		self.mpi.on_data_received(data)
		player_receives: bytes = bytes(self.player_receives)
		self.player_receives.clear()
		game_receives: bytes = bytes(self.game_receives)
		self.game_receives.clear()
		state: MPIState = self.mpi.state
		self.mpi.state = MPIState.DATA
		self.mpi._mpi_buffer.clear()
		return player_receives, game_receives, state

	@patch("mudproto.mpi.logger", Mock())
	@patch("mudproto.mpi.threading")
	def test_mpi_on_data_received(self, mock_threading: Mock) -> None:
		data: bytes = BODY
		self.mpi.output_format = "normal"
		self.mpi.on_connection_made()
		self.assertEqual(self.parse(data), (data, MPI_INIT + b"I" + LF, MPIState.DATA))
		# When line feed is encountered, state becomes 'newline'.
		self.assertEqual(self.parse(data + LF), (data + LF, b"", MPIState.NEWLINE))
		# If data follows line feed and MPI_INIT does not start with data, fall back to state 'data'.
		self.assertEqual(self.parse(data + LF + data), (data + LF + data, b"", MPIState.DATA))
		# if some but not all of MPI_INIT was  received followed by a line feed, fall back to state 'newline'.
		self.assertEqual(self.parse(LF + MPI_INIT[:1] + LF), (LF + MPI_INIT[:1] + LF, b"", MPIState.NEWLINE))
		# if some but not all of MPI_INIT was  received followed by data, fall back to state 'data'.
		self.assertEqual(self.parse(LF + MPI_INIT[:1] + data), (LF + MPI_INIT[:1] + data, b"", MPIState.DATA))
		# if a line feed is followed by 1 or more bytes of MPI_INIT, but
		# not the final byte, state becomes 'init'.
		# If a line feed is followed by part of MPI_INIT and then junk, state becomes 'data'.
		for i in range(1, len(MPI_INIT)):
			self.mpi.on_data_received(LF + MPI_INIT[:i])
			self.assertEqual(
				(self.player_receives, self.game_receives, self.mpi.state), (LF, b"", MPIState.INIT)
			)
			self.mpi.on_data_received(b"**junk**")
			self.assertEqual(
				(self.player_receives, self.game_receives, self.mpi.state),
				(LF + MPI_INIT[:i] + b"**junk**", b"", MPIState.DATA),
			)
			self.player_receives.clear()
			self.mpi.state = MPIState.DATA
			self.mpi._mpi_buffer.clear()
		# If a line feed is followed by all the bytes of MPI_INIT, state becomes 'command'.
		self.assertEqual(self.parse(LF + MPI_INIT), (LF, b"", MPIState.COMMAND))
		# Command is a single byte after MPI_INIT. State then becomes 'length'.
		self.assertEqual(self.parse(LF + MPI_INIT + b"V"), (LF, b"", MPIState.LENGTH))
		# Length is the length of the message body as one or more digits, terminated by a line feed.
		# Verify that an empty length or length containing non-digits is properly handled.
		self.assertEqual(
			self.parse(LF + MPI_INIT + b"V" + LF), (LF + MPI_INIT + b"V" + LF, b"", MPIState.NEWLINE)
		)
		self.assertEqual(
			self.parse(LF + MPI_INIT + b"V1t" + LF), (LF + MPI_INIT + b"V1t" + LF, b"", MPIState.NEWLINE)
		)
		# If length is valid, state becomes 'body'.
		# The body consists of the bytes following length and the line feed.
		# Once <length> bytes are received, state becomes 'data' and the appropriate
		# method is called to handle the MPI message.
		message: bytes = b"%d%b%b" % (len(data), LF, data)
		# Test invalid MPI commands are handled.
		self.assertEqual(
			self.parse(LF + MPI_INIT + b"A" + message), (LF + MPI_INIT + b"A" + message, b"", MPIState.DATA)
		)
		# test valid MPI commands are handled.
		self.assertEqual(self.parse(LF + MPI_INIT + b"V" + message), (LF, b"", MPIState.DATA))
		mock_threading.Thread.assert_called_once_with(
			target=self.mpi.command_map[b"V"], args=(data,), daemon=True
		)

	@patch("mudproto.mpi.os.remove")
	@patch("mudproto.mpi.subprocess.run")
	@patch("mudproto.mpi.tempfile.NamedTemporaryFile")
	@patch("mudproto.mpi.print")
	def test_mpi_view(
		self,
		mock_print: Mock,
		mock_named_temporary_file: Mock,
		mock_subprocess: Mock,
		mock_remove: Mock,
	) -> None:
		temp_file_name: str = "temp_file_name"
		mock_named_temporary_file.return_value.__enter__.return_value.name = temp_file_name
		self.assertEqual(self.player_receives, b"")
		self.assertEqual(self.game_receives, b"")
		self.assertEqual(self.mpi.state, MPIState.DATA)
		self.mpi.on_connection_made()
		self.assertEqual(self.parse(b""), (b"", MPI_INIT + b"I" + LF, MPIState.DATA))
		# Test output_format is 'tintin'.
		self.mpi.output_format = "tintin"
		self.mpi.view(b"V" + BODY + LF)
		self.assertEqual(
			(self.player_receives, self.game_receives, self.mpi.state), (b"", b"", MPIState.DATA)
		)
		mock_named_temporary_file.assert_called_once()
		mock_print.assert_called_once_with(f"MPICOMMAND:{self.mpi.pager} {temp_file_name}:MPICOMMAND")
		mock_named_temporary_file.reset_mock()
		# Test output_format is *not* 'tintin'.
		self.mpi.output_format = "normal"
		self.mpi.view(b"V" + BODY + LF)
		self.assertEqual(
			(self.player_receives, self.game_receives, self.mpi.state), (b"", b"", MPIState.DATA)
		)
		mock_named_temporary_file.assert_called_once()
		mock_subprocess.assert_called_once_with((*self.mpi.pager.split(), temp_file_name))
		mock_remove.assert_called_once_with(temp_file_name)

	@patch("mudproto.mpi.open", mock_open(read_data=str(BODY, "utf-8")))
	@patch("mudproto.mpi.MPIProtocol.postprocess")
	@patch("mudproto.mpi.os.remove")
	@patch("mudproto.mpi.subprocess.run")
	@patch("mudproto.mpi.tempfile.NamedTemporaryFile")
	@patch("mudproto.mpi.os.path")
	@patch("mudproto.mpi.input", return_value="")
	@patch("mudproto.mpi.print")
	def test_mpi_edit(
		self,
		mock_print: Mock,
		mock_input: Mock,
		mock_os_path: Mock,
		mock_named_temporary_file: Mock,
		mock_subprocess: Mock,
		mock_remove: Mock,
		mock_postprocessor: Mock,
	) -> None:
		session: bytes = b"12345" + LF
		description: bytes = b"description" + LF
		temp_file_name: str = "temp_file_name"
		expected_sent: bytes
		mock_named_temporary_file.return_value.__enter__.return_value.name = temp_file_name
		# Make sure we are in the default state.
		self.assertEqual(self.player_receives, b"")
		self.assertEqual(self.game_receives, b"")
		self.assertEqual(self.mpi.state, MPIState.DATA)
		self.mpi.on_connection_made()
		self.assertEqual(self.parse(b""), (b"", MPI_INIT + b"I" + LF, MPIState.DATA))
		# Test a canceled session.
		expected_sent = MPI_INIT + b"E" + b"%d" % len(b"C" + session) + LF + b"C" + session
		# Same modified time means the file was *not* modified.
		mock_os_path.getmtime.return_value = 1.0
		# Test output_format is 'tintin'.
		self.mpi.output_format = "tintin"
		self.mpi.edit(b"E" + session + description + BODY + LF)
		self.assertEqual(
			(self.player_receives, self.game_receives, self.mpi.state), (b"", expected_sent, MPIState.DATA)
		)
		self.game_receives.clear()
		mock_named_temporary_file.assert_called_once()
		mock_print.assert_called_once_with(f"MPICOMMAND:{self.mpi.editor} {temp_file_name}:MPICOMMAND")
		mock_input.assert_called_once_with("Continue:")
		mock_remove.assert_called_once_with(temp_file_name)
		mock_named_temporary_file.reset_mock()
		mock_print.reset_mock()
		mock_input.reset_mock()
		mock_remove.reset_mock()
		# Test output_format is *not* 'tintin'.
		self.mpi.output_format = "normal"
		self.mpi.edit(b"E" + session + description + BODY + LF)
		self.assertEqual(
			(self.player_receives, self.game_receives, self.mpi.state), (b"", expected_sent, MPIState.DATA)
		)
		self.game_receives.clear()
		mock_named_temporary_file.assert_called_once()
		mock_subprocess.assert_called_once_with((*self.mpi.editor.split(), temp_file_name))
		mock_remove.assert_called_once_with(temp_file_name)
		mock_named_temporary_file.reset_mock()
		mock_subprocess.reset_mock()
		mock_remove.reset_mock()
		mock_os_path.reset_mock(return_value=True)
		# Test remote editing.
		expected_sent = (
			MPI_INIT + b"E" + b"%d" % len(b"E" + session + BODY + LF) + LF + b"E" + session + BODY + LF
		)
		# Different modified time means the file was modified.
		mock_os_path.getmtime.side_effect = lambda *args: uuid4()
		# Test output_format is 'tintin'.
		self.mpi.output_format = "tintin"
		self.mpi.edit(b"E" + session + description + BODY + LF)
		self.assertEqual(
			(self.player_receives, self.game_receives, self.mpi.state), (b"", expected_sent, MPIState.DATA)
		)
		self.game_receives.clear()
		mock_named_temporary_file.assert_called_once()
		mock_print.assert_called_once_with(f"MPICOMMAND:{self.mpi.editor} {temp_file_name}:MPICOMMAND")
		mock_input.assert_called_once_with("Continue:")
		mock_remove.assert_called_once_with(temp_file_name)
		mock_named_temporary_file.reset_mock()
		mock_print.reset_mock()
		mock_input.reset_mock()
		mock_remove.reset_mock()
		# Test output_format is *not* 'tintin'.
		self.mpi.output_format = "normal"
		self.mpi.edit(b"E" + session + description + BODY + LF)
		self.assertEqual(
			(self.player_receives, self.game_receives, self.mpi.state), (b"", expected_sent, MPIState.DATA)
		)
		self.game_receives.clear()
		mock_named_temporary_file.assert_called_once()
		mock_subprocess.assert_called_once_with((*self.mpi.editor.split(), temp_file_name))
		mock_remove.assert_called_once_with(temp_file_name)
		# confirm pre and post processors were not called since wordwrapping was not defined
		mock_postprocessor.assert_not_called()
		# test given wordwrapping is enabled, processor methods are called
		self.mpi.is_word_wrapping = True
		self.mpi.edit(b"E" + session + description + BODY + LF)
		mock_postprocessor.assert_called_once()
		mock_postprocessor.reset_mock()
		# test given wordwrapping is disabled, processor methods are not called
		self.mpi.is_word_wrapping = False
		self.mpi.edit(b"E" + session + description + BODY + LF)
		mock_postprocessor.assert_not_called()


class TestEditorPostprocessor(TestCase):
	def setUp(self) -> None:
		self.game_receives: bytearray = bytearray()
		self.player_receives: bytearray = bytearray()
		self.MPIProtocol = MPIProtocol(
			self.game_receives.extend, self.player_receives.extend, output_format="normal", is_client=True
		)
		self.postprocess = self.MPIProtocol.postprocess
		self.get_paragraphs = self.MPIProtocol.get_paragraphs
		self.collapse_spaces = self.MPIProtocol.collapse_spaces
		self.capitalise = self.MPIProtocol.capitalise
		self.word_wrap = self.MPIProtocol.word_wrap

	def test_postprocessing(self) -> None:
		with patch.object(self.MPIProtocol, "collapse_spaces", Mock(wraps=str)) as mock_collapse_spaces:
			for sample_text in SAMPLE_TEXTS:
				self.MPIProtocol.postprocess(sample_text)
				text_without_comments: str = re.sub(r"(^|(?<=\n))\s*#.*(?=\n|$)", "\0", sample_text)
				text_without_comments = text_without_comments.replace("\0\n", "\0")
				paragraphs: list[str] = [
					paragraph.rstrip() for paragraph in text_without_comments.split("\0")
				]
				expected_calls: list[Callable[[str], _Call]] = [call(p) for p in paragraphs if p]
				self.assertListEqual(
					mock_collapse_spaces.mock_calls,
					expected_calls,
					f"from sample text {sample_text.encode('us-ascii')!r}",
				)
				mock_collapse_spaces.reset_mock()

	def test_when_collapsing_spaces_then_each_newline_is_preserved(self) -> None:
		for sample_text in SAMPLE_TEXTS:
			processed_text: str = self.collapse_spaces(sample_text)
			self.assertEqual(
				processed_text.count("\n"),
				sample_text.count("\n"),
				f"processed text:\n{processed_text}\nsample text:\n{sample_text}\n",
			)

	def test_capitalisation(self) -> None:
		for sample_text in SAMPLE_TEXTS:
			processed_text: str = self.capitalise(sample_text)
		for sentence in processed_text.split(". "):
			self.assertTrue(
				sentence[0].isupper() or not sentence[0].isalpha(),
				(
					f"The sentence\n{sentence}\nfrom the sample text\n{sample_text}\n"
					+ "starts with an uncapitalized letter."
				),
			)

	def test_word_wrap(self) -> None:
		for sample_text in SAMPLE_TEXTS:
			processed_text: str = self.word_wrap(sample_text)
			for line in processed_text.split("\n"):
				self.assertLess(
					len(line),
					80,
					(
						f"The line\n{line}\nfrom the sample text\n{sample_text}\nis {len(line)} "
						+ "chars long, which is too long"
					),
				)
