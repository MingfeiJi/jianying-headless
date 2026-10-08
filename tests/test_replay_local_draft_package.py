import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest


ENTRY = Path(__file__).resolve().parents[1] / 'tools/replay_local_draft_package.py'


class ReplayPackageTest(unittest.TestCase):
    def test_cli_loads_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ENTRY), '--help'], cwd=directory,
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--package-dir', result.stdout)
        self.assertIn('unpack,compile,build,publish,verify', result.stdout)

    def test_changed_archive_stops_before_extracting_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'package'; (package / '源码').mkdir(parents=True)
            archive = package / '源码/jianying-headless-b8f0c71.tar.gz'
            archive.write_bytes(b'not the locked source archive')
            (package / '环境与源码锁定.json').write_text(json.dumps({
                'source_archives': {archive.name: '0' * 64}}))
            output = root / 'output'
            result = subprocess.run([sys.executable, str(ENTRY), '--package-dir', str(package),
                                     'unpack', '--out', str(output)], cwd=root,
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Source archive differs', result.stderr)
            self.assertFalse((output / 'CORE').exists())
            self.assertFalse((output / 'source-receipt.json').exists())

    def test_hash_matching_archive_still_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'package'; (package / '源码').mkdir(parents=True)
            archive = package / '源码/jianying-headless-b8f0c71.tar.gz'
            with tarfile.open(archive, 'w:gz') as output:
                item = tarfile.TarInfo('outside-link')
                item.type = tarfile.SYMTYPE
                item.linkname = '/outside-package'
                output.addfile(item)
            (package / '环境与源码锁定.json').write_text(json.dumps({
                'source_archives': {archive.name: hashlib.sha256(archive.read_bytes()).hexdigest()}}))
            output = root / 'output'
            result = subprocess.run([sys.executable, str(ENTRY), '--package-dir', str(package),
                                     'unpack', '--out', str(output)], cwd=root,
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unsafe archive member', result.stderr)
            self.assertFalse((output / 'CORE/outside-link').exists())
            self.assertFalse((output / 'source-receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
