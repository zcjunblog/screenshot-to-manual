"""Shared source selection for portable packages and local installers."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NAME = 'screenshot-to-manual'
SOURCE = ROOT / 'skills' / NAME


def source_files(source=SOURCE):
    if source.is_symlink():
        raise ValueError('Skill source cannot be a symlink')
    files = []
    for p in sorted(source.rglob('*')):
        if '__pycache__' in p.parts or p.suffix == '.pyc':
            continue
        if p.is_symlink():
            raise ValueError('Symlink in skill source: ' + str(p))
        if not p.is_file():
            continue
        rel = p.relative_to(source)
        if rel.parts[0] not in ('SKILL.md', 'VERSION', 'requirements.txt', 'requirements-optional.txt', 'scripts', 'references', 'templates', 'agents'):
            raise ValueError('Unexpected skill resource: ' + str(rel))
        if p.stat().st_size > 1024 * 1024:
            raise ValueError('Oversized skill resource: ' + str(rel))
        if p.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
                if not link.startswith(('https:', 'http:', '#')) and not (p.parent / link).is_file():
                    raise ValueError('Missing linked resource: ' + link)
        files.append(p)
    return files


def skill_info(source=SOURCE):
    text = (source / 'SKILL.md').read_text(encoding='utf-8')
    parts = text.split('---\n', 2)
    if len(parts) != 3 or parts[0]:
        raise ValueError('Expected YAML frontmatter')
    # Our canonical source intentionally uses only two single-line scalar fields.
    fields = {}
    for line in parts[1].splitlines():
        key, value = line.split(':', 1)
        value = value.strip()
        fields[key] = json.loads(value) if value.startswith('"') else value
    if set(fields) != {'name', 'description'} or fields['name'] != NAME:
        raise ValueError('Canonical Skill must have only standard name/description fields')
    if not isinstance(fields['description'], str) or not 1 <= len(fields['description']) <= 1024:
        raise ValueError('Invalid description')
    version = (source / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid version')
    return fields, parts[2], version


def workbuddy_entry(fields, body, version):
    profile = json.loads((ROOT / 'distribution/workbuddy.json').read_text(encoding='utf-8'))
    values = {**fields, **profile, 'version': version}
    required = {'name', 'description', 'display_name', 'display_name_en', 'description_zh', 'description_en', 'version', 'author'}
    if not all(values.get(key) for key in required):
        raise ValueError('Missing WorkBuddy metadata')
    examples=[values.get(key,[]) for key in ('examples_zh','examples_en')]
    if any(not isinstance(items,list) or any(not isinstance(item,str) or not item.strip() for item in items) for items in examples):
        raise ValueError('WorkBuddy examples must be lists of non-empty strings')
    if len(examples[0])!=len(examples[1]):
        raise ValueError('WorkBuddy examples_zh and examples_en must have matching counts')
    lines = [key + ': ' + json.dumps(value, ensure_ascii=False) for key, value in values.items()]
    return ('---\n' + '\n'.join(lines) + '\n---\n' + body).encode('utf-8')
