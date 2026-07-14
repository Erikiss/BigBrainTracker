import unittest

from tracker.names import fold, matches, name_tokens, title_key


class FoldTests(unittest.TestCase):
    def test_diacritics(self):
        self.assertEqual(fold("Łukasz"), "Lukasz")
        self.assertEqual(fold("Csaba Szepesvári"), "Csaba Szepesvari")
        self.assertEqual(fold("Sébastien Bubeck"), "Sebastien Bubeck")
        self.assertEqual(fold("Jürgen"), "Jurgen")


class TokenTests(unittest.TestCase):
    def test_comma_reversed_order(self):
        self.assertEqual(name_tokens("LeCun, Yann"), ["yann", "lecun"])

    def test_hyphen_and_period(self):
        self.assertEqual(name_tokens("Fei-Fei Li"), ["fei", "fei", "li"])
        self.assertEqual(name_tokens("Michael I. Jordan"), ["michael", "i", "jordan"])


class MatchTests(unittest.TestCase):
    def test_exact(self):
        self.assertTrue(matches("Yann LeCun", ["Yann LeCun"]))

    def test_middle_initial_ignored(self):
        self.assertTrue(matches("Quoc V. Le", ["Quoc Le"]))
        self.assertTrue(matches("Emmanuel J. Candes", ["Emmanuel Candès"]))
        self.assertTrue(matches("Michael Jordan", ["Michael I. Jordan"]))

    def test_diacritic_variants(self):
        self.assertTrue(matches("Lukasz Kaiser", ["Łukasz Kaiser"]))
        self.assertTrue(matches("Łukasz Kaiser", ["Lukasz Kaiser"]))

    def test_reversed_with_comma(self):
        self.assertTrue(matches("LeCun, Yann", ["Yann LeCun"]))

    def test_multi_part_surname(self):
        self.assertTrue(matches("Blaise Aguera y Arcas", ["Blaise Agüera y Arcas"]))
        self.assertTrue(matches("Blaise Agüera-Arcas", ["Blaise Agüera y Arcas"]))

    def test_abbreviated_first_name_rejected(self):
        self.assertFalse(matches("J. Wei", ["Jason Wei"]))
        self.assertFalse(matches("Y. LeCun", ["Yann LeCun"]))

    def test_different_person_rejected(self):
        self.assertFalse(matches("Jerry Wei", ["Jason Wei"]))
        self.assertFalse(matches("Karla Friston-Smith", ["Karl Friston"]))
        self.assertFalse(matches("", ["Jason Wei"]))


class TitleKeyTests(unittest.TestCase):
    def test_same_work_across_sources(self):
        self.assertEqual(
            title_key("FlashAttention-3: Fast and Exact Attention"),
            title_key("  FlashAttention 3:  fast and exact attention"),
        )

    def test_different_titles_differ(self):
        self.assertNotEqual(title_key("Paper A"), title_key("Paper B"))


if __name__ == "__main__":
    unittest.main()
