import contextlib
import io
import os
import tempfile
import unittest

from src import genbank

from . import wxapp

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'test_plasmid.gb')

# test_plasmid.gb (95 bp, circular):
#   1..33   CDS, MASKGSEFGT*            (NheI GCTAGC, BamHI GGATCC, EcoRI GAATTC, KpnI GGTACC inside)
#   40..55  promoter on the complement strand
SEQ = ('atggctagcaaaggatccgaattcggtacctaa'
       'gcgcgcatatgcgcgcatatgcgcgcttttaaaattttccccggggaaaattttccccgggg')


def load():
    # the parser and editor print progress messages, keep the test log clean
    with contextlib.redirect_stdout(io.StringIO()):
        return genbank.gbobject(DATA)


def quiet(func, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.gb = load()

    def test_locus(self):
        locus = self.gb.gbfile['locus']
        self.assertEqual(locus['name'], 'TestPlasmid')
        self.assertEqual(locus['length'], '95')
        self.assertEqual(locus['type'], 'DNA')
        self.assertEqual(locus['topology'], 'circular')
        self.assertEqual(locus['division'], 'SYN')
        self.assertEqual(locus['date'], '01-JAN-2015')

    def test_header_fields(self):
        self.assertEqual(self.gb.gbfile['definition'],
                         'Small synthetic plasmid used for the DNApy unit tests.')
        self.assertEqual(self.gb.gbfile['source'], 'synthetic construct')

    def test_dna(self):
        self.assertEqual(self.gb.GetDNA(), SEQ)
        self.assertEqual(len(self.gb.GetDNA()), 95)

    def test_get_dna_range_is_one_based_and_inclusive(self):
        self.assertEqual(self.gb.GetDNA(1, 3), 'atg')
        self.assertEqual(self.gb.GetDNA(4, 6), 'gct')

    def test_features(self):
        features = self.gb.get_all_features()
        self.assertEqual([f['key'] for f in features], ['CDS', 'promoter'])
        self.assertEqual(features[0]['location'], ['1..33'])
        self.assertFalse(features[0]['complement'])
        self.assertEqual(features[1]['location'], ['40..55'])
        self.assertTrue(features[1]['complement'])

    def test_qualifiers(self):
        self.assertEqual(self.gb.get_qualifiers(0),
                         ['/label="test_cds"', '/translation="MASKGSEFGT"'])
        self.assertEqual(self.gb.get_feature_label(1), '"test_promoter"')

    def test_feature_positions(self):
        positions = self.gb.get_all_feature_positions()
        self.assertEqual(positions[0][:4], ['CDS', False, 1, 33])
        self.assertEqual(positions[1][:4], ['promoter', True, 40, 55])

    def test_feature_dna(self):
        self.assertEqual(self.gb.GetFeatureDNA(0), SEQ[:33])

    def test_features_at_position(self):
        self.assertEqual([f['key'] for f in self.gb.get_features_for_pos(5)], ['CDS'])
        self.assertEqual(self.gb.get_features_for_pos(36), [])

    def test_parse_location_variants(self):
        self.assertEqual(self.gb.parse_location('1..5'), (['1..5'], False, False, False))
        self.assertEqual(self.gb.parse_location('complement(1..5)'), (['1..5'], True, False, False))
        self.assertEqual(self.gb.parse_location('join(1..5,10..12)'),
                         (['1..5', '10..12'], False, True, False))
        self.assertEqual(self.gb.parse_location('order(1..5,10..12)'),
                         (['1..5', '10..12'], False, False, True))

    def test_new_empty_object(self):
        gb = genbank.gbobject()
        self.assertIsNone(gb.gbfile['dna'])
        self.assertEqual(gb.fileName, 'New DNA')

    def test_taxonomy_keeps_its_spaces(self):
        self.assertEqual(self.gb.gbfile['organism'][1:],
                         ['other sequences', 'artificial sequences'])

    def test_taxonomy_that_wraps_over_several_lines(self):
        with open(DATA) as f:
            text = f.read().replace(
                '            other sequences; artificial sequences.\n',
                '            Eukaryota; Metazoa; Chordata; Craniata; Vertebrata; Euteleostomi;\n'
                '            Mammalia; Eutheria; Euarchontoglires; Primates; Haplorrhini;\n'
                '            Catarrhini; Hominidae; Homo.\n')
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'wrapped.gb')
            with open(path, 'w') as f:
                f.write(text)
            gb = quiet(genbank.gbobject, path)
        self.assertEqual(gb.gbfile['organism'][1:4], ['Eukaryota', 'Metazoa', 'Chordata'])
        self.assertEqual(gb.gbfile['organism'][-3:], ['Catarrhini', 'Hominidae', 'Homo'])
        self.assertEqual(len(gb.gbfile['organism']), 15)

    def test_taxonomy_is_written_with_its_spaces(self):
        text = self.gb.make_gbstring()
        self.assertIn('other sequences; artificial sequences.', text)


