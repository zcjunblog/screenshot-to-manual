"""Structural checks; screenshot semantics remain an Agent/human responsibility."""
import math
import re
from common import MAX_IMAGES,MAX_PIXELS,MAX_TOTAL_PIXELS

def valid_box(box,w,h):
    return (isinstance(box,list) and len(box)==4 and all(type(x) in (int,float) and math.isfinite(x) for x in box)
            and 0<=box[0]<box[2]<=w and 0<=box[1]<box[3]<=h and all(float(x).is_integer() for x in box))
def overlap(a,b):return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])
def contains(a,b):return a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3]

def validate(model,bundle):
    errors=[];warnings=['校验只检查结构、来源引文与坐标；截图内容、动作、脱敏覆盖和完成标志需Agent及人工复核。']
    def fail(message):errors.append(message)
    def string(value,limit=6000):return isinstance(value,str) and 0<len(value.strip())<=limit and not any(ord(c)<32 and c not in '\n\t' for c in value)
    if not isinstance(bundle,dict) or not isinstance(bundle.get('images'),list) or not 1<=len(bundle['images'])<=MAX_IMAGES:
        return {'errors':['来源索引images无效'],'warnings':warnings}
    images={};total=0
    for row in bundle['images']:
        if not isinstance(row,dict) or not string(row.get('id')) or row['id'] in images or row.get('status') not in ('ok','error'):
            fail('图片来源记录无效或ID重复');continue
        images[row['id']]=row
        if row['status']=='ok':
            w,h=row.get('width'),row.get('height')
            if type(w)!=int or type(h)!=int or min(w,h)<1 or w*h>MAX_PIXELS:fail('图片尺寸超限或无效');continue
            total+=w*h
            if not string(row.get('path')) or not isinstance(row.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',row['sha256']):fail('图片路径或摘要缺失')
        else:warnings.append(row['id']+'：资料未读取')
    if total>MAX_TOTAL_PIXELS:fail('累计像素超过限制')
    notes={}
    if not isinstance(bundle.get('notes'),list):fail('来源notes必须为列表')
    else:
        for n in bundle['notes']:
            if not isinstance(n,dict) or not string(n.get('id')) or not string(n.get('text'),100000) or n['id'] in notes:fail('说明来源无效')
            else:notes[n['id']]=n['text']
    if errors:return {'errors':errors,'warnings':warnings}
    if not isinstance(model,dict):return {'errors':['步骤模型必须是对象'],'warnings':warnings}
    if model.get('schema_version')!='1.0':fail('schema_version需为1.0')
    for key in ('title','audience','purpose','software_version'):
        if not string(model.get(key),500):fail(key+'必须为非空文本且不超过500字符')
    for key in ('prerequisites','open_questions'):
        if not isinstance(model.get(key),list) or len(model[key])>100 or any(not string(x) for x in model[key]):fail(key+'必须为文本列表')
    if model.get('order_basis') not in ('user','filename','inferred','unknown'):fail('order_basis无效')
    elif model['order_basis']!='user':warnings.append('截图顺序尚需核对，文件名与推断顺序不等于实际流程')
    privacy=model.get('privacy')
    if not isinstance(privacy,dict):fail('privacy必须为对象');privacy={}
    valid_redactions={}
    for iid,review in privacy.items():
        row=images.get(iid)
        if not row or row['status']!='ok' or not isinstance(review,dict):fail('privacy来源无效');continue
        rects=review.get('redactions')
        if not isinstance(rects,list) or len(rects)>50 or any(not valid_box(b,row['width'],row['height']) for b in rects):fail(iid+'脱敏坐标无效')
        else:valid_redactions[iid]=rects
    steps=model.get('steps')
    if not isinstance(steps,list) or not 1<=len(steps)<=60:return {'errors':errors+['steps需1至60条记录'],'warnings':warnings}
    ids=set()
    for i,step in enumerate(steps,1):
        prefix='步骤'+str(i)+'：'
        if not isinstance(step,dict):fail(prefix+'必须为对象');continue
        if 'image_id' not in step:fail(prefix+'必须显式提供image_id，缺图填null')
        sid=step.get('step_id')
        if not isinstance(sid,str) or not re.fullmatch(r'T[1-9]\d*',sid) or sid in ids:fail(prefix+'ID无效或重复')
        else:ids.add(sid)
        for key in ('title','observation','target','action','expected_result'):
            if not string(step.get(key)):fail(prefix+key+'需非空文本')
        status=step.get('evidence_status');result=step.get('result_basis')
        if status not in ('screenshot','user_note','inferred','missing'):fail(prefix+'evidence_status无效')
        if result not in ('screenshot','user_note','inferred','unknown'):fail(prefix+'result_basis无效')
        refs=step.get('source_notes');good_refs=0
        if not isinstance(refs,list) or len(refs)>50:fail(prefix+'source_notes无效')
        else:
            for ref in refs:
                if not isinstance(ref,dict) or ref.get('note_id') not in notes or not string(ref.get('quote')) or ref['quote'] not in notes[ref['note_id']]:fail(prefix+'说明引文无法精确匹配')
                else:good_refs+=1
        if (status=='user_note' or result=='user_note') and not good_refs:fail(prefix+'用户说明依据不能为空')
        if not isinstance(step.get('open_questions'),list) or any(not string(q) for q in step['open_questions']):fail(prefix+'open_questions无效')
        annotations=step.get('annotations')
        if not isinstance(annotations,list) or len(annotations)>10:fail(prefix+'annotations需0至10项');continue
        iid=step.get('image_id');row=images.get(iid) if isinstance(iid,str) else None
        if iid is None and status=='missing':
            if annotations or step.get('crop') is not None:fail(prefix+'缺图步骤不能标注或裁切')
            if result=='screenshot':fail(prefix+'缺图步骤不能声称截图完成标志')
            warnings.append(prefix+'缺少截图，保留草稿');continue
        if not row or row['status']!='ok':fail(prefix+'截图ID不存在或未读取');continue
        if status=='missing':fail(prefix+'已有截图不能标为missing，请用inferred并说明缺失动作')
        review=privacy.get(iid,{})
        if review.get('reviewed') is not True or iid not in valid_redactions:fail(prefix+'必须完成逐图隐私复核')
        crop=step.get('crop');w,h=row['width'],row['height']
        if crop is not None and not valid_box(crop,w,h):fail(prefix+'crop越界或无效');crop=None
        labels=set()
        for a in annotations:
            if not isinstance(a,dict) or not valid_box(a.get('box'),w,h):fail(prefix+'标注坐标无效');continue
            if not isinstance(a.get('label'),str) or not re.fullmatch(r'[1-9]\d?',a['label']) or a['label'] in labels:fail(prefix+'标注编号需1至99且不重复')
            else:labels.add(a['label'])
            if crop and not contains(crop,a['box']):fail(prefix+'裁切必须包含标注区域')
            if any(overlap(a['box'],b) for b in valid_redactions.get(iid,[])):fail(prefix+'标注区域与脱敏区域重叠')
        if status=='inferred' or result in ('inferred','unknown'):warnings.append(prefix+'存在推断或未知信息，需核对')
    return {'errors':errors,'warnings':warnings}
