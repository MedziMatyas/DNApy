import unittest

from dnapy import dna
from dnapy.mixed_base_codons import AmbigousCodon


def encoded_amino_acids(triplet):
    """All amino acids encoded by an ambiguous triplet such as 'YTC'."""
    codons = dna.combine([dna.UnAmb(base) for base in triplet])
    return {dna.Translate(codon) for codon in codons}


class TestAmbiguousCodon(unittest.TestCase):
    def test_nnk_codes_for_all_20_amino_acids_and_a_stop(self):
        codon = AmbigousCodon('NNK', 1)
        self.assertEqual(sorted(codon.getTarget()), sorted('FLSYCWPHERIMTNKVADQG*'))
        self.assertEqual(codon.getOfftarget(), [])
        self.assertEqual(codon.getTriplet(), 'NNK')
        self.assertEqual(codon.getTable(), 1)

    def test_single_ambiguous_codon_evaluates_to_encoded_amino_acids(self):
        self.assertEqual(AmbigousCodon('GAR', 1).getTarget(), ['E'])

    def test_phe_leu_needs_no_off_target_amino_acids(self):
        codon = AmbigousCodon(['F', 'L'], 1)
        self.assertEqual(codon.getOfftarget(), [])
        # several triplets (e.g. YTC, TTK) are equally good, so check what it encodes
        self.assertEqual(encoded_amino_acids(codon.getTriplet()), {'F', 'L'})

    def test_asp_glu_needs_no_off_target_amino_acids(self):
        self.assertEqual(AmbigousCodon(['D', 'E'], 1).getOfftarget(), [])

    def test_designed_triplet_covers_every_requested_amino_acid(self):
        wanted = ['A', 'C', 'Y']
        codon = AmbigousCodon(wanted, 1)
        covered = encoded_amino_acids(codon.getTriplet())
        self.assertTrue(set(wanted) <= covered)
        self.assertEqual(sorted(covered - set(wanted)), sorted(codon.getOfftarget()))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            AmbigousCodon('AT', 1)


if __name__ == '__main__':
    unittest.main()
