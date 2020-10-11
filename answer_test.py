import unittest

from question import Question

class TestStringMethods(unittest.TestCase):

    def test_single_character(self):
        q = Question("", "8")
        self.assertFalse(q.is_answer_correct("2"))
        self.assertTrue(q.is_answer_correct("8"))

    def test_remove_stop_words(self):
        q = Question("", "California and Hawaii")
        self.assertTrue(q.is_answer_correct("California Hawaii"))
        self.assertTrue(q.is_answer_correct("Hawaii California"))
        self.assertFalse(q.is_answer_correct("Hawaii and"))

    def test_removal_of_punctuation(self):
        q = Question("", "\n!%#answer{}()")
        self.assertTrue(q.is_answer_correct("answer"))

    def test_tokenization_requires_enough(self):
        q = Question("", "Baking soda")
        self.assertFalse(q.is_answer_correct("Baking"))
        self.assertFalse(q.is_answer_correct("soda"))

    def test_tokenization_works(self):
        q = Question("", "The Emerald City")
        self.assertTrue(q.is_answer_correct("Emeralz City"))

    def test_removal_of_stop_words(self):
        q = Question("", "The I we ours you they chicken was doing a the and")
        self.assertTrue(q.is_answer_correct("chicken"))

    def test_numeric_answer(self):
        q = Question("", "321")
        self.assertTrue(q.is_answer_correct("321"))
        self.assertFalse(q.is_answer_correct("322"))
        self.assertFalse(q.is_answer_correct("421"))
        self.assertFalse(q.is_answer_correct("32"))

    def test_numeric_answer_spelled_out(self):
        q = Question("", "Twenty-Seven")
        self.assertTrue(q.is_answer_correct("27"))

    def test_long_keyword_matches(self):
        q = Question("", "Yellowstone National Park")
        self.assertTrue(q.is_answer_correct("yellowstone"))

    def test_words_in_question_ignored(self):
        q = Question("Who is the only US president to serve more than two terms?", "President Franklin Delano Roosevelt")
        self.assertTrue(q.is_answer_correct("Franklin Roosevelt"))
        self.assertTrue(q.is_answer_correct("Roosevelt"))

    def test_short_answer_must_be_exact(self):
        q = Question("", "tin")
        self.assertTrue(q.is_answer_correct("tin"))
        self.assertFalse(q.is_answer_correct("bin"))

    def test_acronym(self):
        q = Question("", "The I.D.P.D")
        self.assertTrue(q.is_answer_correct("idpd"))
        self.assertFalse(q.is_answer_correct("idps"))

    def test_accents_dont_matter(self):
        q = Question("", "Adiós")
        self.assertTrue(q.is_answer_correct("adios"))
        self.assertTrue(q.is_answer_correct("adiós"))

    def test_bad_answer(self):
        q = Question("", "Marine One")
        self.assertFalse(q.is_answer_correct("Airforce One"))

    def test_can_spell_numbers(self):
        q = Question("", "20")
        self.assertTrue(q.is_answer_correct("twenty"))

    def test_number_answer(self):
        q = Question("", "One, earth")
        self.assertTrue(q.is_answer_correct("1 earth"))

if __name__ == '__main__':
    unittest.main()



