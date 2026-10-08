#!/usr/bin/env python3
"""Replay the exact local draft experiment. GUI acceptance remains explicit."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import uuid

PACKAGE = Path(__file__).resolve().parent.parent


def digest(path):
    with Path(path).open('rb') as source:
        result = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')


def run_logged(command, cwd, log_dir, env=None):
    log_dir.mkdir(exist_ok=False, parents=True)
    started = datetime.datetime.now().astimezone().isoformat()
    begin = time.monotonic()
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                            text=True, timeout=600)
    (log_dir / 'stdout.txt').write_text(result.stdout)
    (log_dir / 'stderr.txt').write_text(result.stderr)
    record = {'command': command, 'cwd': str(cwd), 'started_at': started,
              'elapsed_s': round(time.monotonic() - begin, 3),
              'exit_code': result.returncode, 'gui_verified': False}
    write_new(log_dir / 'command.json', record)
    if result.returncode:
        raise SystemExit('Command failed; inspect ' + str(log_dir / 'stderr.txt'))
    return record


def skill_command(root, codec):
    root = Path(root).resolve(strict=True)
    core = root / 'CORE'
    entry = root / 'SKILL_REPO/yichen-jianying-edit/scripts/local_draft.py'
    if not core.is_dir() or not entry.is_file():
        raise SystemExit('Run unpack first; root must contain CORE and SKILL_REPO')
    env = dict(os.environ, JIANYING_HEADLESS_ROOT=str(core))
    return [sys.executable, str(entry), '--codec', str(Path(codec).resolve(strict=True))], env


def main():
    global PACKAGE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-dir', default=str(PACKAGE), help='Experience package root; required when using the public repository copy')
    sub = parser.add_subparsers(dest='phase', required=True)
    p = sub.add_parser('unpack'); p.add_argument('--out', required=True)
    p = sub.add_parser('compile'); p.add_argument('--root', required=True); p.add_argument('--out', required=True)
    for phase in ['build', 'publish', 'verify']:
        p = sub.add_parser(phase)
        p.add_argument('--root', required=True); p.add_argument('--codec', required=True)
        if phase == 'build':
            p.add_argument('--out', required=True)
            p.add_argument('--case', choices=['smoke', 'full'], default='smoke')
            p.add_argument('--name')
            p.add_argument('--font', default=str(Path.home() / 'Library/Fonts/AlibabaPuHuiTi-3-75-SemiBold.ttf'))
        else:
            p.add_argument('--case-dir', required=True)
        if phase == 'verify':
            p.add_argument('--label', required=True, help='Unique label, such as after-save or cold-01')
    args = parser.parse_args()
    PACKAGE = Path(args.package_dir).resolve(strict=True)
    if args.phase == 'unpack':
        out = Path(args.out).resolve(); out.mkdir(exist_ok=False, parents=True)
        meta = json.loads((PACKAGE / '环境与源码锁定.json').read_text())
        for name, dest in [('jianying-headless-b8f0c71.tar.gz', 'CORE'),
                           ('yichen-skills-83e6631.tar.gz', 'SKILL_REPO')]:
            archive_path = PACKAGE / '源码' / name
            if digest(archive_path) != meta['source_archives'][name]:
                raise SystemExit('Source archive differs: ' + name)
            target = out / dest; target.mkdir()
            with tarfile.open(archive_path, 'r:gz') as archive:
                for member in archive.getmembers():
                    candidate = (target / member.name).resolve()
                    if (member.issym() or member.islnk()
                            or not candidate.is_relative_to(target.resolve())):
                        raise SystemExit('Unsafe archive member: ' + member.name)
                archive.extractall(target)
        write_new(out / 'source-receipt.json', dict(meta, unpacked_at=datetime.datetime.now().astimezone().isoformat()))
        print(json.dumps({'status': 'unpacked', 'root': str(out)}, ensure_ascii=False))
    elif args.phase == 'compile':
        root = Path(args.root).resolve(strict=True)
        out = Path(args.out).resolve()
        record = run_logged([sys.executable, str(root / 'CORE/tools/build_local_draft_codec.py'),
                             '--out', str(out)], root, out.parent / (out.name + '-logs'))
        print(json.dumps(dict(record, codec=str(out / 'codec-probe')), ensure_ascii=False))
    elif args.phase == 'build':
        command, env = skill_command(args.root, args.codec)
        sample = PACKAGE / '示例' / ('3s最小样例' if args.case == 'smoke' else '50s完整案例')
        manifest = json.loads((sample / 'input-manifest.json').read_text())
        for relative, expected in manifest['assets'].items():
            if digest(sample / relative) != expected:
                raise SystemExit('Example input changed: ' + relative)
        font = Path(args.font).resolve(strict=True)
        if digest(font) != manifest['font']['sha256']:
            raise SystemExit('Different font requires a new layout review; this replay pins the tested font')
        out = Path(args.out).resolve(); out.mkdir(exist_ok=False, parents=True)
        plan = json.loads((sample / 'plan-template.json').read_text())
        plan['name'] = args.name or ('VERIFY-' + datetime.datetime.now().strftime('%m%d-%H%M%S')
                                     + '-' + args.case + '-' + uuid.uuid4().hex[:6])
        for track in plan['tracks']:
            for segment in track['segments']:
                if 'source' in segment:
                    segment['source'] = str((sample / segment['source']).resolve(strict=True))
                if 'font_path' in segment:
                    segment['font_path'] = str(font)
        write_new(out / 'plan.json', plan)
        records = [run_logged(command + ['doctor'], out, out / 'logs/doctor', env),
                   run_logged(command + ['build', '--plan', str(out / 'plan.json'),
                                         '--out', str(out / 'build')], out, out / 'logs/build', env),
                   run_logged(command + ['verify-build', '--build', str(out / 'build'),
                                         '--report', str(out / 'verify-build.json')], out,
                              out / 'logs/verify-build', env)]
        receipt = {'schema': 'jianying-experience-replay/v1', 'case': args.case,
                   'name': plan['name'], 'build': str(out / 'build'),
                   'plan_sha256': digest(out / 'plan.json'), 'records': records,
                   'live_written': False, 'gui_verified': False}
        write_new(out / 'replay-receipt.json', receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        command, env = skill_command(args.root, args.codec)
        case_dir = Path(args.case_dir).resolve(strict=True)
        if args.phase == 'publish':
            record = run_logged(command + ['publish', '--build', str(case_dir / 'build'),
                                          '--audit', str(case_dir / 'publish-audit')],
                                case_dir, case_dir / 'logs/publish', env)
            print(json.dumps(record, ensure_ascii=False))
        else:
            if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.label):
                raise SystemExit('Use a simple unique ASCII verification label')
            record = run_logged(command + ['verify', '--build', str(case_dir / 'build'),
                                          '--report', str(case_dir / ('verify-' + args.label + '.json'))],
                                case_dir, case_dir / ('logs/verify-' + args.label), env)
            print(json.dumps(record, ensure_ascii=False))


if __name__ == '__main__':
    main()
