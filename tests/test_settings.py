import os
import re
import tempfile
import unittest
from unittest import mock

from dnapy import settings
from dnapy.settings import SettingsError


class SettingsFileCase(unittest.TestCase):
    """Base class with a helper that writes a user settings file into a temporary folder."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        # never read the real ~/.dnapy/settings.toml or DNAPY_SETTINGS of the person running the tests
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(settings.ENVIRONMENT_VARIABLE, None)
        patcher = mock.patch.object(settings, 'USER_FILE', os.path.join(self.folder.name, 'no_such_file.toml'))
        patcher.start()
        self.addCleanup(patcher.stop)
        settings.reset()
        self.addCleanup(settings.reset)

    def write(self, text, name='user.toml'):
        path = os.path.join(self.folder.name, name)
        with open(path, 'w') as f:
            f.write(text)
        return path


class TestDefaults(SettingsFileCase):
    def test_default_values(self):
        s = settings.load()
        self.assertEqual(s.window_size, (1300, 650))
        self.assertEqual(s.default_directory, '')
        self.assertEqual(s.fallback_colour, 'grey')

    def test_colours(self):
        s = settings.load()
        self.assertEqual(sorted(s.colours), sorted(
            ['red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple', 'magenta', 'burgundy', 'grey']))
        self.assertEqual(s.colours['red'], {'color': 'red', 'fw': '#B01A1A', 'rv': '#CC3B3B'})
        for colour in s.colours.values():
            self.assertRegex(colour['fw'], r'^#[0-9a-fA-F]{6}$')
            self.assertRegex(colour['rv'], r'^#[0-9a-fA-F]{6}$')

    def test_feature_colours(self):
        s = settings.load()
        self.assertEqual(s.feature_colour('CDS')['color'], 'green')
        self.assertEqual(s.feature_colour('promoter')['color'], 'cyan')
        self.assertEqual(s.feature_colour('CDS')['fw'], '#159918')

    def test_feature_keys_that_are_not_python_names(self):
        s = settings.load()
        self.assertEqual(s.feature_colour('-35_signal')['color'], 'burgundy')
        self.assertEqual(s.feature_colour('-10_signal')['color'], 'burgundy')
        for key in ("5'UTR", "3'UTR", "5'clip", "3'clip", 'D-loop'):
            self.assertIn(key, s.feature_colours)
            self.assertEqual(s.feature_colour(key)['color'], 'grey', key)

    def test_unknown_feature_keys_use_the_fallback(self):
        s = settings.load()
        self.assertEqual(s.feature_colour('something_new')['color'], 'grey')
        self.assertEqual(s.feature_colour('files')['color'], 'grey')

    def test_the_colours_of_all_the_old_python_settings_were_kept(self):
        # the number of feature types that were assigned a color in the old Python settings file (src/defaults/settings)
        self.assertEqual(len(settings.load().feature_colours), 63)

    def test_icons_exist(self):
        s = settings.load()
        self.assertTrue(os.path.isfile(s.icon('new.png')))
        self.assertTrue(os.path.isfile(s.icon('icon.ico')))

    def test_start_directory_is_the_current_folder_when_not_set(self):
        self.assertEqual(settings.load().start_directory, os.getcwd())

    def test_get_loads_once(self):
        self.assertIs(settings.get(), settings.get())


class TestUserFile(SettingsFileCase):
    def test_user_values_replace_defaults(self):
        path = self.write('[window]\nsize = [800, 600]\n[files]\ndefault_directory = "C:/vectors"\n')
        s = settings.load(path)
        self.assertEqual(s.window_size, (800, 600))
        self.assertEqual(s.default_directory, 'C:/vectors')
        self.assertEqual(s.start_directory, 'C:/vectors')

    def test_everything_not_mentioned_keeps_its_default(self):
        s = settings.load(self.write('[window]\nsize = [800, 600]\n'))
        self.assertEqual(s.feature_colour('CDS')['color'], 'green')
        self.assertEqual(len(s.colours), 10)

    def test_change_the_colour_of_a_feature(self):
        s = settings.load(self.write('[features.colors]\nCDS = "blue"\n"-35_signal" = "red"\n'))
        self.assertEqual(s.feature_colour('CDS')['color'], 'blue')
        self.assertEqual(s.feature_colour('-35_signal')['color'], 'red')
        self.assertEqual(s.feature_colour('promoter')['color'], 'cyan')

    def test_add_a_colour_and_use_it(self):
        s = settings.load(self.write('[colors]\nteal = { fw = "#008080", rv = "#66b2b2" }\n'
                                     '[features.colors]\nrepeat_region = "teal"\n'))
        self.assertEqual(s.feature_colour('repeat_region'), {'color': 'teal', 'fw': '#008080', 'rv': '#66b2b2'})

    def test_environment_variable_names_the_file(self):
        os.environ[settings.ENVIRONMENT_VARIABLE] = self.write('[window]\nsize = [640, 480]\n')
        self.assertEqual(settings.load().window_size, (640, 480))

    def test_file_in_the_home_folder_is_used_when_it_exists(self):
        path = self.write('[window]\nsize = [700, 500]\n', name='home_settings.toml')
        with mock.patch.object(settings, 'USER_FILE', path):
            self.assertEqual(settings.load().window_size, (700, 500))

    def test_a_missing_default_user_file_is_ignored(self):
        self.assertEqual(settings.load().window_size, (1300, 650))

    def test_a_missing_file_that_was_asked_for_is_an_error(self):
        with self.assertRaisesRegex(SettingsError, 'does not exist'):
            settings.load(os.path.join(self.folder.name, 'missing.toml'))

    def test_the_defaults_are_not_changed_by_a_user_file(self):
        settings.load(self.write('[features.colors]\nCDS = "blue"\n'))
        self.assertEqual(settings.load().feature_colour('CDS')['color'], 'green')


class TestValidation(SettingsFileCase):
    def assert_rejected(self, text, message):
        with self.assertRaisesRegex(SettingsError, message):
            settings.load(self.write(text))

    def test_invalid_toml(self):
        self.assert_rejected('this is = = not toml', 'not valid TOML')

    def test_window_size(self):
        self.assert_rejected('[window]\nsize = [800]\n', 'window.size')
        self.assert_rejected('[window]\nsize = [800, -5]\n', 'window.size')
        self.assert_rejected('[window]\nsize = "big"\n', 'window.size')
        self.assert_rejected('[window]\nsize = [800.5, 600]\n', 'window.size')

    def test_default_directory_must_be_text(self):
        self.assert_rejected('[files]\ndefault_directory = 5\n', 'default_directory')

    def test_colour_values(self):
        self.assert_rejected('[colors]\nred = { fw = "red", rv = "#CC3B3B" }\n', r'colors\.red\.fw')
        self.assert_rejected('[colors]\nteal = { fw = "#008080" }\n', r'colors\.teal\.rv')
        self.assert_rejected('[colors]\nteal = "#008080"\n', r'colors\.teal')

    def test_changing_one_part_of_a_default_colour_keeps_the_other(self):
        s = settings.load(self.write('[colors]\nred = { fw = "#FF0000" }\n'))
        self.assertEqual(s.colours['red'], {'color': 'red', 'fw': '#FF0000', 'rv': '#CC3B3B'})

    def test_feature_colour_must_name_a_known_colour(self):
        self.assert_rejected('[features.colors]\nCDS = "chartreuse"\n', "unknown color 'chartreuse'")

    def test_fallback_colour_must_be_known(self):
        self.assert_rejected('[features]\nfallback_color = "chartreuse"\n', 'fallback_color')

    def test_missing_section_in_the_default_file(self):
        path = self.write('[window]\nsize = [800, 600]\n', name='defaults.toml')
        with self.assertRaisesRegex(SettingsError, r'\[files\]'):
            settings.load(default_file=path)


class TestDefaultFile(SettingsFileCase):
    def test_every_feature_colour_names_a_defined_colour(self):
        s = settings.load()
        self.assertTrue(set(s.feature_colours.values()) <= set(s.colours))

    def test_the_file_has_no_python_code_in_it(self):
        with open(settings.DEFAULT_FILE) as f:
            text = f.read()
        self.assertIsNone(re.search(r'^\s*(import|exec|eval)\b', text, re.M))


if __name__ == '__main__':
    unittest.main()