class TestSaving(unittest.TestCase):
    def test_save_and_reload_round_trip(self):
        gb = load()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'copy.gb')
            self.assertTrue(quiet(gb.Save, path))
            copy = quiet(genbank.gbobject, path)
        self.assertEqual(copy.GetDNA(), gb.GetDNA())
        self.assertEqual(copy.get_all_features(), gb.get_all_features())
        self.assertEqual(copy.gbfile['locus'], gb.gbfile['locus'])
        self.assertEqual(copy.gbfile['definition'], gb.gbfile['definition'])

    def test_gbstring_has_standard_sections(self):
        text = load().make_gbstring()
        for keyword in ('LOCUS', 'DEFINITION', 'FEATURES', 'ORIGIN', '//'):
            self.assertIn(keyword, text)
        self.assertIn('complement(40..55)', text)


class TestSequenceEditing(unittest.TestCase):
    def setUp(self):
        self.gb = load()

    def test_upper_and_lower(self):
        quiet(self.gb.Upper, 1, 3)
        self.assertEqual(self.gb.GetDNA(1, 6), 'ATGgct')
        quiet(self.gb.Lower, 1, 3)
        self.assertEqual(self.gb.GetDNA(1, 6), 'atggct')

    def test_delete_removes_dna_and_shifts_features(self):
        quiet(self.gb.Delete, 1, 3)
        self.assertEqual(len(self.gb.GetDNA()), 92)
        self.assertEqual(self.gb.GetDNA(1, 3), 'gct')
        positions = self.gb.get_all_feature_positions()
        self.assertEqual(positions[0][2:4], [1, 30])
        self.assertEqual(positions[1][2:4], [37, 52])

    def test_paste_inserts_dna_and_shifts_features(self):
        # the insertion point is the 1-based position of the base the new DNA is placed in front of
        quiet(self.gb.Paste, 1, 'GGG')
        self.assertEqual(len(self.gb.GetDNA()), 98)
        self.assertEqual(self.gb.GetDNA(1, 3), 'GGG')
        positions = self.gb.get_all_feature_positions()
        self.assertEqual(positions[0][2:4], [4, 36])
        self.assertEqual(positions[1][2:4], [43, 58])

    def test_paste_at_the_end(self):
        quiet(self.gb.Paste, 96, 'GGG')
        self.assertEqual(self.gb.GetDNA()[-6:], 'gggGGG')
        positions = self.gb.get_all_feature_positions()
        self.assertEqual(positions[0][2:4], [1, 33])

    def test_paste_requires_integer_position(self):
        with self.assertRaises(AssertionError):
            self.gb.Paste('1', 'GGG')


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.gb = load()

    def test_find_nucleotide(self):
        self.assertEqual(self.gb.FindNucleotide('GGATCC'), [(13, 18)])

    def test_find_nucleotide_with_ambiguity_code(self):
        self.assertEqual(self.gb.FindNucleotide('GGWTCC'), [(13, 18)])

    def test_find_nucleotide_reverse_complement(self):
        # GGTACC is a palindrome, so it is found on the reverse strand at the same place
        self.assertEqual(self.gb.FindNucleotide('GGTACC', -1, True), [(25, 30)])

    def test_find_nucleotide_within_feature(self):
        self.assertEqual(self.gb.FindNucleotide('ATG', 0), [(1, 3)])

    def test_find_amino_acid_sequence_in_feature(self):
        # the two residues Gly-Ser are residues 5-6 of the CDS, i.e. nucleotides 13-18
        self.assertEqual(quiet(self.gb.FindAminoAcid, 'GS', 0)[0], (13, 18))

    def test_find_amino_acid_by_position(self):
        self.assertEqual(quiet(self.gb.FindAminoAcid, 2, 0), [(4, 6)])

    def test_find_feature_by_label(self):
        self.assertEqual(self.gb.FindFeature('test_cds'), [(0, 33)])


