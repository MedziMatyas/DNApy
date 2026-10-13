import contextlib
import io
import os
import unittest

from src import enzyme, genbank

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'test_plasmid.gb')


def load():
    with contextlib.redirect_stdout(io.StringIO()):
        return genbank.gbobject(DATA)


class TestRestrictionEnzymes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gb = load()
        cls.enzymes = cls.gb.restrictionEnzymes.enzymeObj

    def test_enzyme_list_is_loaded(self):
        self.assertGreater(len(self.enzymes), 500)
        for name in ('EcoRI', 'BamHI', 'KpnI', 'NheI'):
            self.assertIn(name, self.enzymes)

    def test_enzyme_properties(self):
        eco = self.enzymes['EcoRI']
        self.assertEqual(eco.pattern, 'GAATTC')
        self.assertEqual(eco.length, 6)
        self.assertEqual(eco.ncuts, 2)
        self.assertEqual(eco.c51, 1)

    def test_ambiguous_recognition_site_becomes_regex(self):
        # AccI recognises GTMKAC
        regex = self.enzymes['AccI'].regex
        for site in ('GTAGAC', 'GTCTAC', 'GTAGAC'.lower()):
            self.assertIsNotNone(regex.search(site))
        self.assertIsNone(regex.search('GTGGAC'))

    def test_sites_are_found_with_one_based_positions(self):
        site = self.enzymes['EcoRI'].restrictionSites[0]
        self.assertEqual(site[:3], ['EcoRI', 19, 24])
        self.assertEqual(site[5].upper(), 'GAATTC')

        site = self.enzymes['BamHI'].restrictionSites[0]
        self.assertEqual(site[:3], ['BamHI', 13, 18])

    def test_enzyme_without_site_has_no_sites(self):
        self.assertEqual(self.enzymes['EcoRV'].restrictionSites, [])

    @unittest.expectedFailure
    def test_each_site_is_reported_once(self):
        # known issue: sites in the first 100 bp are found again in the circular helper sequence
        self.assertEqual(len(self.enzymes['BamHI'].restrictionSites), 1)

    def test_enzymes_with_two_cuts_do_not_crash(self):
        # regression test: a typo left the second cut position unassigned
        two_cutters = [e for e in self.enzymes.values() if e.c52 != 0]
        self.assertTrue(two_cutters)
        initial = enzyme.initRestriction(self.gb)
        self.assertEqual(len(initial.enzymeObj), len(self.enzymes))


if __name__ == '__main__':
    unittest.main()
