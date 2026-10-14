import fnmatch
import os
import tempfile
import tomllib
import unittest

import dnapy
from dnapy import enzyme, ladders

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPackageData(unittest.TestCase):
    def test_folders_exist(self):
        for folder in (dnapy.DATA_DIR, dnapy.ICONS_DIR, dnapy.DEFAULT_SETTINGS_DIR):
            self.assertTrue(os.path.isdir(folder), folder)

    def test_enzyme_data(self):
        self.assertTrue(os.path.isfile(enzyme.ENZYME_FILE))
        names = enzyme.commercial_enzyme_names()
        self.assertGreater(len(names), 100)
        self.assertIn('EcoRI', names)
        self.assertNotIn('', names)

    def test_every_data_file_is_included_when_the_package_is_built(self):
        """pyproject.toml lists the data files by pattern, a new kind of file has to be added there."""
        with open(os.path.join(REPO, 'pyproject.toml'), 'rb') as f:
            patterns = tomllib.load(f)['tool']['setuptools']['package-data']['dnapy']
        missing = []
        for folder in (dnapy.DATA_DIR, dnapy.ICONS_DIR, dnapy.DEFAULT_SETTINGS_DIR):
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if not os.path.isfile(path) or name.endswith('.py'):
                    continue
                relative = os.path.relpath(path, dnapy.ROOT_DIR).replace(os.sep, '/')
                if not any(fnmatch.fnmatch(relative, pattern) for pattern in patterns):
                    missing.append(relative)
        self.assertEqual(missing, [])


class TestLadders(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.user_file = os.path.join(folder.name, 'new_folder', 'dnaLadders.lst')

    def test_the_ladders_of_the_program(self):
        loaded = ladders.load(self.user_file)
        self.assertEqual(len(loaded), 3)
        name, *sizes = loaded[0]
        self.assertEqual(name, '1 kb DNA Ladder')
        self.assertEqual(sizes[:3], [500, 1000, 1500])  # sizes are numbers

    def test_added_ladders_are_saved_in_the_file_of_the_user(self):
        ladders.add(['my ladder', 100, 200, 400], self.user_file)  # the folder is made if needed
        loaded = ladders.load(self.user_file)
        self.assertEqual(len(loaded), 4)
        self.assertEqual(loaded[-1], ['my ladder', 100, 200, 400])

    def test_several_added_ladders(self):
        ladders.add(['one', 1, 2], self.user_file)
        ladders.add(['two', 3, 4], self.user_file)
        self.assertEqual(ladders.load(self.user_file)[-2:], [['one', 1, 2], ['two', 3, 4]])

    def test_the_ladder_file_of_the_program_is_not_changed(self):
        with open(ladders.BUNDLED_FILE) as f:
            before = f.read()
        ladders.add(['my ladder', 100, 200], self.user_file)
        with open(ladders.BUNDLED_FILE) as f:
            self.assertEqual(f.read(), before)

    def test_blank_lines_are_ignored(self):
        os.makedirs(os.path.dirname(self.user_file))
        with open(self.user_file, 'w') as f:
            f.write('\n\nmine,10,20\n\n')
        self.assertEqual(ladders.load(self.user_file)[-1], ['mine', 10, 20])
        self.assertEqual(len(ladders.load(self.user_file)), 4)


if __name__ == '__main__':
    unittest.main()
