"""Verify both ZIPs in isolated paths using independent ingests and example models."""
import hashlib,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
from distribution import ROOT,SOURCE,NAME
version=(SOURCE/'VERSION').read_text().strip();release=ROOT/'releases'/version
records=[]
with tempfile.TemporaryDirectory(prefix='manual skill archive ') as td:
 for pkg in json.loads((release/'manifest.json').read_text())['packages']:
  zpath=release/pkg['archive'];assert hashlib.sha256(zpath.read_bytes()).hexdigest()==pkg['sha256']
  folder=Path(td)/pkg['profile'];folder.mkdir()
  with zipfile.ZipFile(zpath) as z:
   assert z.testzip() is None
   assert all(n.startswith(NAME+'/') and '..' not in Path(n).parts for n in z.namelist());z.extractall(folder)
  cli=folder/NAME/'scripts/manual_tool.py';cases=[]
  for case in ('desktop','mobile','mixed'):
   template={'desktop':'office','mobile':'delivery','mixed':'training'}[case]
   inp=ROOT/'examples/screenshots'/case;source=folder/(case+'.json')
   commands=[['ingest',*[str(inp/f'{i}.png') for i in (1,2,3)],'--notes',str(ROOT/'examples'/case/'notes.txt'),'--out',str(source)],['validate','--model',str(ROOT/'examples'/case/'model.json'),'--sources',str(source)],['render','--model',str(ROOT/'examples'/case/'model.json'),'--sources',str(source),'--out',str(folder/'交付'),'--template',template,'--pdf','off']]
   for command in commands:
    run=subprocess.run([sys.executable,str(cli),*command],capture_output=True,text=True,cwd=folder);assert run.returncode==0,(run.stdout,run.stderr)
   result=json.loads(run.stdout);assert result['skill_version']==version
   cases.append({'case':case,'template':result['template'],'word':result['word'],'pdf':result['pdf'],'standalone_pipeline':'passed'})
  records.append({'profile':pkg['profile'],'sha256':pkg['sha256'],'cases':cases})
(ROOT/'evidence'/version/'archive-smoke.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(records,ensure_ascii=False,indent=2))
