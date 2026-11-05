"""Export identical content through each native document layout for visual review."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/screenshot-to-manual/scripts'))
from common import load_json, version
from document import templates
from export import render

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--soffice', required=True)
parser.add_argument('--renderer', required=True)
parser.add_argument('--fontconfig')
args = parser.parse_args()
if args.fontconfig:
    os.environ['FONTCONFIG_FILE'] = args.fontconfig
results = []
case = ROOT / 'examples/mixed'
for template in templates():
    result = render(load_json(case/'model.json'), load_json(case/'sources.json'),
                    ROOT/'outputs'/version()/'templates'/template,
                    word='required', pdf='required', soffice=args.soffice, template=template)
    directory = Path(result['directory'])
    pages = directory/'qa-pages'
    run = subprocess.run([sys.executable, args.renderer, str(directory/'操作手册.docx'),
                          '--output_dir', str(pages), '--emit_pdf'], capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(run.stdout+run.stderr)
    record = {'template': template, 'name': templates()[template]['name'],
              'directory': str(directory.relative_to(ROOT)), 'word': result['word'], 'pdf': result['pdf'],
              'pages': len(list(pages.glob('page-*.png'))), 'visual_review': 'pending'}
    results.append(record)
    print(json.dumps(record, ensure_ascii=False), flush=True)
(ROOT/'evidence'/version()/'template-renders.json').write_text(
    json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
