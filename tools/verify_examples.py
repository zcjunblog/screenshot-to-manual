"""Generate and render every actual demo case; requires caller document runtime."""
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'skills/screenshot-to-manual/scripts'))
from common import load_json,version
from export import render
p=argparse.ArgumentParser();p.add_argument('--soffice',required=True);p.add_argument('--renderer',required=True);p.add_argument('--fontconfig');a=p.parse_args()
if a.fontconfig:os.environ['FONTCONFIG_FILE']=a.fontconfig
results=[]
for name in ('desktop','mobile','mixed'):
 case=ROOT/'examples'/name
 result=render(load_json(case/'model.json'),load_json(case/'sources.json'),ROOT/'outputs'/version()/name,word='required',pdf='required',soffice=a.soffice)
 directory=Path(result['directory']);pages=directory/'qa-pages'
 run=subprocess.run([sys.executable,a.renderer,str(directory/'操作手册.docx'),'--output_dir',str(pages),'--emit_pdf'],capture_output=True,text=True)
 if run.returncode:raise RuntimeError(run.stdout+run.stderr)
 results.append({'case':name,'directory':str(directory.relative_to(ROOT)),'word':result['word'],'pdf':result['pdf'],'pages':len(list(pages.glob('page-*.png'))),'visual_review':'pending'})
 print(name,results[-1],flush=True)
p=ROOT/'evidence'/version()/'document-renders.json';p.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
