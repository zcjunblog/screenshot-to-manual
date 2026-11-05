"""Portable draft handbooks and a public handoff ZIP; originals stay outside."""
from datetime import datetime,timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from common import text,version,digest,check_source
from images import prepare_image
from validate import validate

STATUS={'screenshot':'截图可见依据，操作效果仍需核对','user_note':'用户说明依据','inferred':'推断步骤，待确认','missing':'缺少截图，待补充'}
RESULT={'screenshot':'截图可见状态','user_note':'用户说明的预期状态','inferred':'推断结果，待确认','unknown':'完成标志未知'}
ORDER={'user':'用户提供的顺序','filename':'文件编号顺序，待核对','inferred':'推断顺序，待核对','unknown':'顺序未知，待核对'}

def md(value):
    s=text(value).replace('\n',' / ').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    return re.sub(r'([\\`*_{}\[\]()#+.!|~-])',r'\\\1',s)

def find_soffice(explicit=None):
    if explicit:
        p=Path(explicit).expanduser()
        if not p.is_file() or not os.access(p,os.X_OK):raise ValueError('指定的LibreOffice程序不存在或不可执行')
        return str(p.resolve())
    for name in ('libreoffice','soffice'):
        path=shutil.which(name)
        if path:return path
    if sys.platform=='darwin':
        p=Path('/Applications/LibreOffice.app/Contents/MacOS/soffice')
        if p.is_file():return str(p)
    return None

def markdown(model,bundle):
    lines=['# '+md(model['title']),'操作手册草稿',md(model['purpose']),
           '**目标读者：** '+md(model['audience']),'**软件版本：** '+md(model['software_version']),
           '**步骤顺序：** '+ORDER[model['order_basis']],
           '本稿依据提供的截图和说明整理，尚未验证完整业务流程。请核对待补充信息后再使用。','## 使用前准备']
    lines.extend(md(x) for x in model['prerequisites'])
    if not model['prerequisites']:lines.append('资料未提供明确前置条件，请核对账号、权限和运行环境。')
    for i,s in enumerate(model['steps'],1):
        lines.extend([f'## {i} '+md(s['title']),'**依据：** '+STATUS[s['evidence_status']],
                      '**操作对象：** '+md(s['target']),'**操作：** '+md(s['action']),
                      '**当前界面：** '+md(s['observation'])])
        if s['image_id']:
            lines.extend([f'![步骤{i}截图](assets/step-{i:03d}.png)',f'图{i} · 来源 '+s['image_id']])
            if s['annotations']:lines.append('重点标注：'+'、'.join(a['label'] for a in s['annotations'])+'；编号与同色边框对应。')
        else:lines.append('缺少截图：此步骤需要补充界面，不能据此确认操作已完成。')
        lines.append('**'+RESULT[s['result_basis']]+'：** '+md(s['expected_result']))
        for q in s['open_questions']:lines.append('待确认：'+md(q))
    lines.extend(['## 待补充信息',*questions(model,bundle)])
    return '\n\n'.join(lines)+'\n'

def questions(model,bundle):
    items=list(model['open_questions'])
    if model['order_basis']!='user':items.append('截图顺序尚未由用户明确，请核对实际操作顺序。')
    for i,s in enumerate(model['steps'],1):
        if s['image_id'] is None:items.append(f'步骤{i}缺少截图。')
        if s['evidence_status']=='inferred':items.append(f'步骤{i}操作为推断，需确认动作。')
        if s['result_basis'] in ('unknown','inferred'):items.append(f'步骤{i}完成标志尚未确认。')
        items.extend(f'步骤{i}：'+q for q in s['open_questions'])
    for row in bundle['images']:
        if row['status']!='ok':items.append(row['id']+'未读取，请补充可读图片。')
        for w in row.get('warnings',[]):items.append(row['id']+'：'+w)
    return [md(x) for x in dict.fromkeys(items)] or ['当前没有单列缺口；仍需实际操作者核对步骤与结果。']

from document import write_docx,templates


