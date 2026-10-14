# DNApy: summary

## What it is
DNApy is a GPL3 desktop GUI for viewing and editing DNA in GenBank format. It's aimed at molecular and synthetic biology work, in the spirit of ApE or SnapGene. Martin Engqvist wrote it in 2014–15. The last commit is from August 2019.

## What it should do
These features are implemented, according to the README:
- A DNA sequence editor drawn with Cairo, with feature annotations.
- A circular plasmid map that also shows restriction sites.
- Editing with copy/paste, reverse complement, and unlimited undo/redo.
- Search by nucleotide or amino-acid position or sequence.
- Mutation by nucleotide or amino-acid position.
- A mixed-base codon designer for libraries.
- DNA-to-protein translation.
- Add, remove and edit GenBank features and qualifiers.
- Restriction enzyme finder, partly done.

These are listed as not implemented: ab1 trace reading, codon optimization, NCBI fetch and BLAST, primer design, PCR simulation, and multiple sequence alignment.

## Layout (~20k lines)
- **`src/` core logic, no GUI:**
  - `genbank.py` (2.3k lines) is the GenBank parser and data model.
  - `dna.py` holds translation, reverse complement, ambiguity codes and codon tables.
  - `protein.py`, `enzyme.py`, `mixed_base_codons.py`, `oligo_localizer.py` and `peptide_localizer.py` cover the rest.
- **`src/gui/`:**
  - `main.py` is the entry point. It glues together the Cairo DNA editor, the plasmid view, the feature list and edit dialogs, and the enzyme dialog.
  - The other GUI modules are one per panel or dialog.
  - They are built on wxPython and pycairo, and communicate through `wx.lib.pubsub`.
- **`src/external/`:** vendored third-party code: pyperclip, ABI/SCF/ZTR trace readers, MUSCLE wrapper, Needleman-Wunsch.
- **`src/defaults/`:** `settings.toml` (the default settings, see Configuration below). `english` and `errors` are unused text files left over from another project.
- **Other folders:**
  - `src/other/` and `src/resources/` hold experimental code and parsers such as fasta and fastq.
  - `resources/` holds enzyme lists and DNA ladders.
  - `docs/` holds GenBank feature and qualifier reference text.
  - `icon/` holds the icons.

## Why it was broken (original state, before the Python 3 port)
The repo history explains it: a commit titled "Reorganize folder structure, break everything" was followed by "run 2to3 on entire project". The code was moved into a new layout and run through 2to3 without being finished. The README itself says "This repo is currently broken."

1. **Missing dependencies.** Neither `wx` nor `cairo` is installed. The environment has Python 3.14, and the code was written for Python 2.7 with wxPython 2.8/GTK.
2. **Removed or Python 2 APIs.**
   - `wx.lib.pubsub` with `setupkwargs` is gone from modern wxPython.
   - `string.replace(...)` is still in `main.py`.
   - `pango`/`pangocairo` are Python 2 GTK bindings.
   - `import pyalign`, `SequenceTrace` and `ABIreader` refer to modules that don't exist in this layout.
3. **Broken imports after the reorganization.**
   - Modules use flat imports (`import dna`, `import genbank`, `from base_class import ...`). Others use relative ones (`from . import dna`, `from . import protein`).
   - `import fasta` in `dna.py` now points at `src/resources/`.
4. **Wrong paths.**
   - `main.py` loads config from `sys.argv[0]`'s directory, so it looks for `variables` and `settings` next to `gui/main.py`. They now live in `src/defaults/`.
   - `ICONS_DIR` in `src/__init__.py` points at `gui/icon`, but the icons are in the top-level `icon/`.
   - The default file path in `settings` is `/home/martin/...`.
5. **Packaging.**
   - `setup.py` reads `HISTORY.md`, which doesn't exist.
   - Its entry point refers to `DNApy.gui.main_GUI:startgui`, which doesn't exist either.
   - The README still says `python main.py` from the repo root.

## Suggested path
The non-GUI core (`dna`, `genbank`, `protein`, `enzyme`) looks closest to working and is easy to test headlessly. A sensible order would be:
1. Make the core importable on Python 3 and add tests.
2. Port the GUI to a current wxPython (Phoenix) with pycairo.
3. Replace the `exec()`-based config loading.

## Work done so far

