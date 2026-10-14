import unittest

from recommendations import build_recommendation


class RecommendationTests(unittest.TestCase):
    def test_career_suggestion_is_explainable_and_repeatable(self):
        answers = {
            "education": "Curso de Python e informática",
            "superpower": "Organização e lógica",
            "hobby": "Programar e aprender tecnologia",
            "work_style": "hybrid",
            "decision_style": "analytical",
        }
        first = build_recommendation("profession", answers)
        second = build_recommendation("profession", answers)
        self.assertEqual(first, second)
        self.assertEqual(first["kind"], "profession")
        self.assertTrue(first["roles"])
        self.assertTrue(first["basis"])
        self.assertIn("não usa ia generativa", first["notice"].casefold())

    def test_team_result_is_explicitly_recreational(self):
        result = build_recommendation("team", {"work_style": "onsite"})
        self.assertEqual(result["kind"], "team")
        self.assertIn("recreativa", result["summary"])
        self.assertIn("tempo real", result["notice"])
        self.assertTrue(result["squad"])

    def test_empty_career_answers_use_a_stable_default(self):
        result = build_recommendation("profession", {"work_style": "hybrid", "decision_style": "analytical"})
        self.assertEqual(result["kind"], "profession")
        self.assertTrue(result["title"].startswith("Afinidade inicial:"))
        self.assertTrue(result["roles"])


if __name__ == "__main__":
    unittest.main()
