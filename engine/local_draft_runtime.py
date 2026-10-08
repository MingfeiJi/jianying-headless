"""Opt-in draft-only experiment for one observed, signed beta build.

Canonical application/codec/export profiles remain unchanged. This backend
accepts only the separately compiled bridge whose exact bytes passed local
round trips. It provides no native export or cached-effect compatibility.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import subprocess
import threading
from types import SimpleNamespace

import headless_runtime as canonical

APP_VERSION = '11.5.13264'
APP_BUILD = '11.6.0-beta6'
LIBRARY_SHA256 = 'e3a30819d30f008ed8fa9b147f98adb09b0b4b9dc788f599ef1bcb4901a70d0d'
CODEC_SHA256 = '57eab54b180f37b45278dff33d02528d587e366df824aae0734360140acbe138'
PROFILE = 'experimental-local-draft-macos-11.5.13264-beta6'
APP = canonical.APP
DRAFT_ROOT = canonical.DRAFT_ROOT
MANIFEST_SHA = canonical.MANIFEST_SHA
digest = canonical.digest
packed = canonical.packed
fresh_directory = canonical.fresh_directory


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate_timeline_schema(timeline, runtime_profile=None):
    schema = (timeline.get('new_version'), timeline.get('version'))
    require(type(schema[1]) is int and schema in {('185.0.0', 360000), ('189.0.0', 360000)},
            'Unobserved timeline schema for local draft experiment')
    require(runtime_profile in {None, PROFILE}, 'Different local draft runtime profile')
    if schema[0] == '189.0.0':
        require(timeline.get('last_modified_platform', {}).get('app_version') == APP_BUILD,
                'Saved schema must identify the exact observed beta build')
    return schema


class LocalDraftRuntime:
    APP = APP
    DRAFT_ROOT = DRAFT_ROOT
    MANIFEST_SHA = MANIFEST_SHA
    digest = staticmethod(digest)
    packed = staticmethod(packed)
    fresh_directory = staticmethod(fresh_directory)
    validate_timeline_schema = staticmethod(validate_timeline_schema)

    def __init__(self, codec):
        self.codec = Path(codec)
        require(self.codec.is_absolute(), 'Local codec path must be absolute')
        bridge = Path(__file__).resolve().parent.parent / 'bridge'
        require(digest(bridge / 'SOURCE_MANIFEST.json') == canonical.IO_MANIFEST_SHA,
                'Canonical bridge source manifest changed')
        manifest = json.loads((bridge / 'SOURCE_MANIFEST.json').read_text())
        for name, expected in manifest['source_files'].items():
            path = bridge / name
            require(path.is_file() and not path.is_symlink() and digest(path) == expected,
                    'Unreviewed bridge source: ' + name)
        spec = importlib.util.spec_from_file_location('_local_draft_secure_io', bridge / 'runtime_io.py')
        self.io = importlib.util.module_from_spec(spec)
        # dataclasses resolves the module when the canonical helper is loaded.
        import sys
        sys.modules[spec.name] = self.io
        spec.loader.exec_module(self.io)
        self.io._tool_pin(self.codec, CODEC_SHA256, 'codec')

    def doctor(self):
        self.io._tool_pin(self.codec, CODEC_SHA256, 'codec')
        info = plistlib.loads((APP / 'Contents/Info.plist').read_bytes())
        require((info.get('CFBundleShortVersionString'), info.get('CFBundleVersion'),
                 info.get('CFBundleIdentifier')) == (APP_VERSION, APP_BUILD, canonical.BUNDLE_ID),
                'Exact local draft application identity changed')
        require(digest(APP / 'Contents/Frameworks/libvideoeditor.dylib') == LIBRARY_SHA256,
                'Exact local draft library changed')
        return {'status': 'ok', 'app_version': APP_VERSION, 'app_build': APP_BUILD,
                'bundle_id': canonical.BUNDLE_ID, 'runtime_profile': PROFILE,
                'libvideoeditor_sha256': LIBRARY_SHA256, 'codec_sha256': CODEC_SHA256,
                'experimental': True, 'capabilities': ['basic-editable-draft'],
                'native_export_supported': False, 'cached_effects_supported': False,
                'network_called': False, 'app_modified': False}

    def validate_runtime(self):
        before = self.doctor()
        env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'}
        check = subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(APP)],
                               capture_output=True, timeout=180, env=env)
        details = subprocess.run(['/usr/bin/codesign', '-dv', '--verbose=4', str(APP)],
                                 capture_output=True, text=True, timeout=30, env=env)
        require(check.returncode == 0 and details.returncode == 0
                and ('TeamIdentifier=' + canonical.TEAM) in details.stderr.splitlines(),
                'Application signature or signing identity failed')
        require(self.doctor() == before, 'Local runtime changed during signature verification')
        return dict(before, full_signature_check='passed', team_identifier=canonical.TEAM)

    def _decode(self, path):
        self.doctor()
        snapshot = self.io._snapshot_file(Path(path), 'local draft ciphertext')
        read_fd, write_fd = os.pipe()
        chunks, errors = [], []
        def reader():
            total = 0
            try:
                while True:
                    chunk = os.read(read_fd, self.io.READ_CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
                    require(total <= self.io.MAX_METADATA_PLAINTEXT_BYTES, 'Plaintext exceeds limit')
                    chunks.append(chunk)
            except BaseException as exc:
                errors.append(exc)
            finally:
                os.close(read_fd)
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        try:
            proc = subprocess.Popen([str(self.codec), 'decrypt-fd', str(path), str(write_fd)],
                                    pass_fds=(write_fd,), cwd=self.codec.parent,
                                    env={'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'},
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except BaseException:
            os.close(write_fd)
            thread.join(5)
            raise
        os.close(write_fd)
        try:
            proc.communicate(timeout=self.io.COMMAND_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate()
            raise ValueError('Local draft decode timeout')
        finally:
            thread.join(10)
        require(not thread.is_alive() and not errors and proc.returncode == 0,
                'Local draft decode failed')
        self.io._revalidate_snapshot(snapshot, 'after local draft decode')
        self.doctor()
        return self.io._parse_strict_json(b''.join(chunks), 'local draft plaintext')

    def _encode(self, raw, output):
        self.doctor()
        require(isinstance(raw, bytes) and 0 < len(raw) <= self.io.MAX_METADATA_PLAINTEXT_BYTES,
                'Invalid local draft plaintext size')
        # Parsing rejects duplicate keys, nonfinite values and non-object roots.
        self.io._parse_strict_json(raw, 'local draft plaintext')
        read_fd, write_fd = os.pipe()
        errors = []
        def writer():
            try:
                self.io._write_all(write_fd, raw, Path('<anonymous local draft pipe>'))
            except BaseException as exc:
                errors.append(exc)
            finally:
                os.close(write_fd)
        thread = threading.Thread(target=writer, daemon=True)
        thread.start()
        try:
            proc = subprocess.Popen([str(self.codec), 'encrypt-fd', str(read_fd), str(output)],
                                    pass_fds=(read_fd,), cwd=self.codec.parent,
                                    env={'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'},
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except BaseException:
            os.close(read_fd)
            thread.join(5)
            raise
        os.close(read_fd)
        try:
            proc.communicate(timeout=self.io.COMMAND_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate()
            raise ValueError('Local draft encode timeout')
        finally:
            thread.join(10)
        require(not thread.is_alive() and not errors and proc.returncode == 0,
                'Local draft encode failed; output was retained')
        self.doctor()

    def helper(self):
        self.doctor()
        names = ('_ensure_editor_closed', '_snapshot_file', '_parse_strict_json',
                 '_revalidate_snapshot', '_acquire_directory_transaction_lock',
                 '_release_directory_transaction_lock')
        return SimpleNamespace(**{n: getattr(self.io, n) for n in names},
                               _decrypt_metadata_in_memory=self._decode,
                               _encrypt_metadata_from_memory=self._encode,
                               _validate_runtime_environment=self.validate_runtime)


def validate_basic_plan(plan):
    require(set(t['type'] for t in plan['tracks']) <= {'video', 'text', 'audio'},
            'Local experiment supports basic media/text/audio tracks only')
    forbidden = {'mask', 'transition_out', 'text_effect', 'text_animation'}
    for track in plan['tracks']:
        for seg in track['segments']:
            require(not forbidden.intersection(seg), 'Cached native effects are outside this experiment')
