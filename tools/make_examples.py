"""Manual expected records for actual demo screenshots, not an extraction benchmark."""
import copy,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'skills/screenshot-to-manual/scripts'))
from intake import ingest
from common import save_new
capture=json.loads((ROOT/'examples/capture-record.json').read_text())
notes=['点击“新建申请”打开表单。','在“物品名称”填入“演示笔记本”，将“申请数量”改为2，然后点击“提交申请”。','提交后在列表核对“演示笔记本”、数量2和“待处理”状态。界面提示只证明演示页显示，不能代表采购审批完成。']
for case in ('desktop','mobile','mixed'):
 folder=ROOT/'examples'/case;folder.mkdir(exist_ok=True)
 paths=[ROOT/f'examples/screenshots/{case}/{i}.png' for i in range(1,4)]
 source=ingest(paths,'\n'.join(notes));(folder/'sources.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
 (folder/'notes.txt').write_text('\n'.join(notes)+'\n')
 model={'schema_version':'1.0','title':'办公用品申请操作手册','audience':'首次使用演示台的新员工','purpose':'按照截图完成一条办公用品申请，并核对演示列表显示的结果。所有数据均为虚构测试数据。','software_version':'本地演示程序0.1','order_basis':'user','prerequisites':['已打开虚构演示程序的申请管理页面。'],'privacy':{},'steps':[],'open_questions':[]}
 for i in range(1,4):
  device=('mobile' if i==2 else 'desktop') if case=='mixed' else case
  r=next(x for x in capture if x['case']==device and x['index']==i);b=r['box']
  scale=r.get('pixel_ratio',1)
  box=[math.floor(b['x']*scale),math.floor(b['y']*scale),math.ceil((b['x']+b['width'])*scale),math.ceil((b['y']+b['height'])*scale)]
  rects=[]
  if r['owner']:
   o=r['owner'];rects=[[math.floor((o['x']+2)*scale),math.floor((o['y']+2)*scale),math.ceil((o['x']+o['width']-2)*scale),math.ceil((o['y']+o['height']-2)*scale)]]
  iid=f'I{i:03d}';model['privacy'][iid]={'reviewed':True,'redactions':rects}
  titles=['打开申请表单','填写信息并提交','核对列表结果'];targets=['新建申请按钮','物品名称与申请数量字段和提交申请按钮','提交成功提示与申请列表']
  observations=['当前显示申请列表与新建申请入口。','当前显示物品名称、申请数量和申请人字段；演示申请人区域已按要求遮盖。','当前显示提交成功提示，列表内有演示笔记本，数量2，状态待处理。']
  results=['显示新建申请表单。','提交后返回列表，演示页显示提交成功。','列表显示与用户说明相符；采购审批或后台业务结果不在本次截图验证范围。']
  crop=([250,210,810,735] if i==2 else [250,210,1145,540 if i==3 else 450]) if device=='desktop' else [20,190,370,700 if i==2 else 520 if i==3 else 450]
  crop=[int(x*scale) for x in crop] if crop else None
  step={'step_id':f'T{i}','title':titles[i-1],'image_id':iid,'observation':observations[i-1],'target':targets[i-1],'action':notes[i-1],'expected_result':results[i-1],'result_basis':'user_note','evidence_status':'user_note','source_notes':[{'note_id':f'N{i:03d}','quote':notes[i-1]}],'annotations':[{'box':box,'label':'1'}],'crop':crop,'open_questions':[]}
  model['steps'].append(step)
 (folder/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n')
print('3manual expected examples prepared')
