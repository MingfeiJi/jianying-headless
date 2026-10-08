#!/usr/bin/env python3
"""Opt-in local beta draft experiment. Canonical entrypoint stays unchanged."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

configured = os.environ.get('JIANYING_HEADLESS_ROOT')
if not configured or not Path(configured).is_absolute():
    raise SystemExit('Set JIANYING_HEADLESS_ROOT to an absolute reviewed experiment checkout')
root = Path(configured).resolve(strict=True)
marker = root / 'project.json'
if marker.is_symlink() or json.loads(marker.read_text()).get('id') != 'jianying-headless':
    raise SystemExit('Invalid Jianying Headless checkout')
PINS = {'native_fonts.py': 'ddd7b4c1ecd55890bd645c14930f2c5f6687794691c2280daa32673e048da5e6',
 'runtime_profiles.py': 'f285ddf16d5ad381a9165becc443dd11352663bdb28a1b5d7eccd31b2cd6209e',
 'jy14_headless.py': '7f9f2a4fce2de4f47b0e3104172182d9d0d87a6bcf42e353ad67cb3f889b1b6d',
 'native_motion.py': '5d743caaa38c921779166e5663d36f72a0c3fdb130a690ac3942a7adcf62d6c2',
 'native_effects.py': 'c46b2fc9221dd613f220564b752e532f8f3753dd5595aaffc24f41d5236e4e97',
 'native_resources.py': '9bddfbb1cd688cebd69ac49f9bbf63c242522d9666a2ef7b412fe097113f68f2',
 'native_visual_effects.py': '15df7e56cc7d575a552c180e72ec712f136c618d271b2f3ad2d32dd5929e844c',
 'native-resource-catalog.json': '97af2df27463a9183fb1aa8f2ef534b37a644cb196f340fe88fdc50b456abde9',
 'native_compound.py': 'eb9e7d5544e1726be291912c47a5cc917b80180a231242ca30b7b5aaf68f5bfc',
 'compound-blueprint.json': '9cba9435053280abf9072d5eaccb8586c841b11dac6854b32daf9cbdba76af8e',
 'native_edit.py': '151d2adaa582a6a45dcc9ef7606c1e68ef43110602b264fba7d8fcef2235b36e',
 'native_export.py': '10191828c86c12396c77be5ac7a39ee712c4b5f1ac341a09f73418eac5d7202d',
 'native_export.cpp': 'c60da6c65f5bb7ac733b8f5b619401be3921f9254b953a55903d4e7566156379',
 'headless_runtime.py': '81d75135473eb531688099b45a5a2acf922b4c385a8feaf39f0c92963b46ccca',
 'blueprint.json': '91f7eddad5bff9af23eb88b53713c180e3e3d4054edd469140cfa9aa56bc1dc9',
 'windows_portable.py': '707e5f1040ad59384f864e5e2ad41ff2c93853be8c7bd562d44f6fb632d244ca',
 'windows_export.py': 'b4f20ce94b6ca0a72d5c542bc56ce9fd23a13a09826ba71a34beb99e23474fc8',
 'ffmpeg_graph.py': 'bc0d897993f9e7c2c5f6c0233a3002c07e235323da20fe0eca2755f1410aa594',
 'ffmpeg_tools.py': 'c8d0817c57573e0e755f3277466fa13e08bdc588d90471344faaf30438e9992f',
 'local_draft_runtime.py': 'b380ee8097e24331de8c8b8214b653fc125e1eb8bd3dfafb3fee5d71eb7e1566'}
TOOL_PINS = {'local_draft.py': '7777fe3a334f51937d5b1cfa67b99212bedafbadf9916ea06df9783fd106f4c6',
 'build_local_draft_codec.py': '3e8d501ec1807fadd795a78abb91c20d7529274854584f8b05ee8b0b14225c42'}
for subdir, pins in [('engine', PINS), ('tools', TOOL_PINS)]:
    for name, expected in pins.items():
        path = root / subdir / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Unreviewed local draft component: ' + name)
if 'export' in sys.argv[1:]:
    raise SystemExit('This draft experiment has no native export support')
runpy.run_path(str(root / 'tools/local_draft.py'), run_name='__main__')
