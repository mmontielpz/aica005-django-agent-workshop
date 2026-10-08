"""Focused A/B evidence isolation test using disposable script fixtures."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/isolate.sh"


class IsolationTest(unittest.TestCase):
    def test_a_hidden_during_b_and_restored_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "lab"
            scripts = root / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(SOURCE, scripts / "isolate.sh")
            (scripts / "reset.sh").write_text('#!/usr/bin/env bash\nset -e\nrm "$PWD/workspace/django/candidate.patch"\n')
            (scripts / "preflight.sh").write_text('#!/usr/bin/env bash\nset -e\ntest "$1" = --check\ntest ! -e "$PWD/workspace/django/candidate.patch"\n')
            (scripts / "results.py").write_text('import pathlib, sys\nassert sys.argv[1] == "compare"\npathlib.Path("reports/comparison.txt").write_text("compared")\n')
            django = root / "workspace/django"
            django.mkdir(parents=True)
            (django / "candidate.patch").write_text("A candidate")
            report = root / "reports/A"
            report.mkdir(parents=True)
            original = b"A evidence \x00\xff\n"
            (report / "evidence.zip").write_bytes(original)
            (report / "patch.diff").write_text("A solution patch")
            digest = hashlib.sha256((report / "evidence.zip").read_bytes()).hexdigest()
            outside = Path(tmp) / "outside"
            env = dict(os.environ, AICA005_ISOLATION_DIR=str(outside))
            def run(stage):
                return subprocess.run(["bash", "scripts/isolate.sh", stage], cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(run("before-b").returncode, 0)
            self.assertFalse(report.exists())
            self.assertFalse((django / "candidate.patch").exists())
            self.assertTrue((outside / "A.archived/patch.diff").exists())
            self.assertNotEqual(run("before-b").returncode, 0)
            (root / "reports/B").mkdir()
            (root / "reports/B/evidence.zip").write_bytes(b"B evidence")
            self.assertEqual(run("after-b").returncode, 0)
            self.assertEqual(hashlib.sha256((report / "evidence.zip").read_bytes()).hexdigest(), digest)
            self.assertEqual((report / "patch.diff").read_text(), "A solution patch")
            self.assertEqual((outside / "A.backup/evidence.zip").read_bytes(), original)
            self.assertEqual((root / "reports/comparison.txt").read_text(), "compared")


if __name__ == "__main__":
    unittest.main()
