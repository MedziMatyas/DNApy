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

from dnapy import dna, genbank
from dnapy.gui.state import EditorState

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
        # windows are destroyed later, when wx has time to do it; do that after each test and not all at the end
        self.addCleanup(lambda: [wxapp.wx.Yield() for _ in range(3)])
        # everything the panels share: the open file, the selections, ...
        self.state = EditorState(genbank.gbobject(DATA))
        self.frame = wxapp.wx.Frame(None, size=(900, 700))
        self.addCleanup(self.frame.Destroy)
        # panels of earlier tests are destroyed but would still receive the update messages
        from dnapy.gui.compat import pub
        pub.unsubAll()
        self.addCleanup(pub.unsubAll)


class TestDnaEditor(GuiTestCase):
    def make_editor(self):
        from dnapy.gui import dnaEditorCairo_GUI
        wx = wxapp.wx
        scroll = wx.ScrolledWindow(self.frame, wx.ID_ANY)
        scroll.SetScrollRate(1, 15)  # as in the main window, which makes the window scrollable
        editor = dnaEditorCairo_GUI.TextEdit(scroll, wx.ID_ANY, self.state)
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
        self.assertEqual(editor.cdna, dna.C(self.state.gb.GetDNA()))

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
        self.assertEqual(self.state.gb.GetDNA()[:6], 'gatggc')
        self.press(editor, ord('T'), shift=True)  # shift: upper case
        self.assertEqual(self.state.gb.GetDNA()[:6], 'gTatgg')
        self.assertEqual(len(self.state.gb.GetDNA()), 97)
        self.assertEqual(editor.PositionPointer, 3)

    def shown(self):
        """The beginning of the sequence with a | where the cursor is, for example ag|ct."""
        dna = self.state.gb.GetDNA()
        return dna[:self.state.cursor_position - 1] + '|' + dna[self.state.cursor_position - 1:]

    def test_undo_and_redo_move_the_cursor_with_the_sequence(self):
        editor = self.make_editor()
        self.state.cursor_position = 3
        self.assertEqual(self.shown()[:8], 'at|ggcta')
        self.press(editor, ord('A'))
        self.press(editor, ord('T'))
        self.assertEqual(self.shown()[:9], 'atat|ggct')
        self.state.undo()
        self.assertEqual(self.shown()[:9], 'ata|ggcta')
        self.assertEqual(editor.PositionPointer, 4)  # the editor shows the cursor at the same place
        self.state.undo()
        self.assertEqual(self.shown()[:8], 'at|ggcta')
        self.state.redo()
        self.state.redo()
        self.assertEqual(self.shown()[:9], 'atat|ggct')

    def test_undo_after_backspace_and_delete(self):
        wx = wxapp.wx
        editor = self.make_editor()
        self.state.cursor_position = 3  # at|ggcta...
        self.press(editor, wx.WXK_BACK)
        self.assertEqual(self.shown()[:7], 'a|ggcta')
        self.state.undo()
        self.assertEqual(self.shown()[:8], 'at|ggcta')
        self.press(editor, wx.WXK_DELETE)
        self.assertEqual(self.shown()[:7], 'at|gcta')  # the g after the cursor is gone
        self.state.undo()
        self.assertEqual(self.shown()[:8], 'at|ggcta')

    def test_backspace_at_the_start_and_delete_at_the_end_do_nothing(self):
        wx = wxapp.wx
        editor = self.make_editor()
        self.state.cursor_position = 1
        self.press(editor, wx.WXK_BACK)
        self.assertEqual(len(self.state.gb.GetDNA()), 95)
        self.state.cursor_position = 96
        self.press(editor, wx.WXK_DELETE)
        self.assertEqual(len(self.state.gb.GetDNA()), 95)
        self.assertFalse(self.state.undo())  # nothing was edited

    def test_typing_replaces_the_selection(self):
        editor = self.make_editor()
        self.state.dna_selection = (3, 6, -1)  # the bases 3 to 6 are selected
        self.state.cursor_position = 7
        self.press(editor, ord('C'), shift=True)
        self.assertEqual(self.state.gb.GetDNA()[:6], 'atCagc')  # the bases 3-6 ('ggct') are replaced by a C
        self.assertEqual(len(self.state.gb.GetDNA()), 95 - 4 + 1)
        self.assertEqual(self.state.cursor_position, 4)
        self.assertEqual(self.state.dna_selection, (1, -1, -1))
        self.state.undo()
        self.assertEqual(self.state.gb.GetDNA(), self.state.gb.file_versions[0]['dna'])
        self.assertEqual(self.state.cursor_position, 7)  # where it was before the typing replaced the selection

    def test_backspace_deletes_the_whole_selection(self):
        wx = wxapp.wx
        editor = self.make_editor()
        self.state.dna_selection = (3, 6, -1)
        self.press(editor, wx.WXK_BACK)
        self.assertEqual(self.state.gb.GetDNA()[:6], 'atagca')  # the bases 3-6 ('ggct') are gone
        self.assertEqual(len(self.state.gb.GetDNA()), 91)

    def test_undo_button_of_the_main_window_moves_the_cursor_too(self):
        from dnapy.gui import main
        window = main.DNApy(None, -1, 'DNApy')
        self.addCleanup(window.Destroy)
        window.state.open(genbank.gbobject(DATA))
        window.Show()
        window.update_globalUI()
        editor = window.DNApy.dnaview
        window.state.cursor_position = 3
        self.press(editor, ord('A'))
        self.press(editor, ord('T'))
        self.assertEqual(window.state.cursor_position, 5)
        window.Undo(None)
        self.assertEqual(window.state.cursor_position, 4)
        self.assertEqual(editor.PositionPointer, 4)
        window.Redo(None)
        self.assertEqual(window.state.cursor_position, 5)

    def test_other_letters_are_ignored(self):
        editor = self.make_editor()
        self.press(editor, ord('X'))
        self.assertEqual(len(self.state.gb.GetDNA()), 95)

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
        self.assertEqual(self.state.gb.GetDNA()[:5], 'aggct')
        self.press(editor, wx.WXK_DELETE)  # removes the base after the cursor
        self.assertEqual(len(self.state.gb.GetDNA()), 93)

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
        self.assertEqual(self.state.dna_selection, (11, 26, -1))

    def test_hit_test_finds_the_feature_under_the_mouse(self):
        editor = self.make_editor()
        self.mouse_at(editor, 100, editor.sY - 9)  # the bar of the first feature is drawn just above the text
        self.assertEqual(editor.HitTest(), 'test_cds0')
        self.mouse_at(editor, 100, editor.sY + 60)  # nothing here
        self.assertIsNone(editor.HitTest())

    def test_long_sequence_can_be_scrolled(self):
        self.state.gb.gbfile['dna'] = 'acgt' * 750  # 3000 bp, many more lines than fit in the window
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
        self.state.gb.gbfile['dna'] = 'acgt' * 750
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

    def long_editor(self):
        """An editor with 3000 bp, many more lines than fit in the window, and the window scrolled to the top."""
        self.state.gb.gbfile['dna'] = 'acgt' * 750
        editor = self.make_editor()
        for _ in range(5):
            wxapp.wx.Yield()
        self.assertEqual(self.view_top(editor), 0)
        return editor

    def view_top(self, editor):
        scroll = editor.parent
        return scroll.GetViewStart()[1] * scroll.GetScrollPixelsPerUnit()[1]

    def is_in_view(self, editor, base):
        """Is the line with this base (1-based) completely visible?"""
        y = editor.sY + editor.senseLayout.index_to_pos(base - 1)[1]
        height = 2 * editor.senseLayout.text_height + editor.lineGap
        top = self.view_top(editor)
        return top <= y and y + height <= top + editor.parent.GetClientSize()[1]

    def select(self, editor, start, finish):
        self.state.dna_selection = (start, finish, -1)
        editor.update_ownUI()

    def test_a_selection_below_the_window_is_scrolled_into_view(self):
        editor = self.long_editor()
        self.assertFalse(self.is_in_view(editor, 2900))
        self.select(editor, 2900, 2905)
        self.assertTrue(self.is_in_view(editor, 2900))
        self.assertGreater(self.view_top(editor), 0)

    def test_a_selection_above_the_window_is_scrolled_into_view(self):
        editor = self.long_editor()
        self.select(editor, 2900, 2905)  # scrolls to the end
        self.select(editor, 10, 15)  # and back to the start
        self.assertTrue(self.is_in_view(editor, 10))
        self.assertEqual(self.view_top(editor), 0)

    def test_scrolling_is_as_little_as_needed(self):
        editor = self.long_editor()
        self.select(editor, 2900, 2905)
        top = self.view_top(editor)
        # a selection on the line before the first one in view needs only a little scrolling
        line_length = editor.lineLength
        first_visible_line = int(top // editor.lineHeight)
        base_above = (first_visible_line - 1) * line_length + 1
        self.select(editor, base_above, base_above + 3)
        self.assertTrue(self.is_in_view(editor, base_above))
        self.assertLess(top - self.view_top(editor), 2 * editor.lineHeight)

    def test_a_selection_that_is_in_view_does_not_scroll(self):
        editor = self.long_editor()
        self.select(editor, 20, 25)
        self.assertEqual(self.view_top(editor), 0)
        self.select(editor, 30, 35)
        self.assertEqual(self.view_top(editor), 0)

    def test_the_cursor_is_scrolled_into_view_too(self):
        wx = wxapp.wx
        editor = self.long_editor()
        self.state.cursor_position = 2500
        editor.update_ownUI()
        self.assertTrue(self.is_in_view(editor, 2500))
        self.state.cursor_position = 5
        editor.update_ownUI()
        self.assertEqual(self.view_top(editor), 0)

    def test_typing_far_from_the_view_scrolls_to_the_cursor(self):
        editor = self.long_editor()
        self.state.cursor_position = 2000
        editor.update_ownUI()
        self.press(editor, ord('A'))
        self.assertTrue(self.is_in_view(editor, 2001))

    def test_undo_scrolls_to_where_the_edit_was(self):
        editor = self.long_editor()
        self.state.cursor_position = 2000
        editor.update_ownUI()
        self.press(editor, ord('A'))
        self.state.cursor_position = 5
        editor.update_ownUI()  # the user went back to the start
        self.assertEqual(self.view_top(editor), 0)
        self.state.undo()
        editor.update_ownUI()
        self.assertTrue(self.is_in_view(editor, 2000))

    def test_the_first_drawing_does_not_scroll(self):
        self.state.cursor_position = 2500
        editor = self.long_editor()  # checks that the view is at the top
        self.assertEqual(self.view_top(editor), 0)

    def test_short_sequence_needs_no_scroll_bar(self):
        editor = self.make_editor()
        for _ in range(5):
            wxapp.wx.Yield()
        self.assertFalse(editor.parent.HasScrollbar(wxapp.wx.VERTICAL))

    def test_selection_is_drawn(self):
        editor = self.make_editor()
        self.assertEqual(count_pixels(editor._Buffer, SELECTION_COLOUR), 0)
        self.state.dna_selection = (3, 12, -1)
        editor.update_ownUI()
        self.assertGreater(count_pixels(editor._Buffer, SELECTION_COLOUR), 100)

    def test_empty_file(self):
        self.state.gb = genbank.gbobject()
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
        from dnapy.gui import plasmid_GUI
        view = plasmid_GUI.PlasmidView2(self.frame, -1, self.state)
        self.frame.Show()
        view.update_ownUI()
        self.assertGreater(count_pixels(view.plasmid_view._Buffer), 500)


class TestFeatureList(GuiTestCase):
    def test_builds_and_updates(self):
        from dnapy.gui import featurelist_GUI
        panel = featurelist_GUI.FeatureList(self.frame, -1, self.state)
        panel.update_ownUI()


class TestMainWindow(GuiTestCase):
    def test_main_window_opens_with_a_file(self):
        from dnapy.gui import main
        window = main.DNApy(None, -1, 'DNApy')
        self.addCleanup(window.Destroy)
        window.state.open(genbank.gbobject(DATA))
        window.update_globalUI()
        window.Show()
        for _ in range(5):
            wxapp.wx.Yield()
        self.assertEqual(window.GetTitle(), 'NewFile - DNApy')


class TestSharedState(GuiTestCase):
    """The panels get their state handed to them, there are no global variables."""

    def test_two_editors_with_their_own_state_do_not_interfere(self):
        from dnapy.gui import dnaEditorCairo_GUI
        wx = wxapp.wx
        other = EditorState(genbank.gbobject())
        other.gb.Paste(1, 'GGGGCCCC')
        editors = []
        for state in (self.state, other):
            frame = wx.Frame(None, size=(900, 700))
            self.addCleanup(frame.Destroy)
            scroll = wx.ScrolledWindow(frame, wx.ID_ANY)
            scroll.SetScrollRate(1, 15)
            editors.append(dnaEditorCairo_GUI.TextEdit(scroll, wx.ID_ANY, state))
            frame.Show()
            editors[-1].update_ownUI()
        self.assertEqual(len(editors[0].dna), 95)
        self.assertEqual(editors[1].dna, 'GGGGCCCC')
        # a selection in one editor is not a selection in the other
        self.state.dna_selection = (3, 12, -1)
        self.assertEqual(other.dna_selection, (1, -1, -1))

    def test_the_genbank_module_holds_no_gui_state(self):
        from dnapy.gui import main
        window = main.DNApy(None, -1, 'DNApy')
        self.addCleanup(window.Destroy)
        window.state.open(genbank.gbobject(DATA))
        window.update_globalUI()
        for name in ('gb', 'dna_selection', 'feature_selection', 'cursor_position', 'search_hits'):
            self.assertFalse(hasattr(genbank, name), name)

    def test_opening_a_file_resets_the_selections(self):
        self.state.dna_selection = (3, 12, -1)
        self.state.feature_selection = 1
        self.state.cursor_position = 40
        self.state.search_hits = [(1, 3)]
        self.state.open(genbank.gbobject(DATA))
        self.assertEqual((self.state.dna_selection, self.state.feature_selection,
                          self.state.cursor_position, self.state.search_hits), ((1, -1, -1), False, 1, []))

    def test_dialogs_use_the_state(self):
        from dnapy.gui import featureedit_GUI, enzyme_GUI
        self.state.feature_selection = 0
        dialogs = [featureedit_GUI.FeatureEditDialog(None, 'Edit Feature', self.state),
                   enzyme_GUI.EnzymeSelectorDialog(None, 'Enzyme Selector', self.state),
                   enzyme_GUI.EnzymeDigestionDialog(None, 'digestion', self.state)]
        for dialog in dialogs:
            self.addCleanup(dialog.Destroy)


class TestToolbars(GuiTestCase):
    """The undo and redo buttons and the search bar of the main window."""

    def make_window(self, text=None):
        from dnapy.gui import main
        window = main.DNApy(None, -1, 'DNApy')
        self.addCleanup(window.Destroy)
        gb = genbank.gbobject()
        if text:
            gb.Paste(1, text)
            gb.reset_file_versions()
        else:
            gb = genbank.gbobject(DATA)
        window.state.open(gb)
        window.Show()
        window.update_globalUI()
        wxapp.wx.Yield()
        return window

    def click(self, button):
        wx = wxapp.wx
        event = wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId())
        event.SetEventObject(button)
        button.GetEventHandler().ProcessEvent(event)

    def choose_tool(self, window, tool_id):
        """Press a toggle tool of the main toolbar."""
        wx = wxapp.wx
        toolbar = window.frame_1_toolbar
        toolbar.ToggleTool(tool_id, not toolbar.GetToolState(tool_id))
        event = wx.CommandEvent(wx.wxEVT_TOOL, tool_id)
        event.SetEventObject(toolbar)
        window.ProcessEvent(event)
        wx.Yield()

    def choose_search_type(self, window, name):
        wx = wxapp.wx
        box = window.nucleotideoraminoacid
        box.SetSelection(box.FindString(name))
        event = wx.CommandEvent(wx.wxEVT_COMBOBOX, box.GetId())
        event.SetEventObject(box)
        window.ProcessEvent(event)

    def test_undo_and_redo_buttons_follow_the_history(self):
        window = self.make_window()
        toolbar = window.frame_1_toolbar
        enabled = lambda: (toolbar.UpdateWindowUI(), toolbar.GetToolEnabled(513), toolbar.GetToolEnabled(514))[1:]
        self.assertEqual(enabled(), (False, False))  # nothing to undo in a file that was just opened
        window.state.gb.Upper(1, 10)
        self.assertEqual(enabled(), (True, False))
        window.Undo(None)
        self.assertEqual(enabled(), (False, True))
        window.Redo(None)
        self.assertEqual(enabled(), (True, False))

    def test_undo_and_redo_menu_items_follow_the_history(self):
        window = self.make_window()
        edit_menu = window.GetMenuBar().GetMenu(2)

        def enabled():
            edit_menu.UpdateUI()
            return window.GetMenuBar().FindItemById(9).IsEnabled(), window.GetMenuBar().FindItemById(10).IsEnabled()
        self.assertEqual(enabled(), (False, False))
        window.state.gb.Upper(1, 10)
        self.assertEqual(enabled(), (True, False))

    def test_undo_button_restores_the_sequence(self):
        window = self.make_window()
        window.state.gb.Upper(1, 10)
        self.assertEqual(window.state.gb.GetDNA(1, 3), 'ATG')
        window.Undo(None)
        self.assertEqual(window.state.gb.GetDNA(1, 3), 'atg')

    def test_the_find_and_mutate_buttons_keep_their_own_icons(self):
        """Choosing Find disables Mutate (and the other way around), which used to show the other icon."""
        from dnapy import settings
        wx = wxapp.wx
        window = self.make_window()
        toolbar = window.frame_1_toolbar

        def pixels(bitmap):
            return bytes(bitmap.ConvertToImage().GetData()) if bitmap.IsOk() else None
        find_icon = pixels(wx.Bitmap(settings.get().icon('search.png'), wx.BITMAP_TYPE_ANY))
        mutate_icon = pixels(wx.Bitmap(settings.get().icon('mutate.png'), wx.BITMAP_TYPE_ANY))
        self.assertNotEqual(find_icon, mutate_icon)
        self.assertEqual(pixels(toolbar.FindById(511).GetNormalBitmap()), find_icon)
        self.assertEqual(pixels(toolbar.FindById(512).GetNormalBitmap()), mutate_icon)
        for tool_id in (511, 512):
            # no bitmap of its own for the disabled state: wx makes a grey copy of the icon of the tool itself
            self.assertFalse(toolbar.FindById(tool_id).GetDisabledBitmap().IsOk())

        self.choose_tool(window, 511)  # Find is chosen, Mutate is disabled
        self.assertFalse(toolbar.GetToolEnabled(512))
        self.assertEqual(pixels(toolbar.FindById(512).GetNormalBitmap()), mutate_icon)
        self.choose_tool(window, 511)
        self.assertTrue(toolbar.GetToolEnabled(512))
        self.choose_tool(window, 512)  # and the other way around
        self.assertFalse(toolbar.GetToolEnabled(511))
        self.assertEqual(pixels(toolbar.FindById(511).GetNormalBitmap()), find_icon)

    def test_search_bar_is_shown_and_hidden(self):
        window = self.make_window()
        self.assertFalse(window.frame_2_toolbar.IsShown())
        self.choose_tool(window, 511)  # Find
        self.assertTrue(window.frame_2_toolbar.IsShown())
        self.assertTrue(window.find_button.IsShown())
        self.assertFalse(window.mutate_button.IsShown())
        self.choose_tool(window, 511)
        self.assertFalse(window.frame_2_toolbar.IsShown())
        self.choose_tool(window, 512)  # Mutate
        self.assertTrue(window.mutate_button.IsShown())
        self.assertFalse(window.find_button.IsShown())

    def test_changing_the_kind_of_search_many_times_does_not_hang(self):
        # clearing the tools of a toolbar that holds controls used to hang the program on Windows
        window = self.make_window()
        self.choose_tool(window, 511)
        for _ in range(10):
            self.choose_search_type(window, 'Amino Acid')
            self.choose_search_type(window, 'Feature')
            self.choose_search_type(window, 'Nucleotide')
        self.assertEqual(window.nucleotideoraminoacid.GetValue(), 'Nucleotide')

    def test_options_depend_on_the_kind_of_search(self):
        window = self.make_window()
        self.choose_tool(window, 511)
        self.choose_search_type(window, 'Nucleotide')
        self.assertTrue(window.featurebox.IsShown())
        self.assertEqual(window.featurebox.GetStrings(), ['Molecule', 'test_cds', 'test_promoter'])  # the file has two features
        self.choose_search_type(window, 'Feature')
        self.assertFalse(window.featurebox.IsShown())

    def test_find_selects_the_first_hit(self):
        window = self.make_window()
        self.choose_tool(window, 511)
        window.searchinput.SetValue('GGATCC')
        self.click(window.find_button)
        self.assertEqual(window.state.search_hits, [(13, 18)])
        self.assertEqual(window.state.dna_selection, (13, 18, -1))

    def test_find_next_and_previous_go_through_the_hits(self):
        window = self.make_window('AAGGATCCTTGGATCCTTGGATCC')  # GGATCC at 3, 11 and 19
        self.choose_tool(window, 511)
        window.searchinput.SetValue('GGATCC')
        self.click(window.find_button)
        starts = lambda: window.state.dna_selection[0]
        self.assertEqual(starts(), 3)
        self.click(window.find_next_button)
        self.assertEqual(starts(), 11)
        self.click(window.find_next_button)
        self.assertEqual(starts(), 19)
        self.click(window.find_next_button)  # after the last one it starts again at the first
        self.assertEqual(starts(), 3)
        self.click(window.find_previous_button)  # and before the first one it goes to the last
        self.assertEqual(starts(), 19)
        self.click(window.find_previous_button)
        self.assertEqual(starts(), 11)

    def test_find_scrolls_the_sequence_to_the_hit(self):
        # GGATCC at the very beginning and at the very end of a long sequence
        window = self.make_window('GGATCC' + 'A' * 2900 + 'GGATCC')
        editor = window.DNApy.dnaview
        scroll = editor.parent
        for _ in range(5):
            wxapp.wx.Yield()
        top = lambda: scroll.GetViewStart()[1] * scroll.GetScrollPixelsPerUnit()[1]
        self.choose_tool(window, 511)
        window.searchinput.SetValue('GGATCC')
        self.click(window.find_button)
        self.assertEqual(window.state.dna_selection[0], 1)
        self.assertEqual(top(), 0)  # the first hit is at the top
        self.click(window.find_next_button)  # the hit at the end, far below the window
        self.assertEqual(window.state.dna_selection[0], 2907)
        self.assertGreater(top(), 0)
        y = editor.sY + editor.senseLayout.index_to_pos(2906)[1]
        self.assertTrue(top() <= y and y + 2 * editor.senseLayout.text_height <= top() + scroll.GetClientSize()[1])
        self.click(window.find_next_button)  # wraps around to the first hit
        self.assertEqual(top(), 0)
        self.click(window.find_previous_button)  # and back to the last one
        self.assertGreater(top(), 0)

    def test_find_a_feature_by_name(self):
        window = self.make_window()
        self.choose_tool(window, 511)
        self.choose_search_type(window, 'Feature')
        window.searchinput.SetValue('test_promoter')
        self.click(window.find_button)
        self.assertEqual(window.state.dna_selection[:2], (40, 55))

    def test_find_without_a_hit_keeps_the_selection(self):
        window = self.make_window()
        self.choose_tool(window, 511)
        window.searchinput.SetValue('TTTTTTTTTTTT')
        self.click(window.find_button)
        self.assertEqual(window.state.search_hits, [])
        self.assertEqual(window.state.dna_selection, (1, -1, -1))

    def test_mutate(self):
        window = self.make_window()
        self.choose_tool(window, 512)
        self.choose_search_type(window, 'Nucleotide')
        window.searchinput.SetValue('A1C')
        self.click(window.mutate_button)
        self.assertEqual(window.state.gb.GetDNA(1, 3).lower(), 'ctg')