def pdf_from_word(work,soffice):
    with tempfile.TemporaryDirectory(prefix='manual-lo-') as td:
        stage=Path(td);converted=stage/'converted';converted.mkdir()
        cmd=[soffice,'-env:UserInstallation='+(stage/'profile').as_uri(),'--headless','--convert-to','pdf','--outdir',str(converted),str((work/'操作手册.docx').resolve())]
        environment=os.environ.copy()
        # macOS portable builds can carry their own fontconfig; derive from the
        # actual executable, never from a developer-machine runtime location.
        config=Path(soffice).resolve().parent.parent/'Resources/fontconfig/fonts.conf'
        if not environment.get('FONTCONFIG_FILE') and config.is_file():
            environment['FONTCONFIG_FILE']=str(config)
        elif not environment.get('FONTCONFIG_FILE') and sys.platform=='darwin':
            # Shell launchers hide the .app path. Supply standard macOS font
            # directories to this conversion only, without changing host settings.
            from xml.sax.saxutils import escape
            config=stage/'fonts.conf'
            directories=['/System/Library/Fonts','/Library/Fonts',str(Path.home()/'Library/Fonts'),
                         '/System/Library/Assets/com_apple_MobileAsset_Font3',
                         '/System/Library/Assets/com_apple_MobileAsset_Font4']
            config.write_text('<?xml version="1.0"?><fontconfig>'+''.join('<dir>'+escape(d)+'</dir>' for d in directories)+
                              '<cachedir>'+escape(str(stage/'font-cache'))+'</cachedir></fontconfig>',encoding='utf-8')
            environment['FONTCONFIG_FILE']=str(config)
        run=subprocess.run(cmd,capture_output=True,text=True,timeout=120,cwd=stage,env=environment)
        pdf=converted/'操作手册.pdf'
        if run.returncode or not pdf.is_file() or pdf.stat().st_size<100 or not pdf.read_bytes().startswith(b'%PDF-'):
            raise ValueError('PDF转换失败：'+(run.stderr or run.stdout)[-500:])
        shutil.copyfile(pdf,work/'操作手册.pdf')


def render(model,bundle,out,word='auto',pdf='auto',soffice=None,template='office'):
    if template not in templates():raise ValueError('未知模板：'+str(template))
    if word not in ('auto','off','required') or pdf not in ('auto','off','required'):raise ValueError('模式应为auto/off/required')
    if word=='off' and pdf=='required':raise ValueError('PDF依赖Word，请启用Word输出')
    report=validate(model,bundle)
    if report['errors']:raise ValueError('校验失败：\n'+'\n'.join(report['errors']))
    used={s['image_id'] for s in model['steps'] if s['image_id']}
    rows={row['id']:row for row in bundle['images']}
    for iid in used:check_source(rows[iid])
    has_word=importlib.util.find_spec('docx') is not None
    converter=find_soffice(soffice) if pdf!='off' else None
    if word=='required' and not has_word:raise ValueError('缺少python-docx，无法生成Word')
    if pdf=='required' and (not has_word or not converter):raise ValueError('PDF需要python-docx与LibreOffice')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    dest=Path(tempfile.mkdtemp(prefix='手册-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-',dir=out))
    work=Path(tempfile.mkdtemp(prefix='.manual-',dir=out))
    state={'word':'disabled','pdf':'disabled'}
    try:
        (work/'assets').mkdir()
        for i,s in enumerate(model['steps'],1):
            if s['image_id']:prepare_image(rows[s['image_id']],model['privacy'][s['image_id']],s,work/f'assets/step-{i:03d}.png')
        (work/'操作手册.md').write_text(markdown(model,bundle),encoding='utf-8')
        (work/'待补充信息.md').write_text('# 待补充信息\n\n'+'\n\n'.join(questions(model,bundle))+'\n',encoding='utf-8')
        if word!='off':
            state['word']='missing_dependency'
            if has_word:
                try:write_docx(model,bundle,work,template);state['word']='generated'
                except Exception as exc:
                    if word=='required' or pdf=='required':raise
                    (work/'操作手册.docx').unlink(missing_ok=True);state['word']='failed';report['warnings'].append('Word导出失败：'+str(exc))
        if pdf!='off':
            state['pdf']='missing_dependency'
            if converter and state['word']=='generated':
                try:pdf_from_word(work,converter);state['pdf']='generated'
                except Exception as exc:
                    if pdf=='required':raise
                    (work/'操作手册.pdf').unlink(missing_ok=True);state['pdf']='failed';report['warnings'].append('PDF导出失败：'+str(exc))
        for kind,value in state.items():
            if value in ('missing_dependency','disabled'):report['warnings'].append(kind+'未生成：'+value)
        public=[work/name for name in ('操作手册.md','待补充信息.md','操作手册.docx','操作手册.pdf') if (work/name).is_file()]
        public += [work/f'assets/step-{i:03d}.png' for i,s in enumerate(model['steps'],1) if s['image_id']]
        with zipfile.ZipFile(work/'操作手册-移交包.zip','w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(public):z.write(p,p.relative_to(work).as_posix())
        internal=work/'工作资料';internal.mkdir()
        for name,data in [('步骤模型.json',model),('来源索引.json',bundle),('校验报告.json',report)]:
            (internal/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        result={'skill_version':version(),'created_at':datetime.now(timezone.utc).isoformat(),'status':'draft','template':template,**state,
                'warnings':report['warnings'],'files':[{'path':p.relative_to(work).as_posix(),'sha256':digest(p)} for p in sorted(public+[work/'操作手册-移交包.zip',*internal.glob('*.json')])]}
        (work/'交付清单.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        deliver=[*public,work/'操作手册-移交包.zip',work/'交付清单.json',*internal.glob('*.json')]
        for p in deliver:
            target=dest/p.relative_to(work);target.parent.mkdir(parents=True,exist_ok=True);p.replace(target)
        return {**result,'directory':str(dest.resolve())}
    except Exception:
        shutil.rmtree(dest);raise
    finally:shutil.rmtree(work)
