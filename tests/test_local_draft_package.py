import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'skills/yichen-jianying-edit/scripts/local_draft.py'


class LocalDraftPackageTests(unittest.TestCase):
    def test_pinned_experiment_skill_help_from_unrelated_directory(self):
        env = dict(os.environ, JIANYING_HEADLESS_ROOT=str(ROOT))
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run([sys.executable, str(ENTRY), '--codec', '/unused/codec', '--help'],
                                    cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('draft-only', result.stdout)

    def test_skill_refuses_export_before_codec_or_application_access(self):
        env = dict(os.environ, JIANYING_HEADLESS_ROOT=str(ROOT))
        result = subprocess.run([sys.executable, str(ENTRY), 'export'], env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no native export support', result.stderr)


if __name__ == '__main__':
    unittest.main()
