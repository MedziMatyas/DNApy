import os
import tempfile
import unittest

from dnapy import dna


class TestBasicDnaFunctions(unittest.TestCase):
    def test_clean_removes_non_dna_characters(self):
        self.assertEqual(dna.CleanDNA('AT GC12xN\n'), 'ATGC')

    def test_clean_keeps_ambiguous_codes_when_requested(self):
        self.assertEqual(dna.CleanDNA('ATGN', ambiguous=True), 'ATGN')

    def test_clean_requires_string(self):
        with self.assertRaises(AssertionError):
            dna.CleanDNA(123)

    def test_reverse(self):
        self.assertEqual(dna.R('AACG'), 'GCAA')

    def test_complement(self):
        self.assertEqual(dna.C('AACG'), 'TTGC')

    def test_reverse_complement(self):
        self.assertEqual(dna.RC('AACG'), 'CGTT')

    def test_reverse_complement_is_its_own_inverse(self):
        seq = 'ATGGCTAGCAAAGGATCC'
        self.assertEqual(dna.RC(dna.RC(seq)), seq)


class TestTranslation(unittest.TestCase):
    def test_translate(self):
        self.assertEqual(dna.Translate('ATGGCTAGCTAA'), 'MAS*')

    def test_translate_ignores_trailing_partial_codon(self):
        self.assertEqual(dna.Translate('ATGGC'), 'M')

    def test_translate_rc(self):
        self.assertEqual(dna.TranslateRC('TTAGCTAGCCAT'), 'MAS*')

    def test_get_codons(self):
        self.assertEqual(dna.GetCodons('M'), ['ATG'])
        self.assertEqual(sorted(dna.GetCodons('L')),
                         ['CTA', 'CTC', 'CTG', 'CTT', 'TTA', 'TTG'])

    def test_every_codon_translates_back_to_its_amino_acid(self):
        for aa in 'FLSYCWPHERIMTNKVADQG*':
            for codon in dna.GetCodons(aa):
                self.assertEqual(dna.Translate(codon), aa)

    def test_reverse_translate_lists_all_codons_per_residue(self):
        result = dna.ReverseTranslate('MA')
        self.assertEqual(result[0], ['ATG'])
        self.assertEqual(sorted(result[1]), ['GCA', 'GCC', 'GCG', 'GCT'])


class TestCounting(unittest.TestCase):
    def test_count_bases(self):
        counts = dna.count_bases('AACGTN')
        self.assertEqual((counts['A'], counts['C'], counts['G'], counts['T'], counts['N']),
                         (2, 1, 1, 1, 1))

    def test_count_codons(self):
        counts = dna.count_codons('ATGATGGCT')
        self.assertEqual(counts['AUG'], 2)
        self.assertEqual(counts['GCU'], 1)
        self.assertEqual(sum(counts.values()), 3)

    def test_make_codon_freq_table(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'cds.fasta')
            with open(path, 'w') as f:
                f.write('>one\nATGATGATGATG\n')
            table = dna.make_codon_freq_table(path)
        self.assertTrue(table['AUG'].startswith('1000.0(4)'))
        self.assertTrue(table['GCU'].startswith('0.0(0)'))


class TestAmbiguousCodes(unittest.TestCase):
    def test_amb_combines_bases_into_ambiguity_code(self):
        self.assertEqual(dna.Amb(['A', 'G']), 'R')

    def test_unamb_expands_ambiguity_code(self):
        self.assertEqual(sorted(dna.UnAmb('R')), ['A', 'G'])
        self.assertEqual(sorted(dna.UnAmb('N')), ['A', 'C', 'G', 'T'])

    def test_common_nucleotide(self):
        self.assertEqual(dna.commonNuc(['A', 'G']), ['R'])

    def test_combine_multiplies_out_lists(self):
        self.assertEqual(dna.combine([[1, 2], [3, 4]]), [4, 5, 5, 6])


class TestMisc(unittest.TestCase):
    def test_pair_identity(self):
        self.assertEqual(dna.PairIdent('AAAA', 'AATA'), 75.0)
        self.assertEqual(dna.PairIdent('AAAA', 'AAAA'), 100.0)

    def test_randomize_keeps_composition(self):
        seq = 'AACGTTTGCA'
        self.assertEqual(sorted(dna.randomizeSeq(seq)), sorted(seq))


if __name__ == '__main__':
    unittest.main()
