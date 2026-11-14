import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from footybitez.content.edit_direction import graphic_brief
from footybitez.content.svg_director import SvgDirector,validate_svg

STADIUM='<svg viewBox="0 0 400 300"><g stroke="currentColor" fill="none" stroke-width="6"><ellipse cx="200" cy="150" rx="170" ry="110"/><ellipse cx="200" cy="150" rx="130" ry="75"/><rect x="120" y="110" width="160" height="80"/><path d="M200 110 V190 M40 130 V60 H90 M360 130 V60 H310"/></g></svg>'

def scene(text):
    return {'kind':'editorial','graphic':graphic_brief(text)}


class SvgDirectorTests(unittest.TestCase):
    def test_accepts_geometry_for_a_concept_outside_the_presets(self):
        self.assertIn('<ellipse',validate_svg(STADIUM))
        self.assertIsNone(validate_svg(STADIUM.replace('0 0 400 300','0 0 400 9000')))

    def test_rejects_active_external_or_unbounded_svg(self):
        for body in ['<script>alert(1)</script>','<foreignObject/>','<image href="https://example.com/x"/>',
                     '<path onclick="evil()" d="M0 0"/>','<g style="color:red"/>','<text>Invented score</text>',
                     '<path d="M0 0" stroke="url(#x)"/>','<circle r="999999"/>','<use href="#x"/>']:
            self.assertIsNone(validate_svg(f'<svg viewBox="0 0 400 300">{body}</svg>'),body)
        self.assertIsNone(validate_svg('<svg viewBox="0 0 400 300"/>'))
        self.assertIsNone(validate_svg('<!DOCTYPE svg [<!ENTITY x "bad">]><svg/>'))
        self.assertIsNone(validate_svg('<svg viewBox="0 0 400 300">'+'<path d="M0 0"/>'*81+'</svg>'))

    @patch.dict('os.environ',{'SVG_MAX_REQUESTS':'6','ENABLE_GENERATED_SVG':'true'})
    def test_new_subject_is_attached_and_reused_without_another_request(self):
        item=scene('The stadium expanded its seating capacity.')
        request=Mock(return_value={'illustrations':[{'index':0,'anchor':'stadium expanded','svg':STADIUM,'motion':'float'}]})
        with tempfile.TemporaryDirectory() as directory:
            director=SvgDirector(directory,request)
            report=director.enrich([item])
            self.assertEqual(report['generated'],1)
            self.assertEqual(item['graphic']['motif'],'')
            self.assertEqual(item['graphic']['artwork']['motion'],'float')
            repeat=scene('The stadium expanded its seating capacity.')
            self.assertEqual(director.enrich([repeat])['cached'],1)
            request.assert_called_once()

    def test_unrelated_anchor_and_invalid_geometry_leave_existing_visual_intact(self):
        item=scene('The stadium expanded its seating capacity.')
        request=Mock(return_value={'illustrations':[{'index':0,'anchor':'player transfer','svg':STADIUM}]})
        with tempfile.TemporaryDirectory() as directory:
            report=SvgDirector(directory,request).enrich([item])
        self.assertEqual(report['rejected'],1)
        self.assertNotIn('artwork',item['graphic'])

    def test_provider_outage_does_not_fail_narration_or_render_plan(self):
        item=scene('The stadium expanded its seating capacity.')
        request=Mock(side_effect=RuntimeError('offline'))
        with tempfile.TemporaryDirectory() as directory:
            report=SvgDirector(directory,request).enrich([item])
        self.assertEqual(report['generated'],0)
        self.assertNotIn('artwork',item['graphic'])

    def test_cache_is_revalidated_before_use(self):
        request=Mock(return_value={'illustrations':[{'index':0,'anchor':'stadium expanded','svg':STADIUM,'motion':'draw'}]})
        with tempfile.TemporaryDirectory() as directory:
            director=SvgDirector(directory,request)
            director.enrich([scene('The stadium expanded its seating capacity.')])
            cached=next(Path(directory).glob('*.json'))
            record=json.loads(cached.read_text())
            record['svg']='<svg viewBox="0 0 400 300"><script/></svg>'
            cached.write_text(json.dumps(record))
            request.return_value={}
            item=scene('The stadium expanded its seating capacity.')
            self.assertEqual(director.enrich([item])['cached'],0)
            self.assertNotIn('artwork',item['graphic'])

    @patch.dict('os.environ',{'SVG_MAX_REQUESTS':'1'})
    def test_request_budget_and_repeated_passages(self):
        request=Mock(return_value={})
        with tempfile.TemporaryDirectory() as directory:
            director=SvgDirector(directory,request)
            director.enrich([scene(f'The stadium expanded section {i}.') for i in range(9)])
            director.enrich([scene('A referee reviewed the incident.')])
        request.assert_called_once()
        self.assertEqual(director.calls,1)
