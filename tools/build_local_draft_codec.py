#!/usr/bin/env python3
"""Reproduce the separate draft-only codec with the observed local toolchain."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'engine'))
from local_draft_runtime import (APP, APP_VERSION, APP_BUILD, LIBRARY_SHA256,
                                 CODEC_SHA256, LocalDraftRuntime)
import headless_runtime as canonical


def run(cmd, env):
    result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise ValueError(result.stderr[-3000:])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, help='New isolated build directory')
    args = parser.parse_args()
    bridge = ROOT / 'bridge'
    if canonical.digest(bridge / 'SOURCE_MANIFEST.json') != canonical.IO_MANIFEST_SHA:
        raise ValueError('Canonical bridge manifest changed')
    manifest = json.loads((bridge / 'SOURCE_MANIFEST.json').read_text())
    for name, expected in manifest['source_files'].items():
        if canonical.digest(bridge / name) != expected:
            raise ValueError('Canonical bridge source changed: ' + name)
    info = plistlib.loads((APP / 'Contents/Info.plist').read_bytes())
    if ((info.get('CFBundleShortVersionString'), info.get('CFBundleVersion'), info.get('CFBundleIdentifier'))
            != (APP_VERSION, APP_BUILD, canonical.BUNDLE_ID)
            or canonical.digest(APP / 'Contents/Frameworks/libvideoeditor.dylib') != LIBRARY_SHA256):
        raise ValueError('Outside the one observed local draft application profile')
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C',
           'DEVELOPER_DIR': '/Library/Developer/CommandLineTools'}
    compiler = run(['/usr/bin/xcrun', 'clang++', '--version'], env).stdout.splitlines()[0]
    sdk = run(['/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-version'], env).stdout.strip()
    if compiler != 'Apple clang version 17.0.0 (clang-1700.4.4.1)' or sdk != '26.1':
        raise ValueError('Outside the observed local draft compiler/SDK profile')
    run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(APP)], env)
    signature = run(['/usr/bin/codesign', '-dv', '--verbose=4', str(APP)], env)
    if ('TeamIdentifier=' + canonical.TEAM) not in signature.stderr.splitlines():
        raise ValueError('Unexpected signing identity')
    out = canonical.fresh_directory(args.out)
    codec = out / 'codec-probe'
    command = ['/usr/bin/xcrun', 'clang++', '-std=c++17', '-arch', 'arm64', '-O2',
               '-mmacosx-version-min=26.0', 'bridge/jy14_codec.cpp',
               '-L' + str(APP / 'Contents/Frameworks'), '-lvideoeditor',
               '-Wl,-rpath,' + str(APP / 'Contents/Frameworks'), '-o', str(codec)]
    result = run(command, env)
    actual = canonical.digest(codec)
    report = {'schema': 'local-draft-codec-rebuild/v1', 'compiler': compiler, 'sdk': sdk,
              'command': command, 'codec_sha256': actual, 'expected_codec_sha256': CODEC_SHA256,
              'app_version': APP_VERSION, 'app_build': APP_BUILD, 'library_sha256': LIBRARY_SHA256,
              'source_files': manifest['source_files'], 'stderr': result.stderr,
              'canonical_codec_replaced': False, 'app_modified': False, 'official_library_copied': False}
    (out / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if actual != CODEC_SHA256:
        raise ValueError('Rebuilt local codec differs; retained evidence at ' + str(out))
    run(['/usr/bin/codesign', '--verify', '--strict', str(codec)], env)
    LocalDraftRuntime(codec).validate_runtime()
    print(json.dumps(dict(report, status='reproduced', codec=str(codec)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