class TestMutation(unittest.TestCase):
    def setUp(self):
        self.gb = load()

    def test_dna_mutation(self):
        quiet(self.gb.mutate, 'D', -1, 'A1C')
        self.assertEqual(self.gb.GetDNA(1, 3).lower(), 'ctg')

    def test_amino_acid_mutation_with_explicit_codon(self):
        quiet(self.gb.mutate, 'A', 0, 'A2G(GGA)')
        self.assertEqual(self.gb.GetDNA(4, 6).lower(), 'gga')

    def test_amino_acid_mutation_adds_marker_feature_unless_silent(self):
        quiet(self.gb.mutate, 'A', 0, 'A2G(GGA)')
        self.assertEqual(len(self.gb.get_all_features()), 3)
        self.assertEqual(self.gb.get_all_features()[2]['key'], 'modified_base')

        other = load()
        quiet(other.mutate, 'A', 0, 'A2G(GGA)', silent=True)
        self.assertEqual(len(other.get_all_features()), 2)

    def test_amino_acid_mutation_checks_the_existing_residue(self):
        with self.assertRaises(AssertionError):
            quiet(self.gb.mutate, 'A', 0, 'K2G(GGA)')  # residue 2 is Ala, not Lys

    def test_codon_must_encode_the_requested_amino_acid(self):
        with self.assertRaises(AssertionError):
            quiet(self.gb.mutate, 'A', 0, 'A2G(AAA)')


class TestFeatureEditing(unittest.TestCase):
    def setUp(self):
        self.gb = load()

    def test_add_feature(self):
        quiet(self.gb.add_feature, 'misc_feature', ['/label="x"'], ['60..70'], False, False, False)
        self.assertEqual(len(self.gb.get_all_features()), 3)

    def test_remove_feature(self):
        feature = self.gb.get_feature(1)
        quiet(self.gb.remove_feature, feature)
        self.assertEqual([f['key'] for f in self.gb.get_all_features()], ['CDS'])

    def test_add_and_remove_qualifier(self):
        feature = self.gb.get_feature(0)
        quiet(self.gb.add_qualifier, feature, '/note="n"')
        self.assertIn('/note="n"', self.gb.get_qualifiers(0))
        quiet(self.gb.remove_qualifier, feature, len(self.gb.get_qualifiers(0)) - 1)
        self.assertNotIn('/note="n"', self.gb.get_qualifiers(0))


class TestUndoRedo(unittest.TestCase):
    def test_undo_restores_the_state_before_the_first_edit(self):
        gb = load()
        quiet(gb.Upper, 1, 3)
        self.assertTrue(gb.Undo())
        self.assertEqual(gb.GetDNA(1, 3), 'atg')

    def test_nothing_to_undo_in_a_freshly_loaded_file(self):
        gb = load()
        self.assertFalse(gb.Undo())
        self.assertEqual(gb.GetDNA(), SEQ)

    def test_nothing_to_redo_after_the_last_edit(self):
        gb = load()
        quiet(gb.Upper, 1, 3)
        self.assertFalse(gb.Redo())

    def test_undo_all_the_way_back_and_redo_all_the_way_forward(self):
        gb = load()
        quiet(gb.Upper, 1, 3)
        quiet(gb.Delete, 1, 3)
        quiet(gb.Paste, 1, 'GGG')
        states = [SEQ, 'ATG' + SEQ[3:], SEQ[3:], 'GGG' + SEQ[3:]]
        self.assertEqual(gb.GetDNA(), states[3])
        for expected in reversed(states[:3]):
            self.assertTrue(gb.Undo())
            self.assertEqual(gb.GetDNA(), expected)
        self.assertFalse(gb.Undo())
        for expected in states[1:]:
            self.assertTrue(gb.Redo())
            self.assertEqual(gb.GetDNA(), expected)
        self.assertFalse(gb.Redo())

    def test_undo_restores_the_features_too(self):
        gb = load()
        before = gb.get_all_feature_positions()
        quiet(gb.Delete, 1, 3)
        self.assertNotEqual(gb.get_all_feature_positions(), before)
        gb.Undo()
        self.assertEqual(gb.get_all_feature_positions(), before)

    def test_a_new_edit_after_undo_removes_what_could_have_been_redone(self):
        gb = load()
        quiet(gb.Upper, 1, 3)
        quiet(gb.Upper, 4, 6)
        gb.Undo()
        quiet(gb.Upper, 7, 9)
        self.assertFalse(gb.Redo())
        self.assertEqual(gb.GetDNA(1, 9), 'ATGgctAGC')
        gb.Undo()
        self.assertEqual(gb.GetDNA(1, 9), 'ATGgctagc')

    def test_editing_after_undo_does_not_change_the_stored_versions(self):
        gb = load()
        quiet(gb.Upper, 1, 3)
        gb.Undo()
        quiet(gb.Delete, 1, 3)  # an edit on the restored state
        gb.Undo()
        self.assertEqual(gb.GetDNA(), SEQ)
        gb.Redo()
        self.assertEqual(gb.GetDNA(), SEQ[3:])

    def test_undo_updates_the_restriction_sites(self):
        gb = load()

        def sites():
            return gb.restrictionEnzymes.enzymeObj['BamHI'].restrictionSites
        self.assertEqual(len(sites()), 1)
        quiet(gb.Delete, 13, 18)  # removes GGATCC
        self.assertEqual(len(sites()), 0)
        gb.Undo()
        self.assertEqual(len(sites()), 1)

    def test_undo_keeps_the_file_path(self):
        gb = load()
        quiet(gb.Upper, 1, 3)
        gb.SetFilepath('C:/somewhere/new.gb')
        quiet(gb.Upper, 4, 6)
        gb.Undo()
        gb.Undo()
        self.assertEqual(gb.GetFilepath(), 'C:/somewhere/new.gb')

    def test_a_new_empty_file_can_be_undone_back_to_empty(self):
        gb = genbank.gbobject()
        quiet(gb.Paste, 1, 'ATGC')
        self.assertEqual(gb.GetDNA(), 'ATGC')
        gb.Undo()
        self.assertIsNone(gb.GetDNA())

    def test_undo_and_redo_of_a_later_edit(self):
        gb = load()
        quiet(gb.Upper, 1, 3)
        quiet(gb.Upper, 4, 6)
        self.assertEqual(gb.GetDNA(1, 6), 'ATGGCT')
        quiet(gb.Undo)
        self.assertEqual(gb.GetDNA(1, 6), 'ATGgct')
        quiet(gb.Redo)
        self.assertEqual(gb.GetDNA(1, 6), 'ATGGCT')


