"""Publish previously reviewed template exports and compose their actual-page preview."""
import argparse
import json
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--font', required=True, type=Path, help='Locally installed CJK font, not bundled')
args = parser.parse_args()
records = json.loads((ROOT/'evidence/0.1.0/template-renders.json').read_text())
if any(r['visual_review'] != 'passed' for r in records):
    raise ValueError('Render and visually review every page before publishing examples')
font = lambda size: ImageFont.truetype(str(args.font), size)
canvas = Image.new('RGB', (1560, 1010), '#EDF3FA')
draw = ImageDraw.Draw(canvas)
draw.text((60, 38), '同一组截图 · 三种手册版式', font=font(40), fill='#142B48')
draw.text((62, 101), '可编辑 Word  /  PDF  /  Markdown  ·  截图转操作手册', font=font(22), fill='#62758C')
labels = {'office': ('清爽办公', '信息摘要与流程总览'),
          'delivery': ('正式交付', '独立封面与交接结构'),
          'training': ('培训图解', '大图在前，操作与检查分开')}
for index, record in enumerate(records):
    source = ROOT/record['directory']
    destination = ROOT/'examples/template-previews'/record['template']
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('操作手册.docx', '操作手册.pdf', '操作手册.md', '待补充信息.md', '操作手册-移交包.zip'):
        shutil.copy2(source/name, destination/name)
    shutil.copytree(source/'assets', destination/'assets', dirs_exist_ok=True)
    page = Image.open(source/'qa-pages/page-1.png').convert('RGB')
    page.thumbnail((445, 708))
    x = 60+index*500
    draw.rounded_rectangle((x-4, 252, x+449, 253+page.height), radius=5, fill='#D5DFEC')
    canvas.paste(page, (x, 247))
    name, detail = labels[record['template']]
    draw.text((x, 174), name, font=font(28), fill='#142B48')
    draw.text((x, 214), detail, font=font(18), fill='#62758C')
    draw.text((x, 930), f"{record['pages']} 页示例  ·  {record['template']}", font=font(20), fill='#426080')
    shutil.copy2(source/'qa-pages/page-1.png', destination/'preview.png')
shutil.copytree(ROOT/'examples/template-previews/office', ROOT/'examples/sample-manual', dirs_exist_ok=True)
canvas.save(ROOT/'examples/template-previews/overview.png')
print('Published three reviewed template examples.')
