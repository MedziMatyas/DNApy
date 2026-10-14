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

## Layout (current)
The program is the package `dnapy`. It was called `src` until it was packaged; the history below uses the old names (`src/gui/main.py` is now `dnapy/gui/main.py`).
- **`dnapy/` core logic, no GUI:**
  - `genbank.py` (2.3k lines) is the GenBank parser and data model.
  - `dna.py` holds translation, reverse complement, ambiguity codes and codon tables.
  - `protein.py`, `enzyme.py`, `mixed_base_codons.py`, `oligo_localizer.py`, `peptide_localizer.py` and `ladders.py` cover the rest; `settings.py` reads the settings.
  - `parsers/` has the fasta, fastq and fastv readers (only fasta is used).
- **`dnapy/gui/`:**
  - `main.py` is the entry point (`main()`); `python -m dnapy` and the `dnapy` command run it. It glues together the Cairo DNA editor, the plasmid view, the feature list and edit dialogs, and the enzyme dialog.
  - The other GUI modules are one per panel or dialog, `state.py` holds what they share, `monolayout.py` is the text layout of the editor.
  - They are built on wxPython and pycairo, and communicate through PyPubSub.
- **`dnapy/data/`:** the restriction enzyme list (`emboss_e.txt`), the list of commercial enzymes, the DNA ladders and the icons (`icons/`). These are package data, so they are installed with the program.
- **`dnapy/defaults/settings.toml`:** the default settings (see Configuration below).
- **`dnapy/external/`:** vendored third-party code: pyperclip (used), ABI/SCF/ZTR trace readers, MUSCLE wrapper, Needleman-Wunsch (unused so far, for the features that are not implemented).
- **Top level:** `pyproject.toml` (packaging), `tests/`, `docs/` (GenBank feature and qualifier reference text, `images/` for the README).

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
- Unit tests in `tests/` cover the core (226 tests including the GUI smoke tests), using the fixture `tests/data/test_plasmid.gb`. Run them with:

```
python -m unittest discover -s tests -t .
```

### Bugs fixed (they had been recorded as expected failures)
- **Undo/redo:** the loaded file was never stored as a version, so the first edit could not be undone. Undo and redo also handed out the stored version itself, so later edits changed the history, and an edit after an undo broke the version list. Now the loaded (or new, empty) file is the first version, undo and redo work on copies, an edit after an undo discards what could have been redone, the restriction sites are recalculated and the file path is kept. `Undo()` and `Redo()` return whether anything happened, and the debug prints are gone.
- **Restriction sites** in the first 100 bp of a circular sequence were reported twice (once more in the copy of the start that is added to find sites over the origin). While there, positions were fixed for a site that ends at the last base (it was reported as ending at 0) or starts at the last base.
- **Taxonomy** lost its spaces when a file was read ("other sequences" became "othersequences") and so was written back wrong. Names are now kept with single spaces, and wrapped lines work.

### GUI: ported, launches and draws
Start it with `python -m dnapy` (or the `dnapy` command after `pip install .`).
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
- **No more global state.** The open file and the selections used to be attributes of the `genbank` module (`genbank.gb`, `dna_selection`, `feature_selection`, `cursor_position`, `search_hits`), set by the main window and read from everywhere. They now live in an `EditorState` object (`src/gui/state.py`, no wxPython needed). The main window makes one and hands it to every panel and dialog it creates (`TextEdit`, `PlasmidView2`/`drawPlasmid`, `FeatureList`, `FeatureEdit`/`FeatureEditDialog`, `EnzymeSelectorDialog`, `EnzymeDigestionDialog`, `MyPanel`), which use it as `self.state`. `state.open(gbobject)` makes a file the open one and resets the selections. Two windows can now show different files without interfering, and tests no longer have to set module attributes. The `genbank` module holds no GUI state at all.
- Removed with it: the old STC-based editor `dnaeditor_GUI.py` (unused since the Cairo editor replaced it) and the standalone test runners at the end of three GUI modules (they could not run any more, since the modules use package-relative imports).
- **Undo and redo buttons did nothing**: they were disabled when the window was made and nothing ever enabled them again. They (and the Undo and Redo menu items) now follow the history through wx update-UI events, so they are enabled exactly when there is something to undo or redo. The status bar handler, which receives every update event of the window, now passes them on.
- **Find and Mutate froze the program on Windows.** The bar with the search controls was a `wx.ToolBar` with a combo box and text boxes inside, and the code cleared and rebuilt its tools every time an option changed; clearing a toolbar that holds controls never finishes on Windows (`TB_DELETEBUTTON failed` in a loop). The bar is now a plain panel whose controls are made once and only shown, hidden and filled. `find_next` also crashed (it unpacked the three-part selection into two values).
- Search fixes in `genbank.py`: searching in a file without features (a new file) crashed, `FindFeature` returned positions that started one too early, features with a qualifier without a value (such as `/pseudo`) broke it, and a feature label that contains `=` was cut off. Features without a label are listed by their type in the search bar.
- **Cursor and undo/redo.** The cursor did not move when an edit was undone or redone, so it ended up in the wrong place in the changed sequence. Each history step now remembers the cursor position before and after the edit (`gbobject.set_version_cursors`, filled in by the editor through `EditorState.record_edit`). `EditorState.undo()` puts the cursor where it was before the undone edit, `redo()` where it was after the redone one, and both clear the selection and keep the cursor inside the sequence. The editor's cursor (`PositionPointer`) is now the shared `state.cursor_position`, so the plasmid view, status bar and undo see the same one. Typing, backspace, delete, cut and paste record the cursor; edits that do not (upper/lower case, mutations, feature edits) leave the cursor where it is on undo.
- Editing fixes found while testing this: typing over a selection and backspace with a selection left the first selected base in place and typed at the old cursor; backspace at the start and delete at the end of the sequence did something odd; delete and cut-reverse-complement did not move the cursor to the start of the removed text.
- **The sequence view scrolls to what moved.** A search hit that was outside the window stayed out of sight. After each drawing the editor now checks whether the selection or the cursor changed since the last one (a search hit, a clicked feature, undo and redo, a click on the plasmid map, typing, the arrow keys) and scrolls the window as little as needed to show the lines involved; if a selection is longer than the window, the line where it starts is shown. Nothing scrolls if the new position is already in view, and the first drawing does not scroll. This also covers the earlier TODO that the cursor did not scroll into view.
- Known cosmetic issue: on the plasmid map, long labels are cut off at the edge of the panel.
- `tests/test_gui_smoke.py` also fires every menu item with a file loaded and a selection made (dialogs are cancelled) and fails on any exception.
- **Not yet verified by hand:** clicking, dragging a selection, typing, and what the dialogs do when confirmed (open/save, feature edit, enzyme selection and digestion). The menu test only starts the handlers.

