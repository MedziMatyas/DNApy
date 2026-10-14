import unittest

from dnapy import dna, protein


class TestProtein(unittest.TestCase):
    def test_one_to_three_and_back(self):
        self.assertEqual(protein.one_to_three('A'), 'Ala')
        self.assertEqual(protein.three_to_one('Ala'), 'A')

    def test_all_amino_acids_round_trip(self):
        for aa in 'FLSYCWPHERIMTNKVADQG':
            self.assertEqual(protein.three_to_one(protein.one_to_three(aa)), aa)

    def test_one_to_full_name(self):
        self.assertEqual(protein.one_to_full('A'), 'Alanine')

    def test_full_name_round_trip(self):
        self.assertEqual(protein.full_to_one('Alanine'), 'A')

    def test_count_aa(self):
        counts = protein.count_aa('AAG')
        self.assertEqual((counts['A'], counts['G'], counts['M']), (2, 1, 0))

    def test_reverse_translate_gives_a_dna_that_translates_back(self):
        self.assertEqual(dna.Translate(protein.reverse_translate('MASKGSEFGT')),
                         'MASKGSEFGT')


if __name__ == '__main__':
    unittest.main()
