import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from footybitez.content.staging import photo_treatment,is_comparison
from footybitez.content.svg_director import validated_artwork
from footybitez.media.text_fit import fit_text_box
from footybitez.video.short_timeline import plan_visual_beats
from footybitez.video.visual_review import scene_spans,review_render
from test_svg_director import STADIUM


class EditingToolsTests(unittest.TestCase):
    def test_raster_card_preserves_every_character_inside_measured_bounds(self):
        text="Rooney contemplated suicide at his lowest point before seeking support and rebuilding his life. "*4+'X'*80
        layout=fit_text_box(text,840,900,['remotion-video/public/assets/fonts/BarlowCondensed-Bold.ttf'])
        self.assertEqual(''.join(layout['lines']).replace(' ',''),text.replace(' ',''))
        draw=ImageDraw.Draw(Image.new('RGB',(1,1)))
        self.assertTrue(all(draw.textlength(line,font=layout['font'])<=840 for line in layout['lines']))
        self.assertLessEqual(layout['height'],900)

    def test_match_card_text_is_fitted_or_rejected_before_it_is_rasterized(self):
        from footybitez.media.card_generator import _draw_text,_get_font
        draw=Mock()
        draw._image.size=(1080,1920)
        # The real Pillow geometry measures the supplied font, not guessed character counts.
        actual=ImageDraw.Draw(Image.new('RGB',(1080,1920)))
        draw.textbbox.side_effect=actual.textbbox
        text='A very long club name competing in an important final'
        _draw_text(draw,(540,400),text,font=_get_font(90),fill='white',anchor='mm')
        args,kwargs=draw.text.call_args
        bounds=actual.textbbox(args[0],args[1],font=kwargs['font'],anchor='mm')
        self.assertGreaterEqual(bounds[0],16)
        self.assertLessEqual(bounds[2],1064)
        with self.assertRaises(ValueError):
            _draw_text(draw,(-100,400),'Impossible position',font=_get_font(40),fill='white')

    def test_legacy_hash_cards_are_not_mistaken_for_real_photos_or_match_data(self):
        for name in ['card_-123456789.jpg','card_abcdef0123456789.jpg']:
            scenes,_,_=plan_visual_beats('The player reflected on a difficult period in his life.',[],6,[name])
            self.assertTrue(all(scene['kind']=='editorial' for scene in scenes))
        scenes,_,_=plan_visual_beats('The home team won the match after a late goal.',[],6,['card_score.jpg'])
        self.assertTrue(all(scene['kind']=='media' for scene in scenes))

    def test_photo_treatments_are_contextual(self):
        self.assertEqual(photo_treatment('His early years shaped a long career.'),'archive')
        self.assertEqual(photo_treatment('The match starts tonight.'),'photo')
        self.assertTrue(is_comparison('Messi versus Ronaldo in the final.'))
        self.assertFalse(is_comparison('Messi scored the winning goal.'))

    @patch('footybitez.media.real_assets.wikipedia_primary_photo')
    def test_comparison_pair_requires_two_explicitly_narrated_subjects(self,photo):
        from footybitez.media.asset_orchestrator import fetch_asset
        scene={'visual_type':'image','narration_snippet':'Lionel Messi versus Cristiano Ronaldo.',
               'named_entities':[{'name':'Lionel Messi'},{'name':'Cristiano Ronaldo'},{'name':'Neymar'}]}
        photo.side_effect=['messi.jpg','ronaldo.jpg']
        result=fetch_asset(scene,'qa',Mock(),topic='Comparison')
        self.assertEqual(result['secondary_asset_path'],'ronaldo.jpg')
        self.assertEqual(result['photo_treatment'],'comparison')
        self.assertEqual(photo.call_count,2)

    def test_svg_layers_must_each_match_the_narration(self):
        item={'svg':STADIUM,'anchor':'stadium expanded','motion':'draw','layers':[
            {'svg':STADIUM,'anchor':'stadium expanded','motion':'float'},
            {'svg':STADIUM,'anchor':'seating capacity','motion':'draw'}]}
        artwork=validated_artwork(item,'The stadium expanded its seating capacity.')
        self.assertEqual(len(artwork['layers']),2)
        item['layers'][1]['anchor']='invented trophy'
        self.assertNotIn('layers',validated_artwork(item,'The stadium expanded its seating capacity.'))

    def test_contact_sheet_samples_scene_edges_without_changing_the_timeline(self):
        from test_video_preflight_integration import VideoPreflightTests
        props={'segments':[{'duration':1,'visual_scenes':[{'from_frame':0,'duration_frames':24}]}]}
        self.assertEqual(scene_spans(props),[(0,1)])
        with tempfile.TemporaryDirectory() as directory:
            video=VideoPreflightTests().make_video(directory,'sine=frequency=440:duration=1')
            report=review_render(video,Path(directory)/'review',props)
            self.assertEqual(report['sampled_frames'],3)
            self.assertTrue((Path(directory)/'review/contact-sheet.jpg').is_file())
            self.assertFalse(any(sample['possibly_blank'] for sample in report['samples']))