### Clean-up and packaging
- **Package renamed** from `src` to `dnapy`, and the data moved inside it (`icon/` is now `dnapy/data/icons/`, the files of `resources/` are in `dnapy/data/`, the Python parsers that were in `src/resources/` are `dnapy/parsers/`). The program finds them relative to the package, not to the working directory (the enzyme list used to be opened as `resources/emboss_e.txt`, which only worked when started from the repository root).
- **`pyproject.toml`** replaces the broken `setup.py`. `pip install .` builds and installs the package with its dependencies (wxPython, pycairo, PyPubSub), including the data files and the settings, and creates the `dnapy` command (a GUI script, so there is no console window on Windows). The version is read from `dnapy.__version__` (now 0.2.0). A built wheel was installed into an empty folder and started from there to check that nothing depends on the repository. `tests/test_data_files.py` checks that every file in the data folders is covered by the patterns in `pyproject.toml`.
- **DNA ladders** that a user adds are now saved in `~/.dnapy/dnaLadders.lst` (new module `ladders.py`, with tests) instead of being appended to the file in the program folder, which would fail in an installed program.
- **Removed:** `src/other/` (the unused legacy code: `seqfiles*.py`, `CWdraw.py`, `wsvg.py`), the unused `english` and `errors` files, the old Python-syntax `settings` file, and the outdated `resources/Screenshot.png`. `colcol.py` (colors), which was in `other/`, is now `dnapy/gui/colcol.py`.
- **Debug output:** the `print` calls in the core were replaced by `logging` (loggers named after the modules, for example `dnapy.genbank`); `dnapy.gui.main.main()` shows messages of level INFO and higher on the console. The leftover debugging prints (`'keypress'`, `'filever index'`, ...) are gone. Choosing a file that is not a GenBank file now shows a message box, and `.gbk` files are opened too.

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
2. **Plasmid map export is missing:** File > Export plasmid map calls `drawPlasmid.exportMapAs`, which does not exist (the menu test cancels the dialog, so it did not notice). Implement the SVG export, for example by drawing the map on a `cairo.SVGSurface`, and add a test that exports to a temporary file.
3. **Try the GUI by hand and fix what breaks:** mouse selection and clicking on features, keyboard input, menus, dialogs (open/save, feature edit, enzyme selection and digestion), undo/redo. Replace the deprecated `wx.EVT_TOOL(...)`/`wx.EVT_*` calls with `Bind`, and check wx calls for float vs int arguments. `open_file` splits the file name on `.` and fails for names with several dots.
4. **Extend the GUI tests**: smoke tests exist for the editor, plasmid view, feature list and main window. Missing: the other dialogs and panels, and simulated mouse and keyboard input.
5. **Large sequences in the editor.** The editor keeps one bitmap as tall as the whole sequence (about 95 pixels per line), so memory use and bitmap size limits will be a problem for sequences of tens or hundreds of kilobases. Draw only the visible part instead.
6. **Leftovers:** the code in `dnapy/external/` for the features that are not implemented has never been run on Python 3, and the GUI modules still contain a lot of commented-out code.
7. Longer term: the features listed as not implemented in the README (ab1 trace analysis, codon optimization, NCBI fetch, primer design, PCR simulation, alignment).
