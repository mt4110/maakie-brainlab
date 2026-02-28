import importlib.util
import unittest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "ops" / "s32_handoff_pack.py"
    spec = importlib.util.spec_from_file_location("s32_handoff_pack", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestS32S33BacklogSeedPack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_module()

    def test_generate_backlog_seed_is_ranked_and_deterministic(self):
        closeout = {"unresolved_risks": ["missing_input:latency", "warn_input:trend"]}
        trend = {"rows": [{"phase": "s32-16", "status": "WARN", "path": "docs/evidence/s32-16/x.json"}]}
        pending = ["S32-30 pending handoff finalize"]
        first = self.m.generate_backlog_seed(closeout, trend, pending)
        second = self.m.generate_backlog_seed(closeout, trend, pending)
        self.assertEqual(first, second)
        self.assertGreater(len(first), 0)
        self.assertIn("id", first[0])
        self.assertIn("priority", first[0])


if __name__ == "__main__":
    unittest.main()
