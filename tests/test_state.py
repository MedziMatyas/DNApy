import contextlib
import io
import unittest

from dnapy import genbank
from dnapy.gui.state import EditorState


def state_with(sequence, cursor):
    """A state with a file that holds `sequence`, as if it was just opened, and the cursor in front of base `cursor`."""
    gb = genbank.gbobject()
    with contextlib.redirect_stdout(io.StringIO()):
        gb.Paste(1, sequence)
    gb.reset_file_versions()
    state = EditorState(gb)
    state.cursor_position = cursor
    return state


def type_in(state, text):
    """Insert text at the cursor, one base at a time, like the editor does for key presses."""
    for char in text:
        before = state.cursor_position
        state.gb.Paste(state.cursor_position, char)
        state.cursor_position += 1
        state.record_edit(before)


def show(state):
    """The sequence with a | where the cursor is, for example ag|ct."""
    dna = state.gb.GetDNA()
    return dna[:state.cursor_position - 1] + '|' + dna[state.cursor_position - 1:]


class TestCursorAndHistory(unittest.TestCase):
    def test_undo_and_redo_of_insertions_move_the_cursor_with_the_sequence(self):
        state = state_with('agct', 3)
        self.assertEqual(show(state), 'ag|ct')
        type_in(state, 'at')
        self.assertEqual(show(state), 'agat|ct')
        self.assertTrue(state.undo())
        self.assertEqual(show(state), 'aga|ct')
        self.assertTrue(state.undo())
        self.assertEqual(show(state), 'ag|ct')
        self.assertFalse(state.undo())
        self.assertEqual(show(state), 'ag|ct')
        self.assertTrue(state.redo())
        self.assertEqual(show(state), 'aga|ct')
        self.assertTrue(state.redo())
        self.assertEqual(show(state), 'agat|ct')
        self.assertFalse(state.redo())

    def test_undo_of_a_backspace_puts_the_cursor_after_the_restored_base(self):
        state = state_with('agct', 3)  # ag|ct
        before = state.cursor_position
        state.gb.Delete(2, 2)  # backspace removes the g
        state.cursor_position = 2
        state.record_edit(before)
        self.assertEqual(show(state), 'a|ct')
        state.undo()
        self.assertEqual(show(state), 'ag|ct')
        state.redo()
        self.assertEqual(show(state), 'a|ct')

    def test_undo_of_a_delete_keeps_the_cursor_in_front_of_the_restored_base(self):
        state = state_with('agct', 3)  # ag|ct
        before = state.cursor_position
        state.gb.Delete(3, 3)  # delete removes the c, the cursor stays
        state.record_edit(before)
        self.assertEqual(show(state), 'ag|t')
        state.undo()
        self.assertEqual(show(state), 'ag|ct')

    def test_the_cursor_goes_back_to_the_place_of_the_edit_not_to_where_it_was_later(self):
        state = state_with('aaaaaaaaaa', 2)
        type_in(state, 'g')  # a|aaaaaaaaa -> ag|aaaaaaaaa
        state.cursor_position = 9  # the user clicks somewhere else
        type_in(state, 't')
        self.assertEqual(show(state), 'agaaaaaat|aaa')
        state.undo()
        self.assertEqual(state.cursor_position, 9)  # where the undone edit was made
        state.undo()
        self.assertEqual(state.cursor_position, 2)

    def test_edits_that_did_not_say_where_the_cursor_was_leave_it_alone(self):
        state = state_with('agct', 4)
        state.gb.Upper(1, 2)  # no record_edit
        state.undo()
        self.assertEqual(state.cursor_position, 4)
        self.assertEqual(state.gb.GetDNA(), 'agct')

    def test_the_cursor_stays_inside_the_sequence(self):
        state = state_with('agct', 4)
        type_in(state, 'aaaa')  # the cursor is at 8
        state.gb.Delete(1, 6)  # a big edit that says nothing about the cursor
        state.record_edit(8)
        state.cursor_position = 3
        state.undo()
        self.assertLessEqual(state.cursor_position, len(state.gb.GetDNA()) + 1)
        self.assertGreaterEqual(state.cursor_position, 1)

    def test_undo_removes_the_selection(self):
        state = state_with('agct', 3)
        type_in(state, 'a')
        state.dna_selection = (1, 2, -1)
        state.undo()
        self.assertEqual(state.dna_selection, (1, -1, -1))

    def test_a_new_edit_after_undo_forgets_the_old_cursors_too(self):
        state = state_with('agct', 3)
        type_in(state, 'a')
        type_in(state, 't')
        state.undo()
        type_in(state, 'c')  # replaces the undone edit
        self.assertEqual(show(state), 'agac|ct')
        self.assertFalse(state.redo())
        state.undo()
        self.assertEqual(show(state), 'aga|ct')
        state.undo()
        self.assertEqual(show(state), 'ag|ct')
        self.assertEqual(len(state.gb.file_version_cursors), len(state.gb.file_versions))

    def test_cursors_are_stored_per_version(self):
        state = state_with('agct', 3)
        type_in(state, 'at')
        self.assertEqual(state.gb.get_version_cursors(0), (None, None))  # the file as it was opened
        self.assertEqual(state.gb.get_version_cursors(1), (3, 4))
        self.assertEqual(state.gb.get_version_cursors(2), (4, 5))

    def test_open_starts_a_new_history(self):
        state = state_with('agct', 3)
        type_in(state, 'a')
        state.open(genbank.gbobject())
        self.assertFalse(state.undo())
        self.assertEqual(state.cursor_position, 1)


if __name__ == '__main__':
    unittest.main()
