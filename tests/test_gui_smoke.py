"""
Smoke tests for the GUI: build the panels and the main window with a loaded file and check that they draw.
They need wxPython and pycairo (and a display), otherwise they are skipped.
"""
import os
import shutil
import tempfile
import unittest
import warnings

from . import wxapp

try:
    import cairo  # noqa: F401
except ImportError:
    cairo = None

from src import dna, genbank

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'test_plasmid.gb')

needs_gui = unittest.skipIf(wxapp.wx is None or cairo is None, 'wxPython and pycairo are needed')


def count_pixels(bitmap, colour=None):
    """Number of pixels of the given (r, g, b) colour, or of all non-white pixels if no colour is given."""
    data = bytes(bitmap.ConvertToImage().GetData())
    pixels = (data[i:i + 3] for i in range(0, len(data), 3))
    if colour is None:
        return sum(1 for pixel in pixels if pixel != b'\xff\xff\xff')
    return sum(1 for pixel in pixels if pixel == bytes(colour))


SELECTION_COLOUR = (0, 130, 237)  # #0082ED


@needs_gui
class GuiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.app = wxapp.get_app()

    def setUp(self):
        # the GUI shares its state through attributes of the genbank module
        genbank.gb = genbank.gbobject(DATA)
        genbank.dna_selection = (1, -1, -1)
        genbank.cursor_position = 1
        genbank.feature_selection = False
        genbank.search_hits = []
        self.frame = wxapp.wx.Frame(None, size=(900, 700))
        self.addCleanup(self.frame.Destroy)
        # panels of earlier tests are destroyed but would still receive the update messages
        from src.gui.compat import pub
        pub.unsubAll()
        self.addCleanup(pub.unsubAll)


class TestDnaEditor(GuiTestCase):
    def make_editor(self):
        from src.gui import dnaEditorCairo_GUI
        wx = wxapp.wx
        scroll = wx.ScrolledWindow(self.frame, wx.ID_ANY)
        editor = dnaEditorCairo_GUI.TextEdit(scroll, id=wx.ID_ANY)
        self.frame.Show()
        editor.update_ownUI()
        return editor

    def test_draws_the_sequence_and_features(self):
        editor = self.make_editor()
        self.assertGreater(editor.lineLength, 0)
        self.assertGreater(count_pixels(editor._Buffer), 500)

    def test_layout_matches_the_sequence(self):
        editor = self.make_editor()
        self.assertEqual(editor.senseLayout.length, 95)
        self.assertEqual(editor.cdna, dna.C(genbank.gb.GetDNA()))

    def test_selection_is_drawn(self):
        editor = self.make_editor()
        self.assertEqual(count_pixels(editor._Buffer, SELECTION_COLOUR), 0)
        genbank.dna_selection = (3, 12, -1)
        editor.update_ownUI()
        self.assertGreater(count_pixels(editor._Buffer, SELECTION_COLOUR), 100)

    def test_empty_file(self):
        genbank.gb = genbank.gbobject()
        editor = self.make_editor()
        self.assertEqual(editor.dna, '')

    def test_repeated_updates_do_not_change_the_layout(self):
        editor = self.make_editor()
        height, line_length = editor.minHeight, editor.lineLength
        editor.update_ownUI()
        editor.update_ownUI()
        self.assertEqual((editor.minHeight, editor.lineLength), (height, line_length))


class TestPlasmidView(GuiTestCase):
    def test_draws_the_plasmid(self):
        from src.gui import plasmid_GUI
        view = plasmid_GUI.PlasmidView2(self.frame, -1)
        self.frame.Show()
        view.update_ownUI()
        self.assertGreater(count_pixels(view.plasmid_view._Buffer), 500)


class TestFeatureList(GuiTestCase):
    def test_builds_and_updates(self):
        from src.gui import featurelist_GUI
        panel = featurelist_GUI.FeatureList(self.frame, -1)
        panel.update_ownUI()