class TestRealWorldFiles(unittest.TestCase):
    """Files written by other programs differ from the minimal test file."""

    def load_text(self, text):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'other.gb')
            with open(path, 'w', newline='') as f:
                f.write(text)
            return quiet(genbank.gbobject, path)

    def fixture_text(self):
        with open(DATA) as f:
            return f.read()

    def test_empty_accession_and_version_lines(self):
        # e.g. the NEB pUC19 file has "ACCESSION" and "VERSION" without any value
        text = self.fixture_text().replace('ACCESSION   .', 'ACCESSION').replace('VERSION     .', 'VERSION')
        gb = self.load_text(text)
        self.assertEqual(gb.GetDNA(), SEQ)
        self.assertIsNone(gb.gbfile['version'])

    def test_windows_line_endings(self):
        gb = self.load_text(self.fixture_text().replace('\n', '\r\n'))
        self.assertEqual(gb.GetDNA(), SEQ)
        self.assertEqual(len(gb.get_all_features()), 2)

    def test_feature_keys_that_start_with_a_dash_or_digit(self):
        extra = ("     -35_signal      10..15\n"
                 "                     /note=\"a promoter element\"\n"
                 "     5'UTR           20..25\n")
        gb = self.load_text(self.fixture_text().replace('ORIGIN', extra + 'ORIGIN'))
        self.assertEqual([f['key'] for f in gb.get_all_features()], ['CDS', 'promoter', '-35_signal', "5'UTR"])
        self.assertEqual(gb.get_all_features()[2]['location'], ['10..15'])


@unittest.skipIf(genbank.wx is None, 'wxPython is not installed')
class TestRichClipboard(unittest.TestCase):
    """RichCopy/RichPaste go through the wx clipboard, so they need a wx.App."""

    @classmethod
    def setUpClass(cls):
        cls.app = wxapp.get_app()

    def test_copy_and_paste_carries_features(self):
        gb = load()
        if not genbank.wx.TheClipboard.Open():
            self.skipTest('system clipboard is not available')
        genbank.wx.TheClipboard.Close()
        quiet(gb.RichCopy, 1, 33)
        quiet(gb.RichPaste, 96)  # 96 = in front of the (non-existent) base after the last one, i.e. append
        self.assertEqual(len(gb.GetDNA()), 95 + 33)
        self.assertEqual(gb.GetDNA(96, 128), SEQ[:33])
        pasted = [p for p in gb.get_all_feature_positions() if p[0] == 'CDS']
        self.assertEqual([p[2:4] for p in pasted], [[1, 33], [96, 128]])


if __name__ == '__main__':
    unittest.main()
