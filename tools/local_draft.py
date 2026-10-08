#!/usr/bin/env python3
"""Explicit, draft-only local beta experiment; never enables native export."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'engine'))
import jy14_headless as builder
from local_draft_runtime import LocalDraftRuntime, validate_basic_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codec', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    p = sub.add_parser('build'); p.add_argument('--plan', required=True); p.add_argument('--out', required=True)
    for command in ('verify-build', 'verify', 'publish', 'resume-publish'):
        p = sub.add_parser(command); p.add_argument('--build', required=True)
        if command in {'publish', 'resume-publish'}:
            p.add_argument('--audit', required=True)
        else:
            p.add_argument('--report')
    args = parser.parse_args()
    runtime = LocalDraftRuntime(args.codec)
    if args.command == 'doctor':
        result = runtime.validate_runtime()
    elif args.command == 'build':
        validate_basic_plan(builder.read_json(args.plan))
        result = builder.build(args.plan, args.out, runtime_provider=runtime)
    else:
        record = builder.read_json(Path(args.build) / 'build.json')
        if record['runtime_profile'] != runtime.doctor()['runtime_profile']:
            raise ValueError('Build is outside this exact draft experiment')
        validate_basic_plan(builder.read_json(Path(args.build) / 'plan.json'))
        if args.command == 'verify-build':
            builder.verify_build(args.build, runtime_provider=runtime)
            result = {'status': 'verified', 'live_written': False, 'experimental': True}
        elif args.command == 'verify':
            runtime.helper()._ensure_editor_closed(True)
            result = builder.verify_live(args.build, runtime_provider=runtime)
        else:
            result = builder.publish(args.build, args.audit, resume=args.command == 'resume-publish',
                                     runtime_provider=runtime)
    result['experimental'] = True
    result['native_export_supported'] = False
    if getattr(args, 'report', None):
        builder.write(args.report, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
