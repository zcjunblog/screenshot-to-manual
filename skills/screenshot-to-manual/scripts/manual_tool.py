#!/usr/bin/env python3
"""Screenshot to Manual CLI. The host Agent supplies screenshot understanding."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from common import load_json,save_new,version

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    sub.add_parser('templates')
    i=sub.add_parser('ingest');i.add_argument('images',nargs='+');i.add_argument('--notes',type=Path);i.add_argument('--out',required=True,type=Path)
    v=sub.add_parser('validate');v.add_argument('--model',required=True,type=Path);v.add_argument('--sources',required=True,type=Path)
    r=sub.add_parser('render');r.add_argument('--model',required=True,type=Path);r.add_argument('--sources',required=True,type=Path);r.add_argument('--out',required=True,type=Path)
    for flag in ('word','pdf'):r.add_argument('--'+flag,choices=('auto','off','required'),default='auto')
    r.add_argument('--template',choices=('office','delivery','training'),default='office')
    r.add_argument('--soffice',help='可选LibreOffice可执行文件路径')
    a=p.parse_args()
    if a.command=='templates':
        from document import templates
        print(json.dumps(templates(),ensure_ascii=False,indent=2));return 0
    if a.command=='doctor':
        from export import find_soffice
        result={'version':version(),'python':sys.version.split()[0],'python_supported':sys.version_info>=(3,9),
                'images':importlib.util.find_spec('PIL') is not None,'word':importlib.util.find_spec('docx') is not None,'pdf_converter':find_soffice() is not None}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    if a.command=='ingest':
        from intake import ingest
        notes=a.notes.read_text(encoding='utf-8') if a.notes else ''
        result=ingest(a.images,notes);save_new(a.out,result)
        print(json.dumps({'source_file':str(a.out.resolve()),'read':sum(r['status']=='ok' for r in result['images']),'failed':sum(r['status']!='ok' for r in result['images'])},ensure_ascii=False));return 0
    model=load_json(a.model);bundle=load_json(a.sources)
    if a.command=='validate':
        from validate import validate
        result=validate(model,bundle);print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if result['errors'] else 0
    from export import render
    print(json.dumps(render(model,bundle,a.out,a.word,a.pdf,a.soffice,a.template),ensure_ascii=False,indent=2));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,ImportError) as exc:print('错误：'+str(exc),file=sys.stderr);sys.exit(2)
