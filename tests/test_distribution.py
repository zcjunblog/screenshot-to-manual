"""Observable distribution behavior: standalone packages and non-destructive installs."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NAME='screenshot-to-manual'
sys.path.insert(0,str(ROOT/'tools'))
from distribution import skill_info, workbuddy_entry

class DistributionTests(unittest.TestCase):
    def test_workbuddy_examples_have_matching_translations(self):
        profile=json.loads((ROOT/'distribution/workbuddy.json').read_text())
        self.assertEqual(len(profile['examples_zh']),len(profile['examples_en']))

    def test_workbuddy_build_rejects_invalid_examples(self):
        from unittest.mock import patch
        fields,body,version=skill_info()
        profile=json.loads((ROOT/'distribution/workbuddy.json').read_text())
        for invalid in (['one'], 'not-a-list', [None]*3):
            with self.subTest(invalid=invalid):
                with patch('distribution.json.loads',return_value={**profile,'examples_en':invalid}):
                    with self.assertRaises(ValueError): workbuddy_entry(fields,body,version)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='agent distribution ')
        self.root=Path(self.tmp.name).resolve()
    def tearDown(self): self.tmp.cleanup()
    def command(self,tool,*args):
        return subprocess.run([sys.executable,str(ROOT/'tools'/tool),*map(str,args)],capture_output=True,text=True)
    def test_standard_entrypoint_and_resources(self):
        skill=ROOT/'skills'/NAME
        self.assertTrue((skill/'SKILL.md').is_file(),'standard skill source must be available')
        text=(skill/'SKILL.md').read_text()
        front=text.split('---\n',2)[1]
        self.assertEqual(set(re.findall(r'^([a-z_-]+):',front,re.M)),{'name','description'})
        self.assertNotIn('WorkBuddy',text.split('---\n',2)[2])
        self.assertTrue((skill/'agents/openai.yaml').is_file())
    def test_two_standalone_reproducible_packages(self):
        out=self.root/'packages'
        p=self.command('build_release.py','--out',out)
        self.assertEqual(p.returncode,0,p.stderr)
        archives=sorted(out.glob('*.zip'))
        self.assertEqual(len(archives),2,'must build generic and WorkBuddy archives')
        snapshots={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in archives}
        for archive in archives:
            with zipfile.ZipFile(archive) as z:
                text=z.read(NAME+'/SKILL.md').decode()
                if '-workbuddy-' in archive.name:
                    self.assertIn('display_name:',text)
                else:
                    self.assertNotIn('display_name:',text)
                self.assertTrue(all(n.startswith(NAME+'/') and '..' not in Path(n).parts for n in z.namelist()))
                target=self.root/archive.stem
                z.extractall(target)
            p=subprocess.run([sys.executable,str(target/NAME/'scripts/manual_tool.py'),'doctor'],capture_output=True,text=True,cwd=target)
            self.assertEqual(p.returncode,0,p.stderr)
        with zipfile.ZipFile(archives[0]) as a,zipfile.ZipFile(archives[1]) as b:
            self.assertEqual(set(a.namelist()),set(b.namelist()))
            for name in a.namelist():
                if name.endswith('/SKILL.md'):
                    self.assertEqual(a.read(name).decode().split('---\n',2)[2],b.read(name).decode().split('---\n',2)[2])
                else:self.assertEqual(a.read(name),b.read(name),name)
        p=self.command('build_release.py','--out',out)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(snapshots,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in archives})
    def test_client_installs_and_dry_run(self):
        paths={'codex':'.agents/skills','claude':'.claude/skills','cursor':'.cursor/skills','copilot':'.github/skills','gemini':'.gemini/skills','opencode':'.opencode/skills','generic':'.agents/skills'}
        for client,folder in paths.items():
            with self.subTest(client=client):
                project=self.root/client
                p=self.command('install.py','--client',client,'--project',project,'--dry-run')
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertFalse(project.exists())
                p=self.command('install.py','--client',client,'--project',project)
                self.assertEqual(p.returncode,0,p.stderr)
                dest=project/folder/NAME
                self.assertTrue((dest/'SKILL.md').is_file())
                self.assertFalse((dest/'tests').exists())
                self.assertFalse((dest/'README.md').exists())
                result=json.loads(p.stdout)
                self.assertEqual(Path(result['destination']),dest)
                run=subprocess.run([sys.executable,str(dest/'scripts/manual_tool.py'),'doctor'],cwd=self.root,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
    def test_reinstall_refuses_and_replace_preserves_backup(self):
        project=self.root/'project'
        args=['--client','claude','--project',project]
        p=self.command('install.py',*args); self.assertEqual(p.returncode,0,p.stderr)
        dest=project/'.claude/skills'/NAME
        (dest/'user-note.txt').write_text('preserve me')
        p=self.command('install.py',*args)
        self.assertNotEqual(p.returncode,0)
        self.assertEqual((dest/'user-note.txt').read_text(),'preserve me')
        p=self.command('install.py',*args,'--replace')
        self.assertEqual(p.returncode,0,p.stderr)
        backup=Path(json.loads(p.stdout)['backup'])
        self.assertNotIn('skills',backup.relative_to(project).parts)
        self.assertEqual((backup/'user-note.txt').read_text(),'preserve me')
        self.assertFalse((dest/'user-note.txt').exists())
    def test_custom_destination_and_symlink_protection(self):
        dest=self.root/'custom'
        p=self.command('install.py','--dest',dest)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue((dest/NAME/'SKILL.md').is_file())
        outside=self.root/'outside'; outside.mkdir()
        link=self.root/'linked'; link.symlink_to(outside,target_is_directory=True)
        p=self.command('install.py','--dest',link)
        self.assertNotEqual(p.returncode,0)
        self.assertFalse((outside/NAME).exists())

    def test_user_scope_and_invalid_arguments_do_not_target_project(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from install import destination
        user_root=self.root/'user'
        for client,folder in {'codex':'.agents/skills','claude':'.claude/skills','cursor':'.cursor/skills','copilot':'.copilot/skills','gemini':'.gemini/skills','opencode':'.config/opencode/skills'}.items():
            self.assertEqual(destination(client,'user',user_root=user_root),user_root/folder/NAME)
        p=self.command('install.py','--client','codex','--scope','user','--project',self.root/'invalid')
        self.assertNotEqual(p.returncode,0)
        self.assertFalse((self.root/'invalid').exists())

    def test_replacement_rejects_symlinked_backup_root(self):
        project=self.root/'project'
        args=['--client','claude','--project',project]
        p=self.command('install.py',*args); self.assertEqual(p.returncode,0,p.stderr)
        dest=project/'.claude/skills'/NAME
        (dest/'note.txt').write_text('keep')
        elsewhere=self.root/'elsewhere'; elsewhere.mkdir()
        (project/'.claude/skill-backups').symlink_to(elsewhere,target_is_directory=True)
        p=self.command('install.py',*args,'--replace')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual((dest/'note.txt').read_text(),'keep')
        self.assertEqual(list(elsewhere.iterdir()),[])

    def test_dotdot_cannot_target_repository_source(self):
        alias=ROOT/'skills/other/..'
        p=self.command('install.py','--dest',alias,'--replace','--dry-run')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('overlaps',p.stderr)

    def test_custom_root_with_explicit_writable_work_directory(self):
        shared=self.root/'shared'; skills=shared/'skills'; skills.mkdir(parents=True)
        state=self.root/'installer-state'
        shared.chmod(0o555)
        try:
            p=self.command('install.py','--dest',skills,'--work-dir',state)
            self.assertEqual(p.returncode,0,p.stderr)
            dest=skills/NAME
            self.assertTrue((dest/'SKILL.md').is_file())
            (dest/'note.txt').write_text('keep')
            p=self.command('install.py','--dest',skills,'--work-dir',state,'--replace')
            self.assertEqual(p.returncode,0,p.stderr)
            backup=Path(json.loads(p.stdout)['backup'])
            self.assertEqual((backup/'note.txt').read_text(),'keep')
            self.assertTrue(state in backup.parents)
        finally: shared.chmod(0o755)

    def test_work_directory_cannot_be_scanned_skill_root(self):
        root=self.root/'skills'
        p=self.command('install.py','--dest',root,'--work-dir',root)
        self.assertNotEqual(p.returncode,0)
        self.assertFalse((root/NAME).exists())
        self.assertIn('outside skills root',p.stderr)

if __name__=='__main__': unittest.main()
