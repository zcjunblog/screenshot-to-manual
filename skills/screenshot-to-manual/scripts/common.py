"""Shared bounded JSON and image source helpers; no network calls."""
import hashlib
import json
from pathlib import Path

MAX_FILE=10*1024*1024
MAX_PIXELS=40_000_000
MAX_TOTAL_PIXELS=120_000_000
MAX_IMAGES=20

def version():return (Path(__file__).resolve().parents[1]/'VERSION').read_text().strip()
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load_json(path):
    p=Path(path)
    if p.stat().st_size>5*1024*1024:raise ValueError('JSON超过5MiB限制')
    return json.loads(p.read_text(encoding='utf-8'))
def save_new(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
def text(value):return ''.join(c for c in str(value) if c in '\n\t' or ord(c)>=32)
def check_source(row):
    p=Path(row['path'])
    if not p.is_file() or p.stat().st_size>MAX_FILE or digest(p)!=row['sha256']:
        raise ValueError('来源图片已经改变或不可读，请重新登记：'+row['id'])
    return p

def source_bytes(row):
    # Decode the exact bounded snapshot whose hash was verified, even if the path changes.
    with Path(row['path']).open('rb') as f:data=f.read(MAX_FILE+1)
    if len(data)>MAX_FILE or hashlib.sha256(data).hexdigest()!=row['sha256']:
        raise ValueError('来源图片已经改变，请重新登记：'+row['id'])
    return data
