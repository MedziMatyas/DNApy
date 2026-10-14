# -*- coding: utf-8 -*-


__title__ = 'DNApy'
__version__ = '0.2.0'
__desc__ = 'DNA plasmid editing'
__license__ = 'GNU General Public License v3 or later (GPL3+)'
__url__ = 'https://github.com/MedziMatyas/DNApy'

import logging
import os

try:
    # Try systemwide installation and fallback to included
    import pyperclip
except ImportError:
    from .external import pyperclip

# Folders. The data files (enzyme list, DNA ladders, icons) are part of the package, so they are found
# wherever the package is installed.
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_SETTINGS_DIR = os.path.join(ROOT_DIR, "defaults")
DATA_DIR = os.path.join(ROOT_DIR, "data")
ICONS_DIR = os.path.join(DATA_DIR, "icons")

# The folder of the user, for settings and for things the user adds (such as DNA ladders).
# The files in the package are not changed, since it can be installed in a place that is read-only.
USER_DIR = os.path.join(os.path.expanduser("~"), ".dnapy")

logging.getLogger(__name__).addHandler(logging.NullHandler())
