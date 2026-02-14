import unittest
import json
from pathlib import Path
import sys

# Fix import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from il_validator import ILValidator, ILCanonicalizer

class TestILValidator(unittest.TestCase):
    def setUp(self):
        self.validator = ILValidator()
        self.examples_dir = ROOT / "docs/il/examples"

    def test_good_min(self):
        path = self.examples_dir / "good_min.json"
        data = json.loads(path.read_text())
        is_valid, errors = self.validator.validate(data)
        self.assertTrue(is_valid, f"Expected good_min.json to be valid, but got errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_bad_min(self):
        # bad_min.json is schema-invalid (e.g. missing fields)
        path = self.examples_dir / "bad_min.json"
        data = json.loads(path.read_text())
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid, "Expected bad_min.json to be invalid")
        self.assertGreater(len(errors), 0)
        # Check if errors are sorted (path ascending)
        paths = [e.get("path", "") for e in errors]
        self.assertEqual(paths, sorted(paths))

    def test_bad_forbidden_timestamp(self):
        path = self.examples_dir / "bad_forbidden_timestamp.json"
        data = json.loads(path.read_text())
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid, "Expected bad_forbidden_timestamp.json to be invalid")
        
        codes = [e["code"] for e in errors]
        self.assertIn("E_FORBIDDEN", codes)
        
        # Check specifically for the forbidden field
        forbidden_field_errors = [e for e in errors if e["code"] == "E_FORBIDDEN" and "created_at" in e["message"]]
        self.assertGreater(len(forbidden_field_errors), 0)

    def test_canonicalizer_determinism(self):
        data = {
            "b": 2,
            "a": 1,
            "c": {"y": 2, "x": 1},
            "d": [3, 1, 2]
        }
        bytes1 = ILCanonicalizer.canonicalize(data)
        bytes2 = ILCanonicalizer.canonicalize(data)
        self.assertEqual(bytes1, bytes2)
        
        # Check sorted keys and no spaces
        expected = b'{"a":1,"b":2,"c":{"x":1,"y":2},"d":[3,1,2]}'
        self.assertEqual(bytes1, expected)

    def test_illegal_floats(self):
        data = {
            "il": {"val": 1.5},
            "meta": {"version": "il_contract_v1"},
            "evidence": {}
        }
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertIn("E_TYPE", [e["code"] for e in errors])

    def test_null_forbidden(self):
        data = {
            "il": {"val": None},
            "meta": {"version": "il_contract_v1"},
            "evidence": {}
        }
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertIn("E_FORBIDDEN", [e["code"] for e in errors])

if __name__ == "__main__":
    unittest.main()
