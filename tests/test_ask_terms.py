import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TestAskTerms(unittest.TestCase):
    def test_extract_terms_japanese_topic(self):
        import ask
        terms = ask.extract_terms("ingest 儀式について教えてください。")
        self.assertIn("ingest", terms)
        self.assertIn("儀式", terms)

    def test_extract_terms_topic_only(self):
        import ask
        terms = ask.extract_terms("合格条件は何ですか？")
        self.assertIn("合格条件", terms)


if __name__ == "__main__":
    unittest.main()
