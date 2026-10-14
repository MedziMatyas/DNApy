import contextlib
import io
import unittest

from dnapy import oligo_localizer, peptide_localizer
from dnapy.parsers import fasta


class TestOligoLocalizer(unittest.TestCase):
    def test_finds_all_occurrences_with_one_based_inclusive_positions(self):
        self.assertEqual(oligo_localizer.match_oligo('AAGGATCCTTGGATCC', 'GGATCC'),
                         [[3, 8], [11, 16]])

    def test_is_case_insensitive(self):
        self.assertEqual(oligo_localizer.match_oligo('aaggatcctt', 'GGATCC'), [[3, 8]])

    def test_ambiguous_oligo_matches_both_bases(self):
        self.assertEqual(oligo_localizer.match_oligo('AAGGATCCTT', 'GRATCC'), [[3, 8]])

    def test_overlapping_hits_are_found(self):
        self.assertEqual(len(oligo_localizer.match_oligo('AAAA', 'AA')), 3)

    def test_no_hit(self):
        self.assertEqual(oligo_localizer.match_oligo('AAAA', 'GG'), [])


class TestPeptideLocalizer(unittest.TestCase):
    def match(self, seq, peptide):
        # match_peptide prints debugging output, keep the test log clean
        with contextlib.redirect_stdout(io.StringIO()):
            return peptide_localizer.match_peptide(seq, peptide)

    def test_finds_all_occurrences(self):
        self.assertEqual(self.match('MASKGSEFGTGS', 'GS'), [[5, 6], [11, 12]])

    def test_no_hit(self):
        self.assertEqual(self.match('MASK', 'WW'), [])


class TestFasta(unittest.TestCase):
    def test_parse_string(self):
        records = list(fasta.parseString('>a\nATG\nCCC\n>b\nGGG\n'))
        self.assertEqual(records, [('a', 'ATGCCC'), ('b', 'GGG')])


if __name__ == '__main__':
    unittest.main()