class TestMainWindow(GuiTestCase):
    def test_main_window_opens_with_a_file(self):
        from src.gui import main
        window = main.DNApy(None, -1, 'DNApy')
        self.addCleanup(window.Destroy)
        genbank.gb = genbank.gbobject(DATA)
        window.update_globalUI()
        window.Show()
        for _ in range(5):
            wxapp.wx.Yield()
        self.assertEqual(window.GetTitle(), 'NewFile - DNApy')


class TestFeatureColour(GuiTestCase):
    def colour(self, key):
        from src.gui import config
        namespace = {}
        config.load_defaults(namespace)
        return config.feature_colour(namespace, key)

    def test_plain_keys(self):
        self.assertEqual(self.colour('CDS')['color'], 'green')
        self.assertEqual(self.colour('promoter')['color'], 'cyan')

    def test_keys_that_are_not_python_names(self):
        # in the settings these are called a35_signal, a10_signal, a5UTR, a3UTR and Daloop
        self.assertEqual(self.colour('-35_signal')['color'], 'burgundy')
        self.assertEqual(self.colour('-10_signal')['color'], 'burgundy')
        for key in ("5'UTR", "3'UTR", "D-loop"):
            self.assertEqual(self.colour(key)['color'], 'grey', key)

    def test_unknown_keys_are_grey(self):
        self.assertEqual(self.colour('something_new')['color'], 'grey')
        self.assertEqual(self.colour('files')['color'], 'grey')  # a name in the settings that is not a colour


class TestMenuItems(GuiTestCase):
    """Fire every menu item with a file loaded and a selection made. Dialogs are cancelled, no window is left open."""

    class FakeDialog(object):
        def __init__(self, *args, **kwargs):
            pass

        def ShowModal(self):
            return wxapp.wx.ID_CANCEL

        def __getattr__(self, name):
            return lambda *args, **kwargs: ''

    def menu_items(self, window):
        items = []

        def walk(menu, path):
            for item in menu.GetMenuItems():
                if item.GetSubMenu():
                    walk(item.GetSubMenu(), path + [item.GetItemLabelText()])
                elif not item.IsSeparator():
                    items.append((' > '.join(path + [item.GetItemLabelText()]), item.GetId()))
        bar = window.GetMenuBar()
        for i in range(bar.GetMenuCount()):
            walk(bar.GetMenu(i), [bar.GetMenuLabelText(i)])
        return items

    def test_every_menu_item_runs_without_an_error(self):
        import io
        import contextlib
        import subprocess
        import sys
        from unittest import mock
        from src.gui import main
        wx = wxapp.wx

        # File > Save writes to the path of the loaded file, so work on a copy of the test file
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, 'plasmid.gb')
        shutil.copy(DATA, path)

        window = main.DNApy(None, -1, 'DNApy')
        self.addCleanup(window.Destroy)
        window.Show()
        items = self.menu_items(window)
        self.assertGreater(len(items), 20)

        errors = []
        previous_hook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: errors.append((self.current, kind.__name__, str(value)))
        self.addCleanup(setattr, sys, 'excepthook', previous_hook)
        with mock.patch.object(wx, 'FileDialog', self.FakeDialog),                 mock.patch.object(wx, 'MessageDialog', self.FakeDialog),                 mock.patch.object(wx.Dialog, 'ShowModal', lambda dialog: wx.ID_CANCEL),                 mock.patch.object(subprocess, 'Popen'),                 contextlib.redirect_stdout(io.StringIO()):
            for name, item_id in items:
                if name.lower().endswith(('exit', 'quit', 'close')):
                    continue
                self.current = name
                genbank.gb = genbank.gbobject(path)
                genbank.dna_selection = (3, 20, -1)
                genbank.feature_selection = 0
                window.update_globalUI()
                event = wx.CommandEvent(wx.EVT_MENU.typeId, item_id)
                event.SetEventObject(window)
                window.ProcessEvent(event)
                for _ in range(3):
                    wx.Yield()
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
