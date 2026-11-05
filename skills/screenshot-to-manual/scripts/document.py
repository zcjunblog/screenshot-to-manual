"""Three native editable Word layouts sharing the same evidence and image assets."""
from datetime import date
from html import unescape
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from common import text

def templates():
    return json.loads((Path(__file__).resolve().parents[1]/'templates/styles.json').read_text(encoding='utf-8'))

def write_docx(model,bundle,dest,template='office'):
    from export import STATUS,RESULT,ORDER,questions
    from docx import Document
    from docx.shared import Cm,Pt,RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    from PIL import Image
    cfg=templates()[template];doc=Document();sec=doc.sections[0]
    sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.top_margin=Cm(1.8);sec.bottom_margin=Cm(1.7);sec.left_margin=sec.right_margin=Cm(2.1)
    sec.header_distance=sec.footer_distance=Cm(.8)
    cjk=os.environ.get('STM_CJK_FONT') or ('Heiti SC' if sys.platform=='darwin' else 'Microsoft YaHei' if sys.platform=='win32' else 'Noto Sans CJK SC')
    for style in doc.styles:
        for el in list(style.element.iter()):
            if el.tag==qn('w:pBdr'):el.getparent().remove(el)
            if el.tag==qn('w:rFonts'):
                for key in list(el.attrib):
                    if 'theme' in key.lower():del el.attrib[key]
    for name,size in [('Normal',cfg['body_size']),('Title',cfg['title_size']),('Heading 1',cfg['heading_size']),('Heading 2',12)]:
        s=doc.styles[name];s.font.name='Arial';s.font.size=Pt(size);s.font.color.rgb=RGBColor(0,0,0)
        s.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),cjk)
        s.paragraph_format.line_spacing=1.23;s.paragraph_format.space_after=Pt(7)
        s.paragraph_format.widow_control=True
        if name!='Normal':s.paragraph_format.keep_with_next=True
    doc.styles['Title'].paragraph_format.space_after=Pt(16)
    doc.styles['Heading 1'].paragraph_format.space_before=Pt(12)
    def p(value,style=None,small=False,keep=False,bold=False):
        x=doc.add_paragraph(text(value),style=style);x.paragraph_format.keep_with_next=keep
        if small:
            x.paragraph_format.space_after=Pt(5)
            for run in x.runs:run.font.size=Pt(9);run.font.color.rgb=RGBColor(92,103,120)
        if bold:
            for run in x.runs:run.bold=True
        return x
    def labelled(label,value,small=False,keep=False):
        para=p('',small=small,keep=keep);run=para.add_run(label+'  ');run.bold=True
        para.add_run(text(value))
        if small:
            for run in para.runs:run.font.size=Pt(9);run.font.color.rgb=RGBColor(92,103,120)
        return para
    def table(headers,rows,widths):
        t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
        for column,width in zip(t.columns,widths):column.width=Cm(width)
        pr=t._tbl.tblPr;b=OxmlElement('w:tblBorders')
        for edge in ('top','left','bottom','right','insideH','insideV'):
            el=OxmlElement('w:'+edge)
            for k,v in [('val','single'),('sz','4'),('color','D9D9D9')]:el.set(qn('w:'+k),v)
            b.append(el)
        pr.append(b);pad=OxmlElement('w:tblCellMar')
        for edge in ('top','bottom','left','right'):
            e=OxmlElement('w:'+edge);e.set(qn('w:w'),'115');e.set(qn('w:type'),'dxa');pad.append(e)
        pr.append(pad)
        for i,values in enumerate([headers]+rows):
            row=t.rows[0] if i==0 else t.add_row();row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            if i==0:row._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
            for j,value in enumerate(values):
                cell=row.cells[j];cell.width=Cm(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),cfg['accent'] if i==0 else 'FFFFFF' if i%2 else cfg['pale']);cell._tc.get_or_add_tcPr().append(shade)
                para=cell.paragraphs[0];para.paragraph_format.space_after=Pt(0);para.paragraph_format.line_spacing=1.15
                if j==0 and len(headers)>2:para.alignment=WD_ALIGN_PARAGRAPH.CENTER
                r=para.add_run(text(value));r.font.size=Pt(10);r.bold=i==0
                r.font.color.rgb=RGBColor.from_string('FFFFFF' if i==0 else '172B4D')
        p('')
        return t
    def info_table():
        table(['文档信息','当前内容'],[['目标读者',model['audience']],['软件版本',model['software_version']],['生成日期',date.today().isoformat()],['文档状态','操作手册草稿 · '+str(len(model['steps']))+'个步骤']],[3.1,13.7])
    def overview():
        p('流程一览','Heading 1',keep=True)
        table(['步骤','操作主题','截图依据'],[[f'{i:02d}',s['title'],s['image_id'] or '待补图'] for i,s in enumerate(model['steps'],1)],[1.5,12.2,3.1])
    def prerequisites():
        p('使用前准备','Heading 1',keep=True)
        for line in model['prerequisites'] or ['资料未提供明确前置条件，请核对账号、权限和运行环境。']:p(line)
        p('步骤顺序：'+ORDER[model['order_basis']],small=True)
    def picture(i,s,height):
        if s['image_id']:
            path=dest/f'assets/step-{i:03d}.png'
            with Image.open(path) as image:w,h=image.size
            width=min(16.8,height*w/h)
            para=doc.add_paragraph();para.alignment=WD_ALIGN_PARAGRAPH.CENTER
            para.add_run().add_picture(str(path),width=Cm(width),height=Cm(width*h/w));para.paragraph_format.keep_with_next=True
            caption=f'图{i:02d}  来源 '+s['image_id']
            if s['annotations']:caption+='  ·  同色编号与边框对应'
            x=p(caption,small=True);x.alignment=WD_ALIGN_PARAGRAPH.CENTER
        else:p('缺少截图：请补充该步骤界面，当前不能据此确认操作结果。')
    def step_heading(i,s):
        head=p('','Heading 1',keep=True)
        head.paragraph_format.space_before=Pt(0)
        head.paragraph_format.space_after=Pt(12)
        number=head.add_run(f'{i:02d}  ')
        number.font.size=Pt(30 if template=='training' else 26)
        number.font.color.rgb=RGBColor.from_string(cfg['accent'])
        title=head.add_run(s['title']);title.font.size=Pt(cfg['heading_size'])
        return head
    def action_block(label,value):
        label_p=p(label,small=True,keep=True)
        label_p.paragraph_format.space_before=Pt(6)
        p(value,keep=True)
    intro_units=sum(len(text(model[key])) for key in ('title','purpose','audience','software_version'))+sum(len(x) for x in model['prerequisites'])
    training_intro_page=template=='training' and (intro_units>160 or len(model['prerequisites'])>3)
    # Different document archetypes, not only different colors.
    if template=='delivery':
        p('使用与交付手册',small=True)
        title=p(model['title'],'Title');title.paragraph_format.space_before=Pt(88)
        units=sum(1 if unicodedata.east_asian_width(char) in ('W','F') else .55 for char in model['title'])
        fitted_size=max(20,min(cfg['title_size'],460/max(units,1)))
        for run in title.runs:run.font.size=Pt(fitted_size)
        p(model['purpose']);p('操作手册草稿',bold=True)
        stats=p('');stats.paragraph_format.space_before=Pt(26);stats.paragraph_format.space_after=Pt(28)
        count=stats.add_run(f'{len(model["steps"]):02d}');count.font.size=Pt(54);count.font.color.rgb=RGBColor.from_string(cfg['accent'])
        stats.add_run('  个操作步骤').font.size=Pt(12)
        info_table()
        p('供项目交接与使用核对。请先完成必要的步骤与隐私复核，再对外移交。',small=True)
        doc.add_page_break();p('阅读说明','Heading 1',keep=True)
        p('本手册依据提供的截图和说明编制。截图反映可见界面，未验证完整业务流程；不确定信息保留在步骤和待补充清单中。')
        overview();prerequisites()
    elif template=='office':
        p('操作指南  /  操作手册草稿',small=True);p(model['title'],'Title');p(model['purpose'])
        info_table();overview();prerequisites()
    else:
        p('分步学习指南',small=True);p(model['title'],'Title');p(model['purpose'])
        p('操作手册草稿  ·  读者：'+model['audience']+'  ·  软件版本：'+model['software_version'],small=True)
        prerequisites()
    if template!='training':p('本稿依据截图与说明整理，未验证完整业务流程。请核对待补充信息后使用。',small=True)
    for i,s in enumerate(model['steps'],1):
        if (i>1 and template!='office') or (i==1 and (template!='training' or training_intro_page)):doc.add_page_break()
        head=step_heading(i,s)
        head.paragraph_format.space_before=Pt(0 if i>1 or template!='training' else 10)
        if template=='training':
            picture(i,s,8.8 if i==1 else cfg['image_height'])
            action_block('现在这样操作',s['action'])
            action_block('完成后检查',s['expected_result'])
            labelled('操作对象',s['target'],small=True)
            labelled('界面观察',s['observation'],small=True)
        elif template=='delivery':
            labelled('操作对象',s['target'],small=True,keep=True)
            action_block('操作说明',s['action'])
            picture(i,s,cfg['image_height'])
            action_block('完成标志',s['expected_result'])
            labelled('界面观察',s['observation'],small=True)
        else:
            labelled('操作',s['action'],keep=True)
            picture(i,s,cfg['image_height'])
            labelled('检查结果',s['expected_result'])
            labelled('操作对象',s['target'],small=True)
            labelled('当前界面',s['observation'],small=True)
        p('操作依据：'+STATUS[s['evidence_status']]+'；结果依据：'+RESULT[s['result_basis']],small=True)
        for q in s['open_questions']:labelled('待确认',q,small=True)
        if template=='office':
            # Keep one step together when it fits, and let short steps share a page.
            # Very long steps can still flow naturally across pages.
            # Paragraph wrappers are recreated by python-docx, so locate the XML element.
            group=[];inside=False
            for paragraph in doc.paragraphs:
                if paragraph._p is head._p:inside=True
                if inside:group.append(paragraph)
            for paragraph in group[:-1]:paragraph.paragraph_format.keep_with_next=True
            if group:group[-1].paragraph_format.space_after=Pt(20)
    p('待补充信息','Heading 1',keep=True)
    for line in questions(model,bundle):p(unescape(re.sub(r'\\([\\`*_{}\[\]()#+.!|~-])',r'\1',line)))
    header=sec.header.paragraphs[0]
    header.add_run(cfg['subtitle']+'  /  '+model['title']);header.style=doc.styles['Normal']
    for r in header.runs:r.font.size=Pt(8);r.font.color.rgb=RGBColor(0,0,0)
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run('操作手册草稿  ·  ')
    for index,fieldname in enumerate(('PAGE','NUMPAGES')):
        if index:footer.add_run(' / ')
        field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),fieldname);footer._p.append(field)
    for r in footer.runs:r.font.size=Pt(9)
    doc.core_properties.author='';doc.core_properties.last_modified_by='';doc.core_properties.title=model['title']
    doc.save(dest/'操作手册.docx')
