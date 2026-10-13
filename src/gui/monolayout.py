"""
Layout of a monospaced text (such as a DNA sequence) that wraps at a fixed number of characters per line.

This replaces the small part of Pango that the DNA editor used: wrapping text into lines, mapping a
character index to a position and a position back to a character index. Because every character has the
same width the layout is plain arithmetic, so it does not need a text-shaping library, and it can be
tested without a GUI.

All coordinates are in pixels and relative to the top left corner of the layout.
"""

# Fonts to try, in order. The "monospace" alias of Cairo's built-in text API is not reliably monospaced
# (on Windows it resolves to a proportional font), so a font is only accepted if its glyphs have equal widths.
MONOSPACE_FONTS = ('Consolas', 'DejaVu Sans Mono', 'Courier New', 'Lucida Console', 'Liberation Mono', 'monospace')


def select_monospace_font(ctx, size, fonts=MONOSPACE_FONTS):
    """Select the first genuinely monospaced font of `fonts` in the Cairo context and set its size (in pixels)."""
    import cairo
    for family in fonts:
        ctx.select_font_face(family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(size)
        if abs(ctx.text_extents('M')[4] - ctx.text_extents('i')[4]) < 0.01:
            return family
    return fonts[-1]


class MonoLayout(object):
    """
    Wraps `length` characters of width `char_width` into lines that fit in `width` pixels.
    Consecutive lines are `text_height + spacing` pixels apart.
    """
    def __init__(self, length, char_width, text_height, spacing, width):
        assert char_width > 0, 'The character width must be positive.'
        self.length = length
        self.char_width = float(char_width)
        self.text_height = float(text_height)
        self.spacing = float(spacing)
        self.line_height = self.text_height + self.spacing  # distance between the tops of two lines
        self.line_length = max(1, int(width // self.char_width))  # characters per line

    @property
    def line_count(self):
        if self.length == 0:
            return 1
        return (self.length - 1) // self.line_length + 1

    @property
    def pixel_size(self):
        """Width and height of the whole text."""
        width = min(self.length, self.line_length) * self.char_width
        height = self.line_count * self.text_height + (self.line_count - 1) * self.spacing
        return width, height

    def index_to_pos(self, index):
        """
        Rectangle (x, y, width, height) of the character with the 0-based `index`.
        An index at or beyond the end of the text gives the position just after the last character.
        """
        index = max(0, min(index, self.length))
        if index == self.length and self.length > 0:
            line = (self.length - 1) // self.line_length  # the end of the text stays on the last line
        else:
            line = index // self.line_length
        column = index - line * self.line_length
        return column * self.char_width, line * self.line_height, self.char_width, self.text_height

    def xy_to_index(self, x, y):
        """
        Character at the position (x, y) as (index, trailing), where trailing is 1 if the position is in the
        right half of the character and 0 if it is in the left half. Positions outside of the text are moved to
        the nearest character. Returns False if there is no text.
        """
        if self.length == 0:
            return False
        line = int(round((y - self.text_height / 2.0) / self.line_height))  # nearest line
        line = max(0, min(line, self.line_count - 1))
        first = line * self.line_length
        last = min(first + self.line_length, self.length) - 1
        column = x / self.char_width
        if column < 0:
            return first, 0
        index = first + int(column)
        if index > last:
            return last, 1
        return index, (1 if column - int(column) >= 0.5 else 0)

    def span_rects(self, start, end):
        """Rectangles (x, y, width, height), one per line, covering the characters start <= index < end."""
        start = max(0, start)
        end = min(end, self.length)
        rects = []
        while start < end:
            x, y, w, h = self.index_to_pos(start)
            line = start // self.line_length
            stop = min(end, (line + 1) * self.line_length)
            rects.append((x, y, (stop - start) * self.char_width, h))
            start = stop
        return rects