class TestUserSettings(GuiTestCase):
    """The GUI uses the settings, so a user file changes how it looks."""

    def use_settings(self, text):
        from unittest import mock
        from dnapy import settings
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, 'user.toml')
        with open(path, 'w') as f:
            f.write(text)
        patcher = mock.patch.object(settings, '_current', settings.load(path))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_window_size(self):
        from dnapy.gui import main
        self.use_settings('[window]\nsize = [900, 500]\n')
        window = main.DNApy(None, -1, 'DNApy')
        self.addCleanup(window.Destroy)
        self.assertEqual(tuple(window.GetSize()), (900, 500))

    def test_feature_colour_in_the_editor(self):
        from dnapy.gui import dnaEditorCairo_GUI
        wx = wxapp.wx

        def count_cds_bar_pixels(colour):
            frame = wx.Frame(None, size=(900, 700))
            self.addCleanup(frame.Destroy)
            scroll = wx.ScrolledWindow(frame, wx.ID_ANY)
            scroll.SetScrollRate(1, 15)
            editor = dnaEditorCairo_GUI.TextEdit(scroll, wx.ID_ANY, self.state)
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
        from dnapy.gui import main
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
                window.state.open(genbank.gbobject(path))
                window.state.dna_selection = (3, 20, -1)
                window.state.feature_selection = 0
                window.update_globalUI()
                event = wx.CommandEvent(wx.EVT_MENU.typeId, item_id)
                event.SetEventObject(window)
                window.ProcessEvent(event)
                for _ in range(3):
                    wx.Yield()
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
