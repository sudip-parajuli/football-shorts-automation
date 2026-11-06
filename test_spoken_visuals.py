import unittest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch
from footybitez.video.short_timeline import plan_visual_beats, align_words
from footybitez.media.narration import google_payload, hume_payload, DEFAULT_GOOGLE_VOICE
from footybitez.media.real_assets import exact_entity_match, supported_entities, pexels_short_clip


class SpokenVisualTests(unittest.TestCase):
    def test_scene_changes_follow_real_word_starts_not_equal_slices(self):
        text='One two three four five six seven eight nine ten eleven twelve.'
        starts=[0,.2,.4,.6,.8,1,1.2,1.4,1.6,2,7,8]
        timing=[{'word':word,'start':start,'duration':.2} for word,start in zip(text.split(),starts)]
        scenes, words, source=plan_visual_beats(text,timing,9)
        self.assertEqual(source,'word_marks')
        self.assertEqual(sum(scene['duration_frames'] for scene in scenes),216)
        for scene in scenes[1:]:
            self.assertEqual(scene['from_frame'],round(words[scene['word_start']]['start']*24))
        self.assertTrue(all(len(scene['headline'].split())<=5 for scene in scenes))

    def test_missing_marks_preserve_anchors_and_full_coverage(self):
        timing=[{'word':'one','start':0,'duration':.2},{'word':'five','start':4,'duration':1}]
        words,source=align_words('one two three four five',timing,6)
        self.assertEqual(source,'interpolated')
        self.assertEqual(words[4]['start'],4)
        self.assertEqual(words[-1]['start']+words[-1]['duration'],6)

    def test_no_photos_uses_varied_diagrams_never_paragraph_cards(self):
        text='Football agents negotiate contracts and help players handle business. They represent the player in discussions with a club about a deal.'
        scenes,words,source=plan_visual_beats(text,[],12,offset=1)
        self.assertTrue(all(scene['kind']=='diagram' for scene in scenes))
        self.assertGreater(len({scene['theme'] for scene in scenes}),1)
        self.assertTrue(all(not scene['src'] for scene in scenes))

    def test_real_photos_are_used_in_the_plan(self):
        scenes,_,_=plan_visual_beats('Cristiano Ronaldo played for Manchester United. Old Trafford is the home of the club and its supporters.',[],9,['entity_ronaldo.jpg','wiki_stadium.jpg'])
        self.assertTrue(any(scene['kind']=='media' for scene in scenes))
        self.assertTrue(any(scene['src']=='entity_ronaldo.jpg' for scene in scenes))

    def test_natural_uk_ssml_keeps_all_word_marks(self):
        text='Who runs the deal? VAR changes decisions.'
        payload=google_payload(text)
        self.assertEqual(payload['voice']['name'],DEFAULT_GOOGLE_VOICE)
        self.assertEqual(payload['audioConfig']['pitch'],0)
        root=ET.fromstring(payload['input']['ssml'])
        self.assertEqual(len(root.findall('.//mark')),len(text.split()))
        self.assertEqual(len(root.findall('.//s')),2)
        self.assertEqual(root.find('.//say-as').text,'VAR')

    def test_hume_voice_id_is_a_voice_setting(self):
        utterance=hume_payload('A clear football story.','voice-123')['utterances'][0]
        self.assertEqual(utterance['voice']['id'],'voice-123')
        self.assertNotIn('voice-123',utterance['description'])

    def test_exact_football_identity_only(self):
        self.assertTrue(exact_entity_match('Manchester United',{'title':'Manchester United F.C.','extract':'An English football club.'}))
        self.assertFalse(exact_entity_match('Cristiano Ronaldo',{'title':'Ronaldo (Brazilian footballer)','extract':'A Brazilian footballer.'}))
        self.assertFalse(exact_entity_match('Ajax Amsterdam',{'title':'Ajax Amsterdam','extract':'A fictional hero in Greek mythology.'}))

    def test_only_evidenced_entities_can_supply_portraits(self):
        segment={'text':'Cristiano Ronaldo played at Manchester United.','visual_entities':['Cristiano Ronaldo','Lionel Messi']}
        entities=supported_entities(segment,{'primary_entity':''})
        self.assertEqual(entities,['Cristiano Ronaldo'])

if __name__=='__main__': unittest.main()