### Core ported to Python 3 and tested
- `src` is now an importable package (`__init__.py` added to `external`, `gui`, `other`, `resources`) and imports are package-relative.
- `dna`, `protein`, `genbank`, `enzyme`, `mixed_base_codons`, the localizers and the fasta parser work on Python 3. `genbank.py` and `enzyme.py` no longer need wxPython to be imported.
- Python 3 fixes: `None` comparisons in `mixed_base_codons.py`, bytes for the wx clipboard in `genbank.py`, removed `string.*` functions, tab/space mixes in three GUI files, a stray parenthesis in `src/other/seqfiles.py`.
- Also fixed: a typo (`ncut52`) in `enzyme.py` that crashed for enzymes with two cuts.
- The enzyme list (`resources/emboss_e.txt`) is located relative to the package, not the working directory.
- Unit tests in `tests/` cover the core (170 tests including the GUI smoke tests), using the fixture `tests/data/test_plasmid.gb`. Run them with:

```
python -m unittest discover -s tests -t .
```

### Bugs fixed (they had been recorded as expected failures)
- **Undo/redo:** the loaded file was never stored as a version, so the first edit could not be undone. Undo and redo also handed out the stored version itself, so later edits changed the history, and an edit after an undo broke the version list. Now the loaded (or new, empty) file is the first version, undo and redo work on copies, an edit after an undo discards what could have been redone, the restriction sites are recalculated and the file path is kept. `Undo()` and `Redo()` return whether anything happened, and the debug prints are gone.
- **Restriction sites** in the first 100 bp of a circular sequence were reported twice (once more in the copy of the start that is added to find sites over the origin). While there, positions were fixed for a site that ends at the last base (it was reported as ending at 0) or starts at the last base.
- **Taxonomy** lost its spaces when a file was read ("other sequences" became "othersequences") and so was written back wrong. Names are now kept with single spaces, and wrapped lines work.

