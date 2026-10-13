"""
Loading of the Python-syntax configuration files in src/defaults (settings, variables, font).

The GUI modules expect the names defined in those files (colors, windowsize, faces, ...) as globals,
so load_defaults() executes the files into the namespace of the calling module.
"""
import os

import wx

from .. import DEFAULT_SETTINGS_DIR

# the repository root, which holds the icon folder
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def load_defaults(namespace, variables=False):
    """Populate `namespace` (a module's globals()) with the default settings, and optionally the variables."""
    files = namespace.setdefault('files', {})
    files['default_dir'] = ROOT_DIR.replace(os.sep, '/') + '/'
    files['settings_dir'] = DEFAULT_SETTINGS_DIR
    namespace.setdefault('wx', wx)
    namespace.setdefault('os', os)

    names = ['variables', 'settings'] if variables else ['settings']
    for name in names:
        path = os.path.join(DEFAULT_SETTINGS_DIR, name)
        with open(path) as f:
            exec(compile(f.read(), path, 'exec'), namespace)
