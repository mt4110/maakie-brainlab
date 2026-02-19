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

    def test_forbidden_floats(self):
        # 1.0 is forbidden [HARDCORE]
        data = {
            "il": {"val": 1.0},
            "meta": {"version": "il_contract_v1"},
            "evidence": {}
        }
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertEqual(errors[0]["code"], "E_SCHEMA")
        
        # 1.5 is forbidden
        data["il"]["val"] = 1.5
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertEqual(errors[0]["code"], "E_SCHEMA")

    def test_forbidden_bool(self):
        # True/False are forbidden for int fields [HARDCORE]
        data = {
            "il": {"val": True},
            "meta": {"version": "il_contract_v1"},
            "evidence": {}
        }
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertEqual(errors[0]["code"], "E_SCHEMA")

    def test_int_53bit_range(self):
        data = {
            "il": {"val": 2**53 - 1},
            "meta": {"version": "il_contract_v1"},
            "evidence": {}
        }
        is_valid, errors = self.validator.validate(data)
        self.assertTrue(is_valid)
        
        data["il"]["val"] = 2**53
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertEqual(errors[0]["code"], "E_SCHEMA")

    def test_il_must_be_object(self):
        data = {
            "il": [1, 2, 3],
            "meta": {"version": "il_contract_v1"},
            "evidence": {}
        }
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertEqual(errors[0]["code"], "E_SCHEMA")
        self.assertEqual(errors[0]["path"], "/il")

    def test_null_forbidden(self):
        data = {
            "il": {"val": None},
            "meta": {"version": "il_contract_v1"},
            "evidence": {}
        }
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertIn("E_FORBIDDEN", [e["code"] for e in errors])

    def test_canonicalize_rejects_nan(self):
        with self.assertRaises(ValueError):
            ILCanonicalizer.canonicalize({"a": float('nan')})

    def test_reserved_errors_key(self):
        # top-level errors is forbidden
        data = {
            "il": {"val": 1},
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
            "errors": []
        }
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertEqual(errors[0]["code"], "E_SCHEMA")
        self.assertEqual(errors[0]["path"], "/errors")

        # nested errors is forbidden
        data = {
            "il": {"val": 1, "errors": "oops"},
            "meta": {"version": "il_contract_v1"},
            "evidence": {}
        }
        is_valid, errors = self.validator.validate(data)
        self.assertFalse(is_valid)
        self.assertEqual(errors[0]["code"], "E_SCHEMA")
        self.assertEqual(errors[0]["path"], "/il/errors")

    def test_unexpected_top_level_key(self):
        data = {
            "il": {"uid": "u1", "title": "t"},
            "meta": {"version": "il_contract_v1"},
            "evidence": {},
            "extra": 1,
        }
        ok, errors = self.validator.validate(data)
        self.assertFalse(ok)
        self.assertTrue(any(e.get("code") == "E_SCHEMA" and e.get("path") == "/extra" for e in errors))

    def test_canonicalizer_rejects_inf(self):
        with self.assertRaises(ValueError):
            ILCanonicalizer.canonicalize({"a": float('inf')})
        with self.assertRaises(ValueError):
            ILCanonicalizer.canonicalize({"a": float('-inf')})

    def test_canonicalizer_normalize_zero(self):
        data = {"a": -0.0, "b": 0.0, "c": [-0.0]}
        canonical = ILCanonicalizer.canonicalize(data)
        # Expected: {"a":0.0,"b":0.0,"c":[0.0]}
        self.assertEqual(canonical, b'{"a":0.0,"b":0.0,"c":[0.0]}')

    def test_canonicalizer_rejects_inf(self):
        with self.assertRaises(ValueError):
            ILCanonicalizer.canonicalize({"a": float('inf')})
        with self.assertRaises(ValueError):
            ILCanonicalizer.canonicalize({"a": float('-inf')})

    def test_canonicalizer_normalize_zero(self):
        data = {"a": -0.0, "b": 0.0, "c": [-0.0]}
        canonical = ILCanonicalizer.canonicalize(data)
        # Expected: {"a":0.0,"b":0.0,"c":[0.0]}
        self.assertEqual(canonical, b'{"a":0.0,"b":0.0,"c":[0.0]}')

if __name__ == "__main__":
    unittest.main()
