"""Register originals and user notes. Dimensions use EXIF-oriented pixels."""
from pathlib import Path
import warnings
from common import MAX_FILE,MAX_IMAGES,MAX_PIXELS,MAX_TOTAL_PIXELS,digest

def ingest(paths,notes=''):
    from PIL import Image,ImageOps
    if not 1<=len(paths)<=MAX_IMAGES:raise ValueError('每批需1至20张PNG/JPEG截图')
    if len(notes)>100_000:raise ValueError('说明文本超过10万字符')
    images=[];seen={};total=0
    for i,path in enumerate(paths,1):
        p=Path(path).expanduser().resolve();row={'id':f'I{i:03d}','filename':p.name,'path':str(p),'status':'error','warnings':[]}
        try:
            if p.stat().st_size>MAX_FILE:raise ValueError('文件超过10MiB')
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(p) as im:
                    if im.format not in ('PNG','JPEG'):raise ValueError('仅支持PNG/JPEG')
                    if im.width*im.height>MAX_PIXELS:raise ValueError('单图超过4000万像素')
                    if total+im.width*im.height>MAX_TOTAL_PIXELS:raise ValueError('累计超过1.2亿像素')
                    oriented=ImageOps.exif_transpose(im);oriented.load();w,h=oriented.size
                    row.update(width=w,height=h,sha256=digest(p),status='ok')
                    total+=w*h
            if row['sha256'] in seen:row['duplicate_of']=seen[row['sha256']];row['warnings'].append('重复图片，保留并由Agent核对用途')
            else:seen[row['sha256']]=row['id']
            if min(w,h)<320:row['warnings'].append('分辨率较低，请核对界面文字清晰度')
        except (OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:row['error']=str(exc)
        images.append(row)
    lines=[line.strip() for line in notes.splitlines() if line.strip()]
    return {'schema_version':'1.0','images':images,'notes':[{'id':f'N{i:03d}','text':line} for i,line in enumerate(lines,1)]}
