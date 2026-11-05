#!/usr/bin/env python3
"""Build deterministic standard and WorkBuddy packages from a single skill source."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from distribution import ROOT, SOURCE, NAME, skill_info, source_files, workbuddy_entry


def build(out=None):
    fields, body, version = skill_info()
    files = source_files()
    dest = Path(out) if out else ROOT / 'releases' / version
    dest.mkdir(parents=True, exist_ok=True)
    packages = []
    for profile in ('standard', 'workbuddy'):
        suffix = '' if profile == 'standard' else '-workbuddy'
        archive = dest / f'{NAME}{suffix}-{version}.zip'
        entries = []
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in files:
                rel = p.relative_to(SOURCE).as_posix()
                data = workbuddy_entry(fields, body, version) if profile == 'workbuddy' and rel == 'SKILL.md' else p.read_bytes()
                info = zipfile.ZipInfo(NAME + '/' + rel, (2026, 11, 5, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, data)
                entries.append({'path': rel, 'sha256': hashlib.sha256(data).hexdigest()})
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise ValueError('Archive failed integrity check')
        packages.append({'profile': profile, 'archive': archive.name, 'bytes': archive.stat().st_size,
                         'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'files': entries})
    (dest / 'SHA256SUMS').write_text(''.join(p['sha256'] + '  ' + p['archive'] + '\n' for p in packages), encoding='utf-8')
    (dest / 'manifest.json').write_text(json.dumps({'version': version, 'packages': packages}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'version': version, 'directory': str(dest.resolve()), 'packages': [{k: v for k, v in p.items() if k != 'files'} for p in packages]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='Package output directory; defaults to releases/VERSION')
    args = parser.parse_args()
    print(json.dumps(build(args.out), ensure_ascii=False, indent=2))
