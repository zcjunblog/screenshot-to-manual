#!/usr/bin/env python3
"""Copy a portable skill into a selected client's skill directory, without changing settings."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid
from distribution import SOURCE, NAME, skill_info, source_files

CLIENTS = {
    'generic': ('.agents/skills', '.agents/skills'),
    'codex': ('.agents/skills', '.agents/skills'),
    'claude': ('.claude/skills', '.claude/skills'),
    'cursor': ('.cursor/skills', '.cursor/skills'),
    'copilot': ('.github/skills', '.copilot/skills'),
    'gemini': ('.gemini/skills', '.gemini/skills'),
    'opencode': ('.opencode/skills', '.config/opencode/skills'),
}


def destination(client, scope, project=None, user_root=None):
    base = Path(project or Path.cwd()) if scope == 'project' else Path(user_root or Path.home())
    return base.expanduser().resolve() / CLIENTS[client][0 if scope == 'project' else 1] / NAME


def install(target, replace=False, dry_run=False, work_dir=None):
    target = Path(target).expanduser().absolute()
    # Refuse routing through symlinks; avoid silently replacing another client's files.
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError('Destination contains a symlink; choose its intended real directory explicitly')
    target = target.resolve()
    if target == SOURCE or SOURCE in target.parents or target in SOURCE.parents:
        raise ValueError('Destination overlaps repository skill source')
    files = source_files()
    _, _, version = skill_info()
    if target.exists() and not target.is_dir():
        raise ValueError('Destination exists and is not a directory')
    if target.exists() and not replace:
        raise ValueError('Skill already exists; use --replace to back it up before replacing')
    state = Path(work_dir).expanduser().absolute() if work_dir else target.parent.parent
    if any(p.is_symlink() for p in (state, *state.parents)):
        raise ValueError('Work directory contains a symlink; choose its real location')
    state = state.resolve()
    if state == target.parent or target.parent in state.parents or state == SOURCE or SOURCE in state.parents:
        raise ValueError('Work directory must be outside skills root and repository skill source')
    result = {'version': version, 'destination': str(target), 'dry_run': dry_run, 'backup': None, 'work_directory': str(state)}
    if dry_run:
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    # Keep incomplete skills and backups outside the selected discovery root.
    state.mkdir(parents=True, exist_ok=True)
    if os.stat(state).st_dev != os.stat(target.parent).st_dev:
        raise ValueError('Work directory must be on the same filesystem as the skills root')
    try:
        staging = Path(tempfile.mkdtemp(prefix='.skill-stage-', dir=str(state)))
    except PermissionError as exc:
        raise ValueError('Cannot stage here; use --work-dir with a writable directory outside the skills root on the same filesystem') from exc
    backup = None
    try:
        for p in files:
            dst = staging / p.relative_to(SOURCE)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
        if target.exists():
            backups = state / 'skill-backups'
            if backups.is_symlink():
                raise ValueError('Backup directory cannot be a symlink')
            backups.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
            backup = backups / (NAME + '-' + stamp + '-' + uuid.uuid4().hex[:8])
            target.rename(backup)
        try:
            staging.rename(target)
        except Exception:
            if backup is not None and not target.exists():
                backup.rename(target)
            raise
        result['backup'] = str(backup) if backup else None
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--client', choices=sorted(CLIENTS))
    group.add_argument('--dest', type=Path, help='Custom skills root; the named skill subfolder is added')
    p.add_argument('--scope', choices=('project', 'user'), default='project')
    p.add_argument('--project', type=Path, help='Project root (default: current working directory)')
    p.add_argument('--work-dir', type=Path, help='Writable staging/backup directory outside the skills root, on the same filesystem')
    p.add_argument('--replace', action='store_true', help='Back up an existing skill before replacement')
    p.add_argument('--dry-run', action='store_true', help='Show destination without writing files')
    a = p.parse_args()
    if a.dest and (a.project or a.scope != 'project'):
        p.error('--dest cannot be combined with --project or --scope user')
    if a.scope == 'user' and a.project:
        p.error('--project does not apply to user scope')
    custom = a.dest.expanduser().absolute() if a.dest else None
    target = custom.parent.resolve() / custom.name / NAME if custom else destination(a.client, a.scope, a.project)
    try:
        print(json.dumps(install(target, a.replace, a.dry_run, a.work_dir), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        p.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
