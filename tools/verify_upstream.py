"""Verify the complete, pinned upstream snapshot without installing dependencies."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'upstream/claude-video-studio.lock.json'


def verify(index=False):
    manifest = json.loads(LOCK.read_text(encoding='utf-8'))
    base = ROOT / manifest['destination']
    expected = {entry['path']: entry for entry in manifest['files']}
    actual = {p.relative_to(base).as_posix() for p in base.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    errors = [f'Missing: {name}' for name in sorted(expected.keys() - actual)]
    errors += [f'Unexpected: {name}' for name in sorted(actual - expected.keys())]
    for name in sorted(actual & expected.keys()):
        content = (base / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != expected[name]['sha256']:
            errors.append(f'Changed: {name}')
        if index:
            path = f"{manifest['destination']}/{name}"
            staged = subprocess.check_output(['git', 'ls-files', '-s', '--', path], cwd=ROOT, text=True).strip()
            fields = staged.split()
            if len(fields) < 3 or fields[:2] != [expected[name]['mode'], expected[name]['git_blob_sha']]:
                errors.append(f'Git index differs: {name}')
    report = {'source': manifest['repository'], 'commit': manifest['commit'],
              'files': len(expected), 'bytes': sum(e['bytes'] for e in expected.values()),
              'byteIdentical': not errors, 'indexChecked': index, 'errors': errors}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return not errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', action='store_true', help='Also verify staged Git blobs and executable modes')
    sys.exit(0 if verify(parser.parse_args().index) else 1)