### GUI: ported, launches and draws
Start it from the repository root with `python -m src.gui.main`.
- Package-relative imports, `src/gui/compat.py` (pubsub import), wxPython 4 API changes (`Add(item=...)`, `AddTool`, `AddCheckTool`, `wx.FD_OPEN`/`wx.FD_SAVE`, `wx.Bitmap`, `wx.NewIdRef`, int sash position).
- **Pango removed from the DNA editor.** Text layout now lives in `src/gui/monolayout.py`: a pure-arithmetic layout for monospaced text (wrapping, index to position, position to index, selection rectangles), covered by `tests/test_monolayout.py`. The editor draws the strands with Cairo glyphs on a fixed grid, and the selection as filled rectangles behind the text. A monospaced font is picked by measuring glyph widths (Cairo's "monospace" alias resolves to a proportional font on Windows).
- **Drawing target changed.** The editor and the plasmid view now draw on a `cairo.ImageSurface` and convert it to the `wx.Bitmap` (`BitmapFromImageSurface`). Drawing on a device context (`ContextFromDC`) mixed GDI and Cairo output on Windows, so text and shapes overwrote each other.
- Plasmid view: the canvas scaling now happens when the context is created (`normalizeCanvas`), before the label calculations that depend on it (previously they used the context of the previous repaint).
- Fixes found on the way: hashing needs bytes, a resize feedback loop in the editor (the editor and its scroll window kept resizing each other), a zero-size bitmap assertion, and an extra tick label drawn for a non-existing line.
- Features in the editor are now drawn offset by the text border, so they line up with their bases.
- GUI smoke tests in `tests/test_gui_smoke.py` build the editor, plasmid view, feature list and main window with a loaded file (skipped if wxPython or pycairo are missing).
- The deprecated `wx.EVT_MENU(...)`/`wx.EVT_TOOL(...)`/`wx.EVT_COMBOBOX(...)` calls in `main.py` were replaced by `Bind`, which removed the deprecation warnings.
- Menu handlers fixed after a first manual run: `wx.FD_FILE_MUST_EXIST`/`wx.FD_OVERWRITE_PROMPT`, File > New (it started another instance with a Linux-only command), file names with several dots, Enzymes > Digest, the Protein menu (3-value selection, output window, translate feature), the mixed base codon dialog (import, scrollbar call, window added to a sizer twice), and the plasmid label arrangement with no labels.
- Opening a real-world file (NEB pUC19) exposed more problems, now fixed: the file dialog filter (`*` instead of `*.gb;*.gbk`), the parser rejecting an empty `VERSION` line, feature keys starting with `-` (`-35_signal`, `-10_signal`) being dropped, and feature colours looked up with `eval()` on the key, which crashes for keys that are not valid Python names. Colours now come from `config.feature_colour()`, which maps such keys (`-35_signal` to `a35_signal`, `5'UTR` to `a5UTR`) and falls back to grey. The open dialog now starts in the current working directory.
- Flicker on every selection change: the drawing panels erased their background before each paint (6 erase events per update in the editor). They now use `wx.BG_STYLE_PAINT` with a no-op erase handler and `Refresh(False)`, since the buffer covers the whole panel.
- Scroll bar for the sequence view: the editor was inside a scroll window with a sizer, which kept resizing the editor to the visible area, so there was never anything to scroll. The sizer is gone; the editor now wraps the text first (`layoutText`), then sets its own height and the scroll window's virtual size to fit all lines, and the scroll window shows a vertical scroll bar. Room for the bar is always reserved (its appearance changes the client size without a resize event), the editor follows the size of the scroll window, and mouse wheel events are forwarded to the scroll window.
- Keyboard input in the editor: `GetUniChar()` no longer exists, `GetUnicodeKey()` is used (with the key code for non-character keys such as the arrows). Typing bases, arrow keys, backspace and delete, and mouse clicking, dragging and hit testing are covered by smoke tests with synthetic events.
- Known cosmetic issue: on the plasmid map, long labels are cut off at the edge of the panel.
- `tests/test_gui_smoke.py` also fires every menu item with a file loaded and a selection made (dialogs are cancelled) and fails on any exception.
- **Not yet verified by hand:** clicking, dragging a selection, typing, and what the dialogs do when confirmed (open/save, feature edit, enzyme selection and digestion). The menu test only starts the handlers.

### Configuration
Settings are read from TOML files by `src/settings.py` (no code is executed, no wxPython needed):
- `src/defaults/settings.toml` holds the defaults: main window size, the folder where file dialogs start (empty means the current folder), the named colors, and which color each GenBank feature type gets (keys like `"-35_signal"` and `"5'UTR"` are written as they appear in GenBank files).
- To change something, write only the entries to change into `~/.dnapy/settings.toml`, or into the file named by the environment variable `DNAPY_SETTINGS`. They replace the defaults, everything else keeps its default value.
- The settings are validated when loaded (window size, `#rrggbb` colors, color names used by features) and errors say which entry is wrong.
- In the code: `from src import settings` and `settings.get().window_size`, `settings.get().feature_colour('CDS')`, `settings.get().icon('new.png')`.
- This replaced Python files (`settings`, `variables`, `font`) that were executed with `exec()` into the globals of each GUI module. The unused values in them were dropped (`extensions`, `faces`, the dead `size` file that nothing could write).

### Dependencies
`wxPython` 4.x and `pycairo` are required. `PyPubSub` is recommended (the code falls back to wxPython's deprecated copy). `pyperclip` is vendored.

## TODO

1. **Revisit the text rendering and the drawing stack.** Pango was dropped for now (see above) and replaced by a simple monospaced grid on Cairo's basic text API. That is enough for DNA, but it has no advanced shaping or kerning, and the labels (feature names, enzyme names, ticks) still use Cairo's basic text API with Arial. Decide later whether to keep Cairo, move to `wx.GraphicsContext` (drops pycairo, but the plasmid drawing code is written against the Cairo API), or use another toolkit. Also look at the font choice (Consolas, then DejaVu Sans Mono, Courier New, ...) and at high-DPI scaling.
2. **Try the GUI by hand and fix what breaks:** mouse selection and clicking on features, keyboard input, menus, dialogs (open/save, feature edit, enzyme selection and digestion), undo/redo. Replace the deprecated `wx.EVT_TOOL(...)`/`wx.EVT_*` calls with `Bind`, and check wx calls for float vs int arguments. `open_file` splits the file name on `.` and fails for names with several dots.
3. **Remove the app-wide mutable state** stored on the `genbank` module (`genbank.gb`, `dna_selection`, `feature_selection`, `cursor_position`, `search_hits`). It is initialized in `main.py` and makes the GUI hard to test.
4. **Extend the GUI tests**: smoke tests exist for the editor, plasmid view, feature list and main window. Missing: the other dialogs and panels, and simulated mouse and keyboard input.
5. **Packaging and docs:** fix `setup.py` (missing `HISTORY.md`, wrong entry point), add a requirements file, and update the README (it still describes Python 2.7 and `python main.py`).
6. **Large sequences in the editor.** The editor keeps one bitmap as tall as the whole sequence (about 95 pixels per line), so memory use and bitmap size limits will be a problem for sequences of tens or hundreds of kilobases. Draw only the visible part instead. The cursor also does not scroll into view yet when it moves with the keyboard.
7. **Clean up** `src/other/` (unused, partly broken legacy code), the unused `src/defaults/english` and `errors` files, the leftover debug `print` calls (for example in `peptide_localizer.py` and `Undo`), and the `/home/martin/...` default path in `src/defaults/settings`.
8. Longer term: the unimplemented features from the README (ab1 trace analysis, codon optimization, NCBI fetch, primer design, PCR simulation, alignment).
