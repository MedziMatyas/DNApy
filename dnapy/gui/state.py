"""
The state that the panels of the main window share.

The panels (sequence view, plasmid view, feature list, dialogs) show the same GenBank file and keep track of the
same selection, so they have to see the same data. Instead of keeping it in global variables, the main window makes
one EditorState and hands it to every panel it creates, and the panels use it as `self.state`.
This module does not need wxPython, so it can be used in tests.
"""
from .. import genbank

# DNApy is made for plasmids. The sequence view draws the whole sequence as one image, which has a maximum size, so
# sequences longer than this are not drawn completely (and drawing gets slow before that). About 50 kb is enough
# for plasmids, cosmids and large viral vectors.
MAX_SEQUENCE_LENGTH = 50000


class EditorState(object):
    def __init__(self, gb=None):
        self.gb = gb if gb is not None else genbank.gbobject()  # the GenBank file that is open
        self.dna_selection = (1, -1, -1)  # (start, finish, zero): selected dna, (1, -1, -1) means no selection
        self.feature_selection = False  # index of the selected feature, False if there is none
        self.cursor_position = 1  # position of the cursor in the sequence, 1 is in front of the first base
        self.search_hits = []  # (start, finish) positions found by the last search

    def record_edit(self, cursor_before):
        """
        Remember where the cursor was before an edit that was just made (and is now at the current cursor
        position), so that undoing and redoing the edit can put the cursor back.
        """
        self.gb.set_version_cursors(cursor_before, self.cursor_position)

    def undo(self):
        """Undo the last edit, and put the cursor where it was before that edit. Returns False if there is nothing to undo."""
        index = self.gb.get_file_version_index() # the edit that is undone made this version
        if not self.gb.Undo():
            return False
        self._move_cursor(self.gb.get_version_cursors(index)[0])
        return True

    def redo(self):
        """Redo the last undone edit, and put the cursor where it was after that edit. Returns False if there is nothing to redo."""
        if not self.gb.Redo():
            return False
        self._move_cursor(self.gb.get_version_cursors(self.gb.get_file_version_index())[1])
        return True

    def _move_cursor(self, position):
        """Put the cursor at `position` (kept inside the sequence) if it is known, and remove the selection."""
        self.dna_selection = (1, -1, -1)
        if position is not None:
            length = len(self.gb.GetDNA() or '')
            self.cursor_position = max(1, min(position, length + 1))
        else:
            self.cursor_position = max(1, min(self.cursor_position, len(self.gb.GetDNA() or '') + 1))

    def new_file(self):
        """Replace the open file by an empty one and clear the selections."""
        self.open(genbank.gbobject())

    def open(self, gb):
        """Make `gb` (a genbank.gbobject) the open file and clear the selections."""
        self.gb = gb
        self.dna_selection = (1, -1, -1)
        self.feature_selection = False
        self.cursor_position = 1
        self.search_hits = []
