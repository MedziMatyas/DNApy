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
        scroll.SetScrollRate(1, 15)  # as in the main window, which makes the window scrollable
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

    def press(self, editor, code, shift=False):
        """Send a key press to the editor. Printable keys have a unicode key, special keys (arrows) do not."""
        wx = wxapp.wx
        event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        event.SetKeyCode(code)
        event.SetUnicodeKey(code if 32 <= code < 127 else 0)
        event.SetShiftDown(shift)
        editor.OnKeyPress(event)

    def test_typing_inserts_bases(self):
        editor = self.make_editor()
        self.press(editor, ord('G'))  # no shift: lower case
        self.assertEqual(genbank.gb.GetDNA()[:6], 'gatggc')
        self.press(editor, ord('T'), shift=True)  # shift: upper case
        self.assertEqual(genbank.gb.GetDNA()[:6], 'gTatgg')
        self.assertEqual(len(genbank.gb.GetDNA()), 97)
        self.assertEqual(editor.PositionPointer, 3)

    def test_other_letters_are_ignored(self):
        editor = self.make_editor()
        self.press(editor, ord('X'))
        self.assertEqual(len(genbank.gb.GetDNA()), 95)

    def test_arrow_keys_move_the_cursor(self):
        wx = wxapp.wx
        editor = self.make_editor()
        self.press(editor, wx.WXK_RIGHT)
        self.press(editor, wx.WXK_RIGHT)
        self.assertEqual(editor.PositionPointer, 3)
        self.press(editor, wx.WXK_LEFT)
        self.assertEqual(editor.PositionPointer, 2)

    def test_backspace_and_delete(self):
        wx = wxapp.wx
        editor = self.make_editor()
        self.press(editor, wx.WXK_RIGHT)
        self.press(editor, wx.WXK_RIGHT)  # cursor is now in front of the third base
        self.press(editor, wx.WXK_BACK)  # removes the base in front of the cursor
        self.assertEqual(genbank.gb.GetDNA()[:5], 'aggct')
        self.press(editor, wx.WXK_DELETE)  # removes the base after the cursor
        self.assertEqual(len(genbank.gb.GetDNA()), 93)

    def mouse_at(self, editor, x, y):
        """Make the editor see the mouse at (x, y) in its own coordinates."""
        from unittest import mock
        wx = wxapp.wx
        patcher = mock.patch.object(wx, 'GetMousePosition', lambda: editor.ClientToScreen(wx.Point(int(x), int(y))))
        patcher.start()
        self.addCleanup(patcher.stop)

    def centre_of(self, editor, index):
        x, y, w, h = editor.senseLayout.index_to_pos(index)
        return editor.dX + x + w / 2, editor.sY + y + h / 2

    def mouse_event(self, editor, kind):
        event = wxapp.wx.MouseEvent(kind)
        event.SetEventObject(editor)
        return event

    def test_click_places_the_cursor(self):
        wx = wxapp.wx
        editor = self.make_editor()
        self.mouse_at(editor, *self.centre_of(editor, 10))
        editor.OnLeftDown(self.mouse_event(editor, wx.wxEVT_LEFT_DOWN))
        self.assertEqual(editor.PositionPointer, 11)  # positions are 1-based

    def test_dragging_selects(self):
        wx = wxapp.wx
        editor = self.make_editor()
        self.mouse_at(editor, *self.centre_of(editor, 10))
        editor.OnLeftDown(self.mouse_event(editor, wx.wxEVT_LEFT_DOWN))
        self.mouse_at(editor, *self.centre_of(editor, 25))
        motion = self.mouse_event(editor, wx.wxEVT_MOTION)
        motion.SetLeftDown(True)
        editor.OnMotion(motion)
        self.assertEqual(genbank.dna_selection, (11, 26, -1))

    def test_hit_test_finds_the_feature_under_the_mouse(self):
        editor = self.make_editor()
        self.mouse_at(editor, 100, editor.sY - 9)  # the bar of the first feature is drawn just above the text
        self.assertEqual(editor.HitTest(), 'test_cds0')
        self.mouse_at(editor, 100, editor.sY + 60)  # nothing here
        self.assertIsNone(editor.HitTest())

    def test_long_sequence_can_be_scrolled(self):
        genbank.gb.gbfile['dna'] = 'acgt' * 750  # 3000 bp, many more lines than fit in the window
        editor = self.make_editor()
        scroll = editor.parent
        for _ in range(5):
            wxapp.wx.Yield()
        self.assertTrue(scroll.HasScrollbar(wxapp.wx.VERTICAL))
        # the editor is as high as all of its lines, not only as high as the visible part
        self.assertEqual(editor.GetSize()[1], editor.minHeight)
        self.assertGreater(editor.minHeight, scroll.GetClientSize()[1] * 3)
        # the scroll bar must not make the editor wider than the visible area
        self.assertLessEqual(editor.GetSize()[0], scroll.GetClientSize()[0])

    def test_mouse_wheel_scrolls(self):
        wx = wxapp.wx
        genbank.gb.gbfile['dna'] = 'acgt' * 750
        editor = self.make_editor()
        scroll = editor.parent
        for _ in range(5):
            wx.Yield()
        self.assertEqual(scroll.GetViewStart()[1], 0)
        event = wx.MouseEvent(wx.wxEVT_MOUSEWHEEL)
        event.SetEventObject(editor)
        event.SetWheelRotation(-120)  # one notch down
        event.SetWheelDelta(120)
        event.SetLinesPerAction(3)
        editor.GetEventHandler().ProcessEvent(event)
        self.assertGreater(scroll.GetViewStart()[1], 0)

    def test_short_sequence_needs_no_scroll_bar(self):
        editor = self.make_editor()
        for _ in range(5):
            wxapp.wx.Yield()
        self.assertFalse(editor.parent.HasScrollbar(wxapp.wx.VERTICAL))

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


class TestUserSettings(GuiTestCase):
    """The GUI uses the settings, so a user file changes how it looks."""

    def use_settings(self, text):
        from unittest import mock
        from src import settings
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, 'user.toml')
        with open(path, 'w') as f:
            f.write(text)
        patcher = mock.patch.object(settings, '_current', settings.load(path))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_window_size(self):
        from src.gui import main
        self.use_settings('[window]\nsize = [900, 500]\n')
        window = main.DNApy(None, -1, 'DNApy')
        self.addCleanup(window.Destroy)
        self.assertEqual(tuple(window.GetSize()), (900, 500))

    def test_feature_colour_in_the_editor(self):
        from src.gui import dnaEditorCairo_GUI
        wx = wxapp.wx

        def count_cds_bar_pixels(colour):
            frame = wx.Frame(None, size=(900, 700))
            self.addCleanup(frame.Destroy)
            scroll = wx.ScrolledWindow(frame, wx.ID_ANY)
            scroll.SetScrollRate(1, 15)
            editor = dnaEditorCairo_GUI.TextEdit(scroll, id=wx.ID_ANY)
            frame.Show()
            editor.update_ownUI()
            return count_pixels(editor._Buffer, colour)

        self.assertEqual(count_cds_bar_pixels((0xB0, 0x1A, 0x1A)), 0)  # the CDS is green by default
        self.use_settings('[features.colors]\nCDS = "red"\n')
        self.assertGreater(count_cds_bar_pixels((0xB0, 0x1A, 0x1A)), 100)


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
