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

    def test_each_site_is_reported_once(self):
        # sites in the first 100 bp used to be found again in the copy of the start that is added for circular dna
        self.assertEqual(len(self.enzymes['BamHI'].restrictionSites), 1)
        self.assertEqual(len(self.enzymes['EcoRI'].restrictionSites), 1)

    def sites_in(self, sequence, topology, name):
        gb = genbank.gbobject()
        gb.gbfile['locus']['topology'] = topology
        gb.gbfile['dna'] = sequence
        return [site[:3] for site in enzyme.initRestriction(gb).enzymeObj[name].restrictionSites]

    def test_site_at_the_very_end_of_the_sequence(self):
        sequence = 'A' * 20 + 'GGATCC'
        self.assertEqual(self.sites_in(sequence, 'linear', 'BamHI'), [['BamHI', 21, 26]])
        self.assertEqual(self.sites_in(sequence, 'circular', 'BamHI'), [['BamHI', 21, 26]])

    def test_site_at_the_very_start_of_the_sequence(self):
        sequence = 'GGATCC' + 'A' * 20
        self.assertEqual(self.sites_in(sequence, 'linear', 'BamHI'), [['BamHI', 1, 6]])
        self.assertEqual(self.sites_in(sequence, 'circular', 'BamHI'), [['BamHI', 1, 6]])

    def test_site_that_goes_over_the_origin_of_a_circular_sequence(self):
        sequence = 'ATCC' + 'A' * 20 + 'GG'  # GGATCC when the end is joined to the start
        self.assertEqual(self.sites_in(sequence, 'circular', 'BamHI'), [['BamHI', 25, 4]])
        self.assertEqual(self.sites_in(sequence, 'linear', 'BamHI'), [])

    def test_site_beyond_the_first_100_bp_is_reported_once(self):
        sequence = 'A' * 150 + 'GGATCC' + 'A' * 150
        self.assertEqual(self.sites_in(sequence, 'circular', 'BamHI'), [['BamHI', 151, 156]])

    def test_several_sites_are_each_reported_once(self):
        sequence = 'GGATCC' + 'A' * 30 + 'GGATCC' + 'A' * 30
        self.assertEqual(self.sites_in(sequence, 'circular', 'BamHI'),
                         [['BamHI', 1, 6], ['BamHI', 37, 42]])

    def test_enzymes_with_two_cuts_do_not_crash(self):
        # regression test: a typo left the second cut position unassigned
        two_cutters = [e for e in self.enzymes.values() if e.c52 != 0]
        self.assertTrue(two_cutters)
        initial = enzyme.initRestriction(self.gb)
        self.assertEqual(len(initial.enzymeObj), len(self.enzymes))


if __name__ == '__main__':
    unittest.main()
