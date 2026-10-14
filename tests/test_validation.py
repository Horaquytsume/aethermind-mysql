import unittest

from app import _validate_answers


class AnswerValidationTests(unittest.TestCase):
    def setUp(self):
        self.answers = {
            "name": "Alex Silva",
            "age": 25,
            "city": "São Paulo - SP",
            "education": "Mecatrônica Industrial",
            "superpower": "Organização",
            "hobby": "Jogos",
            "animal": "Gato",
            "color": "Azul",
            "work_style": "hybrid",
            "decision_style": "analytical",
        }

    def test_valid_answers_are_normalized(self):
        result = _validate_answers(self.answers, "profession")
        self.assertEqual(result["age"], 25)
        self.assertEqual(result["target"], "profession")

    def test_fractional_age_is_rejected(self):
        self.answers["age"] = 25.5
        with self.assertRaisesRegex(ValueError, "inteiro"):
            _validate_answers(self.answers, "profession")

    def test_boolean_age_is_rejected(self):
        self.answers["age"] = True
        with self.assertRaises(ValueError):
            _validate_answers(self.answers, "profession")

    def test_unrecognized_work_style_is_rejected(self):
        self.answers["work_style"] = "anything"
        with self.assertRaisesRegex(ValueError, "preferência"):
            _validate_answers(self.answers, "profession")


if __name__ == "__main__":
    unittest.main()
