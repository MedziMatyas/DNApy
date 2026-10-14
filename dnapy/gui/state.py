"""
The state that the panels of the main window share.

The panels (sequence view, plasmid view, feature list, dialogs) show the same GenBank file and keep track of the
same selection, so they have to see the same data. Instead of keeping it in global variables, the main window makes
one EditorState and hands it to every panel it creates, and the panels use it as `self.state`.
This module does not need wxPython, so it can be used in tests.
"""
from .. import genbank


class EditorState(object):
    def __init__(self, gb=None):
        self.gb = gb if gb is not None else genbank.gbobject()  # the GenBank file that is open
        self.dna_selection = (1, -1, -1)  # (start, finish, zero): selected dna, (1, -1, -1) means no selection
        self.feature_selection = False  # index of the selected feature, False if there is none
        self.cursor_position = 1  # position of the cursor in the sequence, 1 is in front of the first base
        self.search_hits = []  # (start, finish) positions found by the last search

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
