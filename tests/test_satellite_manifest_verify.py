import json
import tempfile
import unittest
from pathlib import Path

from satellite.manifest import compute_config_sha, generate_run_id, save_manifest
from satellite.manifest_verify import verify_manifest


class SatelliteManifestVerifyTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.source = "test_src"
        self.date = "2026-02-27"

        (self.root / "satellite/sources").mkdir(parents=True, exist_ok=True)
        (self.root / f"satellite/rules").mkdir(parents=True, exist_ok=True)
        (self.root / f"satellite/prompts/{self.source}").mkdir(parents=True, exist_ok=True)
        (self.root / "satellite/sources/test_src.toml").write_text("url='https://example.com/rss'\n", encoding="utf-8")
        (self.root / "satellite/rules/test_src.toml").write_text("[constraints]\nmin_chars=1\n", encoding="utf-8")
        (self.root / "satellite/prompts/test_src/v1.txt").write_text("prompt\n", encoding="utf-8")

        raw_dir = self.root / f"data/satellite/{self.source}/raw/{self.date}"
        raw_dir.mkdir(parents=True, exist_ok=True)
        artifact = raw_dir / "item.json"
        artifact.write_text(json.dumps({"k": "v"}, sort_keys=True), encoding="utf-8")

        self.rel_artifact = str(artifact.relative_to(self.root))
        self.config_sha = compute_config_sha(self.source, self.root)
        self.code_version = "v1-dev"
        self.run_id = generate_run_id(self.date, self.source, self.config_sha, self.code_version)

        manifest_path = self.root / f"data/satellite/{self.source}/manifests/{self.date}.manifest.json"
        save_manifest(
            manifest_path,
            {
                "run_id": self.run_id,
                "date": self.date,
                "source_id": self.source,
                "config_sha": self.config_sha,
                "code_version": self.code_version,
                "artifacts": [
                    {
                        "path": self.rel_artifact,
                        "sha256": __import__("hashlib").sha256(artifact.read_bytes()).hexdigest(),
                        "bytes": artifact.stat().st_size,
                    }
                ],
            },
        )

    def tearDown(self):
        self.td.cleanup()

    def test_verify_manifest_pass_and_fail(self):
        ok = verify_manifest(self.source, self.date, self.root)
        self.assertTrue(ok["ok"])

        artifact_path = self.root / self.rel_artifact
        artifact_path.write_text("tampered", encoding="utf-8")
        ng = verify_manifest(self.source, self.date, self.root)
        self.assertFalse(ng["ok"])
        self.assertTrue(any("sha mismatch" in err for err in ng["errors"]))

    def test_verify_manifest_rejects_non_list_artifacts(self):
        manifest_path = self.root / f"data/satellite/{self.source}/manifests/{self.date}.manifest.json"
        payload = {
            "run_id": self.run_id,
            "date": self.date,
            "source_id": self.source,
            "config_sha": self.config_sha,
            "code_version": self.code_version,
            "artifacts": {"path": self.rel_artifact},
        }
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        out = verify_manifest(self.source, self.date, self.root)
        self.assertFalse(out["ok"])
        self.assertTrue(any("artifacts is not a list" in err for err in out["errors"]))

    def test_verify_manifest_missing_creates_verify_parent(self):
        source = "missing_src"
        date = "2026-02-28"
        out = verify_manifest(source, date, self.root)
        self.assertFalse(out["ok"])
        verify_path = self.root / f"data/satellite/{source}/manifests/{date}.verify.json"
        self.assertTrue(verify_path.exists())
        persisted = json.loads(verify_path.read_text(encoding="utf-8"))
        self.assertFalse(persisted["ok"])
        self.assertTrue(any("manifest missing" in err for err in persisted["errors"]))


if __name__ == "__main__":
    unittest.main()
