"""
Settings of DNApy, read from TOML files.

The defaults are in dnapy/defaults/settings.toml. A user can change them by writing the entries to change into
their own file, either ~/.dnapy/settings.toml or the file named by the environment variable DNAPY_SETTINGS.
The entries of the user file replace the default ones, everything else keeps its default value.

Usage:
    from dnapy import settings
    settings.get().window_size
    settings.get().feature_colour('CDS')['fw']

The settings are plain data, no code from the files is executed, and the module does not need wxPython.
"""
import copy
import os
import re
import tomllib
from dataclasses import dataclass, field

from . import DEFAULT_SETTINGS_DIR, ICONS_DIR, USER_DIR

DEFAULT_FILE = os.path.join(DEFAULT_SETTINGS_DIR, 'settings.toml')
USER_FILE = os.path.join(USER_DIR, 'settings.toml')
ENVIRONMENT_VARIABLE = 'DNAPY_SETTINGS'

_HEX_COLOUR = re.compile(r'^#[0-9a-fA-F]{6}$')


class SettingsError(ValueError):
    """The settings are missing something or contain an invalid value."""


@dataclass(frozen=True)
class Settings:
    window_size: tuple
    default_directory: str
    colours: dict = field(repr=False)  # name -> {'color': name, 'fw': '#rrggbb', 'rv': '#rrggbb'}
    feature_colours: dict = field(repr=False)  # GenBank feature key -> colour name
    fallback_colour: str = 'grey'
    icon_dir: str = ICONS_DIR

    def feature_colour(self, feature_key):
        """Colour (a dict with 'color', 'fw' and 'rv') for a GenBank feature key such as 'CDS' or "-35_signal"."""
        return self.colours[self.feature_colours.get(feature_key, self.fallback_colour)]

    def icon(self, name):
        """Path of an icon file, for example icon('new.png')."""
        return os.path.join(self.icon_dir, name)

    @property
    def start_directory(self):
        """The folder where file dialogs start."""
        return self.default_directory or os.getcwd()


def _merge(base, extra):
    """Merge the nested dict `extra` into a copy of `base`. Values of `extra` win."""
    merged = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _read(path):
    try:
        with open(path, 'rb') as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as error:
        raise SettingsError('%s is not valid TOML: %s' % (path, error)) from error


def _section(data, name):
    section = data.get(name)
    if not isinstance(section, dict):
        raise SettingsError('The settings need a [%s] section.' % name)
    return section


def _build(data):
    """Check the merged settings and turn them into a Settings object."""
    window = _section(data, 'window')
    size = window.get('size')
    if not (isinstance(size, list) and len(size) == 2 and all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in size)):
        raise SettingsError('window.size must be two positive whole numbers (width and height), not %r.' % (size,))

    directory = _section(data, 'files').get('default_directory', '')
    if not isinstance(directory, str):
        raise SettingsError('files.default_directory must be text, not %r.' % (directory,))

    colours = {}
    for name, colour in _section(data, 'colors').items():
        if not isinstance(colour, dict):
            raise SettingsError('colors.%s must have the entries fw and rv.' % name)
        for part in ('fw', 'rv'):
            value = colour.get(part)
            if not (isinstance(value, str) and _HEX_COLOUR.match(value)):
                raise SettingsError('colors.%s.%s must be a color like "#1a2b3c", not %r.' % (name, part, value))
        colours[name] = {'color': name, 'fw': colour['fw'], 'rv': colour['rv']}

    features = _section(data, 'features')
    fallback = features.get('fallback_color')
    if fallback not in colours:
        raise SettingsError('features.fallback_color must be the name of a color, not %r.' % (fallback,))
    feature_colours = _section(features, 'colors')
    for key, name in feature_colours.items():
        if name not in colours:
            raise SettingsError('features.colors.%s uses the unknown color %r. The known colors are: %s.'
                                % (key, name, ', '.join(sorted(colours))))

    return Settings(window_size=tuple(size), default_directory=directory, colours=colours,
                    feature_colours=dict(feature_colours), fallback_colour=fallback)


def load(user_file=None, default_file=DEFAULT_FILE):
    """
    Read the default settings and apply the user's file on top of them.
    `user_file` is the path of that file; if it is not given, the file named by DNAPY_SETTINGS is used, or else
    ~/.dnapy/settings.toml. A user file that does not exist is ignored, unless it was asked for explicitly.
    """
    data = _read(default_file)
    explicit = user_file or os.environ.get(ENVIRONMENT_VARIABLE)
    path = explicit or USER_FILE
    if os.path.isfile(path):
        data = _merge(data, _read(path))
    elif explicit:
        raise SettingsError('The settings file %s does not exist.' % path)
    return _build(data)


_current = None


def get():
    """The settings of the running program, loaded on first use."""
    global _current
    if _current is None:
        _current = load()
    return _current


def reset():
    """Forget the loaded settings so that the next get() reads them again (used in tests)."""
    global _current
    _current = None
