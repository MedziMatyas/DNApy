import unittest

from dnapy.gui.monolayout import MonoLayout


def layout(length=25, width=100):
    # 10 px wide characters, 10 characters per line, lines 15 px high with 80 px between them
    return MonoLayout(length, char_width=10, text_height=15, spacing=80, width=width)


class TestMonoLayout(unittest.TestCase):
    def test_line_length_and_count(self):
        lay = layout()
        self.assertEqual(lay.line_length, 10)
        self.assertEqual(lay.line_count, 3)
        self.assertEqual(lay.line_height, 95)

    def test_exactly_full_lines(self):
        self.assertEqual(layout(length=20).line_count, 2)

    def test_empty_text_has_one_line(self):
        self.assertEqual(layout(length=0).line_count, 1)

    def test_narrow_window_still_fits_one_character(self):
        self.assertEqual(layout(width=3).line_length, 1)

    def test_index_to_pos(self):
        lay = layout()
        self.assertEqual(lay.index_to_pos(0), (0, 0, 10, 15))
        self.assertEqual(lay.index_to_pos(3), (30, 0, 10, 15))
        self.assertEqual(lay.index_to_pos(10), (0, 95, 10, 15))
        self.assertEqual(lay.index_to_pos(24), (40, 190, 10, 15))

    def test_end_of_text_stays_on_the_last_line(self):
        self.assertEqual(layout(length=25).index_to_pos(25)[:2], (50, 190))
        self.assertEqual(layout(length=20).index_to_pos(20)[:2], (100, 95))

    def test_index_beyond_the_text_is_clamped(self):
        self.assertEqual(layout().index_to_pos(1000), layout().index_to_pos(25))

    def test_pixel_size(self):
        self.assertEqual(layout().pixel_size, (100, 3 * 15 + 2 * 80))

    def test_xy_to_index_left_and_right_half_of_a_character(self):
        lay = layout()
        self.assertEqual(lay.xy_to_index(32, 5), (3, 0))
        self.assertEqual(lay.xy_to_index(37, 5), (3, 1))

    def test_xy_to_index_picks_the_nearest_line(self):
        lay = layout()
        self.assertEqual(lay.xy_to_index(5, 95 + 5)[0], 10)
        # in the gap above the second line (where features are drawn), nearer to line 2 than to line 1
        self.assertEqual(lay.xy_to_index(5, 95 - 10)[0], 10)
        # in the gap just below the first line
        self.assertEqual(lay.xy_to_index(5, 30)[0], 0)

    def test_xy_to_index_outside_the_text(self):
        lay = layout()
        self.assertEqual(lay.xy_to_index(-20, -20), (0, 0))
        self.assertEqual(lay.xy_to_index(500, 5), (9, 1))
        self.assertEqual(lay.xy_to_index(500, 5000), (24, 1))  # last line is only 5 characters long

    def test_xy_to_index_without_text(self):
        self.assertFalse(layout(length=0).xy_to_index(0, 0))

    def test_index_to_pos_and_back(self):
        lay = layout()
        for index in range(25):
            x, y, w, h = lay.index_to_pos(index)
            self.assertEqual(lay.xy_to_index(x + 1, y + 1), (index, 0))

    def test_span_rects_within_a_line(self):
        self.assertEqual(layout().span_rects(2, 5), [(20, 0, 30, 15)])

    def test_span_rects_over_several_lines(self):
        self.assertEqual(layout().span_rects(8, 22),
                         [(80, 0, 20, 15), (0, 95, 100, 15), (0, 190, 20, 15)])

    def test_span_rects_empty_and_clipped(self):
        self.assertEqual(layout().span_rects(5, 5), [])
        self.assertEqual(layout().span_rects(23, 100), [(30, 190, 20, 15)])


if __name__ == '__main__':
    unittest.main()
