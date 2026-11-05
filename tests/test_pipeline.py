import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/screenshot-to-manual/scripts'))
from intake import ingest
from validate import validate
from export import render
from images import prepare_image

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.path=self.root/'界面.png'
        Image.new('RGB',(600,400),(230,100,70)).save(self.path)
        self.bundle=ingest([self.path], '点击新增按钮，看到新增表单。')
        self.model={'schema_version':'1.0','title':'新增记录操作手册','audience':'新员工','purpose':'建立记录','software_version':'未知',
          'order_basis':'user','prerequisites':[], 'privacy':{'I001':{'reviewed':True,'redactions':[[20,20,90,60]]}},
          'steps':[{'step_id':'T1','title':'打开新增表单','image_id':'I001','observation':'可见新增按钮。','target':'新增按钮',
          'action':'点击新增按钮。','expected_result':'看到新增表单。','result_basis':'user_note','evidence_status':'user_note',
          'source_notes':[{'note_id':'N001','quote':'点击新增按钮，看到新增表单。'}],
          'annotations':[{'box':[110,100,230,140],'label':'1'}],'crop':None,'open_questions':[]}],
          'open_questions':[]}
    def tearDown(self):self.tmp.cleanup()
    def check_error(self,model=None,bundle=None):self.assertTrue(validate(model or self.model,bundle or self.bundle)['errors'])
    def test_ingest_hash_and_notes(self):
        row=self.bundle['images'][0];self.assertEqual(row['width'],600)
        self.assertEqual(row['sha256'],hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(self.bundle['notes'][0]['id'],'N001')
    def test_partial_failure_and_duplicate(self):
        b=ingest([self.path,self.path,self.root/'absent.png'])
        self.assertEqual([x['status'] for x in b['images']],['ok','ok','error'])
        self.assertEqual(b['images'][1]['duplicate_of'],'I001')
    def test_exif_orientation(self):
        p=self.root/'rotated.jpg';exif=Image.Exif();exif[274]=6
        Image.new('RGB',(60,100)).save(p,exif=exif)
        b=ingest([p]);self.assertEqual((b['images'][0]['width'],b['images'][0]['height']),(100,60))
    def test_bad_format(self):
        p=self.root/'fake.png';p.write_text('not image');self.assertEqual(ingest([p])['images'][0]['status'],'error')
    def test_batch_limit(self):
        with self.assertRaises(ValueError):ingest([self.path]*21)
    def test_valid(self):self.assertEqual(validate(self.model,self.bundle)['errors'],[])
    def test_false_note(self):
        self.model['steps'][0]['source_notes'][0]['quote']='账号已开通';self.check_error()
    def test_unknown_image(self):self.model['steps'][0]['image_id']='I999';self.check_error()
    def test_invalid_box(self):
        for box in ([-1,0,1,10],[0,0,601,5],[20,10,10,20],[True,0,20,20],[0,0,float('nan'),3]):
            self.model['steps'][0]['annotations'][0]['box']=box;self.check_error()
    def test_crop_must_contain_annotation(self):
        self.model['steps'][0]['crop']=[0,0,100,100];self.check_error()
    def test_redaction_review_required(self):self.model['privacy']['I001']['reviewed']=False;self.check_error()
    def test_annotation_cannot_expose_redaction(self):
        self.model['steps'][0]['annotations'][0]['box']=[25,25,70,50];self.check_error()
    def test_invalid_types(self):
        for field,value in [('steps','x'),('privacy',[]),('title',None),('prerequisites','x')]:
            m=copy.deepcopy(self.model);m[field]=value;self.check_error(m)
    def test_unique_ids(self):self.model['steps']*=2;self.check_error()
    def test_empty_steps(self):self.model['steps']=[];self.check_error()
    def test_note_action_requires_quote(self):self.model['steps'][0]['source_notes']=[];self.check_error()
    def test_missing_step_is_visible(self):
        step=self.model['steps'][0];step.update(image_id=None,evidence_status='missing',annotations=[],action='操作待补充',expected_result='未知',result_basis='unknown',source_notes=[])
        r=render(self.model,self.bundle,self.root/'out',word='off',pdf='off')
        text=(Path(r['directory'])/'操作手册.md').read_text();self.assertIn('缺少截图',text);self.assertIn('草稿',text)
    def test_changed_input_rejected(self):
        Image.new('RGB',(600,400)).save(self.path)
        with self.assertRaises(ValueError):render(self.model,self.bundle,self.root/'out',word='off',pdf='off')
    def test_redaction_pixels_and_metadata_removed(self):
        out=self.root/'derived.png';prepare_image(self.bundle['images'][0],self.model['privacy']['I001'],self.model['steps'][0],out)
        with Image.open(out) as im:
            self.assertEqual(im.getpixel((30,70)),(30,41,59));self.assertFalse(im.info)
        self.assertEqual(Image.open(self.path).getpixel((30,30)),(230,100,70))
    def test_crop_transforms_annotation(self):
        step=self.model['steps'][0];step['crop']=[100,80,300,200]
        out=self.root/'derived.png';prepare_image(self.bundle['images'][0],self.model['privacy']['I001'],step,out)
        with Image.open(out) as im:
            self.assertEqual(im.size,(200,160));self.assertEqual(im.getpixel((10,60)),(37,99,235))
    def test_export_relative_complete_exclusive(self):
        import zipfile
        before=self.path.read_bytes()
        a=render(self.model,self.bundle,self.root/'out',word='off',pdf='off')
        b=render(self.model,self.bundle,self.root/'out',word='off',pdf='off')
        self.assertNotEqual(a['directory'],b['directory']);self.assertEqual(self.path.read_bytes(),before)
        dest=Path(a['directory']);text=(dest/'操作手册.md').read_text()
        self.assertIn('assets/step-001.png',text);self.assertNotIn(str(self.root),text)
        with zipfile.ZipFile(dest/'操作手册-移交包.zip') as z:
            self.assertIn('assets/step-001.png',z.namelist());self.assertFalse(any('来源' in n or 'json' in n for n in z.namelist()))
            self.assertNotIn(before,[z.read(n) for n in z.namelist()])
    @unittest.skipUnless(importlib.util.find_spec('docx'),'optional python-docx')
    def test_word_embeds_only_derived_png(self):
        import zipfile
        from docx import Document
        r=render(self.model,self.bundle,self.root/'out',word='required',pdf='off');dest=Path(r['directory'])
        self.assertEqual(r['word'],'generated');self.assertIn('草稿','\n'.join(p.text for p in Document(dest/'操作手册.docx').paragraphs))
        with zipfile.ZipFile(dest/'操作手册.docx') as z:
            pictures=[z.read(n) for n in z.namelist() if n.startswith('word/media/')]
            self.assertEqual(pictures,[(dest/'assets/step-001.png').read_bytes()])
    def test_pdf_missing_reports_limitation(self):
        from unittest.mock import patch
        with patch('export.find_soffice',return_value=None):
            r=render(self.model,self.bundle,self.root/'out',word='auto',pdf='auto')
        self.assertEqual(r['pdf'],'missing_dependency');self.assertFalse((Path(r['directory'])/'操作手册.pdf').exists())
    def test_required_pdf_failure_does_not_publish_partial(self):
        from unittest.mock import patch
        with patch('export.find_soffice',return_value=None):
            with self.assertRaises(ValueError):render(self.model,self.bundle,self.root/'out',pdf='required')
        self.assertFalse(list((self.root/'out').glob('手册-*')))
    def test_order_uncertain_not_verified(self):
        self.model['order_basis']='inferred';r=validate(self.model,self.bundle)
        self.assertFalse(r['errors']);self.assertTrue(any('顺序' in w for w in r['warnings']))

    def test_transparent_hidden_rgb_is_not_exposed(self):
        p=self.root/'transparent.png';Image.new('RGBA',(600,400),(255,0,0,0)).save(p)
        bundle=ingest([p]);step=self.model['steps'][0]
        out=self.root/'transparent-export.png'
        prepare_image(bundle['images'][0],{'redactions':[]},step,out)
        with Image.open(out) as image:self.assertEqual(image.getpixel((300,300)),(255,255,255))

    def test_missing_image_id_key_rejected(self):
        step=self.model['steps'][0];step.update(evidence_status='missing',annotations=[],source_notes=[],result_basis='unknown')
        del step['image_id'];self.check_error()

    def test_source_snapshot_survives_concurrent_replacement(self):
        from unittest.mock import patch
        import images
        original=images.source_bytes
        def read_then_replace(row):
            snapshot=original(row)
            Image.new('RGB',(600,400),(0,255,0)).save(self.path)
            return snapshot
        out=self.root/'snapshot.png'
        with patch('images.source_bytes',side_effect=read_then_replace):
            prepare_image(self.bundle['images'][0],self.model['privacy']['I001'],self.model['steps'][0],out)
        with Image.open(out) as image:self.assertEqual(image.getpixel((300,300)),(230,100,70))

    def test_narrow_crop_keeps_every_number_visible(self):
        step=self.model['steps'][0];step.update(crop=[100,100,164,164],annotations=[{'box':[101+i*20,101,110+i*20,110],'label':str(i+1)} for i in range(3)])
        out=self.root/'narrow.png';prepare_image(self.bundle['images'][0],{'redactions':[]},step,out)
        with Image.open(out) as image:
            self.assertGreaterEqual(image.width,97)
            self.assertNotEqual(image.getpixel((73,20)),(255,255,255))

    def test_numbers_match_distinct_frame_colors(self):
        step=self.model['steps'][0]
        step['annotations']=[{'box':[120+i*100,100,180+i*100,140],'label':str(i+1)} for i in range(3)]
        out=self.root/'colors.png';prepare_image(self.bundle['images'][0],{'redactions':[]},step,out)
        with Image.open(out) as image:
            colors=[]
            for i in range(3):
                color=image.getpixel((120+i*100,140));colors.append(color)
                self.assertEqual(image.getpixel((9+i*32,20)),color)
            self.assertEqual(len(set(colors)),3)

    def test_invalid_source_digest_is_reported(self):
        for value in (None,7,[]):
            bundle=copy.deepcopy(self.bundle);bundle['images'][0]['sha256']=value
            self.check_error(bundle=bundle)

    @unittest.skipUnless(importlib.util.find_spec('docx'),'optional python-docx')
    def test_pdf_converter_failure_reports_only_real_files(self):
        from unittest.mock import patch
        with patch('export.find_soffice',return_value='/fake/soffice'),patch('export.pdf_from_word',side_effect=ValueError('conversion failed')):
            r=render(self.model,self.bundle,self.root/'out',word='auto',pdf='auto')
        self.assertEqual((r['word'],r['pdf']),('generated','failed'))
        self.assertTrue((Path(r['directory'])/'操作手册.docx').exists())
        self.assertFalse((Path(r['directory'])/'操作手册.pdf').exists())
        self.assertTrue(any('conversion failed' in w for w in r['warnings']))

class TemplateTests(unittest.TestCase):
    setUp=PipelineTests.setUp
    tearDown=PipelineTests.tearDown
    @unittest.skipUnless(importlib.util.find_spec('docx'),'optional python-docx')
    def test_template_variants_keep_facts_and_images(self):
        from docx import Document
        structures=[]
        for template in ('office','delivery','training'):
            r=render(self.model,self.bundle,self.root/'templates',word='required',pdf='off',template=template)
            self.assertEqual(r['template'],template)
            doc=Document(Path(r['directory'])/'操作手册.docx')
            text='\n'.join(p.text for p in doc.paragraphs)
            for s in self.model['steps']:
                self.assertIn(s['action'],text);self.assertIn(s['expected_result'],text)
            self.assertEqual(len(doc.inline_shapes),1)
            structures.append((len(doc.tables),text.index(self.model['steps'][0]['action']),text))
        self.assertEqual(len({x[2] for x in structures}),3)
        self.assertGreater(structures[1][0],structures[2][0])

    def test_unknown_template_is_explicit(self):
        with self.assertRaises(ValueError):render(self.model,self.bundle,self.root/'out',template='unknown')
        self.assertFalse((self.root/'out').exists())

    @unittest.skipUnless(importlib.util.find_spec('docx'),'optional python-docx')
    def test_word_question_summary_keeps_literal_symbols(self):
        from docx import Document
        question='请确认 count < 3 && value > 0 以及 field_name'
        self.model['open_questions']=[question]
        for template in ('office','delivery','training'):
            r=render(self.model,self.bundle,self.root/'out',template=template,word='required',pdf='off')
            paragraphs=[p.text for p in Document(Path(r['directory'])/'操作手册.docx').paragraphs]
            self.assertIn(question,paragraphs)

    def test_macos_converter_uses_its_own_fontconfig_without_global_changes(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from export import pdf_from_word
        converter=self.root/'Office.app/Contents/MacOS/soffice';converter.parent.mkdir(parents=True);converter.touch()
        config=converter.parent.parent/'Resources/fontconfig/fonts.conf';config.parent.mkdir(parents=True);config.write_text('fixture')
        work=self.root/'work';work.mkdir();(work/'操作手册.docx').write_bytes(b'fixture')
        def fake_run(cmd,**kwargs):
            self.assertEqual(Path(kwargs['env']['FONTCONFIG_FILE']).resolve(),config.resolve())
            directory=Path(cmd[cmd.index('--outdir')+1]);(directory/'操作手册.pdf').write_bytes(b'%PDF-'+b'0'*120)
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        with patch.dict('os.environ',{},clear=True),patch('export.subprocess.run',side_effect=fake_run):
            pdf_from_word(work,str(converter))
            import os
            self.assertNotIn('FONTCONFIG_FILE',os.environ)

    def test_pdf_conversion_uses_private_directory(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from export import pdf_from_word
        work=self.root/'work';work.mkdir();(work/'操作手册.docx').write_bytes(b'fixture')
        def fake_run(cmd,**kwargs):
            directory=Path(cmd[cmd.index('--outdir')+1]);self.assertNotEqual(directory,work)
            (directory/'操作手册.pdf').write_bytes(b'%PDF-'+b'0'*120)
            (directory/'debug-private.json').write_text('not for handoff')
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        with patch('export.subprocess.run',side_effect=fake_run):pdf_from_word(work,'/fake/soffice')
        self.assertEqual(sorted(p.name for p in work.iterdir()),['操作手册.docx','操作手册.pdf'])

    def test_macos_launcher_font_fallback_stays_private(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from export import pdf_from_word
        work=self.root/'work';work.mkdir();(work/'操作手册.docx').write_bytes(b'fixture')
        configs=[]
        def fake_run(cmd,**kwargs):
            config=Path(kwargs['env']['FONTCONFIG_FILE']);configs.append(config)
            self.assertIn('/System/Library/Fonts',config.read_text())
            self.assertEqual(config.parent,Path(kwargs['cwd']))
            directory=Path(cmd[cmd.index('--outdir')+1]);(directory/'操作手册.pdf').write_bytes(b'%PDF-'+b'0'*120)
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        with patch.dict('os.environ',{},clear=True),patch('export.sys.platform','darwin'),patch('export.subprocess.run',side_effect=fake_run):
            pdf_from_word(work,'/fake/launcher/soffice')
        self.assertFalse(configs[0].exists())

    @unittest.skipUnless(importlib.util.find_spec('docx'),'optional python-docx')
    def test_handoff_excludes_converter_residuals(self):
        from unittest.mock import patch
        import zipfile
        def fake_convert(work,converter):
            (work/'操作手册.pdf').write_bytes(b'%PDF-'+b'0'*120)
            (work/'debug-private.json').write_text('private conversion detail')
        with patch('export.find_soffice',return_value='/fake/soffice'),patch('export.pdf_from_word',side_effect=fake_convert):
            r=render(self.model,self.bundle,self.root/'out',word='required',pdf='required')
        root=Path(r['directory']);self.assertFalse((root/'debug-private.json').exists())
        with zipfile.ZipFile(root/'操作手册-移交包.zip') as z:self.assertNotIn('debug-private.json',z.namelist())

if __name__=='__main__':unittest.main()
