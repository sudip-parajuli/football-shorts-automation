import React from 'react';
import {SpokenCaptions} from './SpokenCaptions';
import { AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { z } from 'zod';
import { stripCaptionMarkup } from './displayText';
import { ShortsScene, ShortVisual } from './compositions/ShortsScene';

export const WordTimingSchema = z.object({
  word: z.string(),
  start: z.number(),
  duration: z.number(),
});

export const SegmentSchema = z.object({
  type: z.string(),
  text: z.string(),
  start: z.number(),
  duration: z.number(),
  media: z.array(z.string()),
  timing: z.array(WordTimingSchema),
  audio_path: z.string().optional(),
  visual_scenes: z.array(z.object({
    from_frame:z.number(), duration_frames:z.number(), headline:z.string(), narration_snippet:z.string(),
    theme:z.string(), src:z.string(), kind:z.string(),
    graphic:z.object({motif:z.string().optional(),layout:z.string(),label:z.string(),headline:z.string(),detail:z.string(),focus:z.string(),actors:z.array(z.string()).optional(),status:z.string().optional()}).nullable().optional(),
  })).optional(),
});

export const MainSchema = z.object({
  title_card: z.string(),
  profile_image: z.string(),
  background_music: z.string().optional(),
  club_logos: z.array(z.string()).optional(),
  edit_sounds: z.record(z.string(),z.string()).optional(),
  sound_cues: z.array(z.object({from_frame:z.number(),sound:z.string()})).optional(),
  segments: z.array(SegmentSchema),
});

type MainProps = z.infer<typeof MainSchema>;

export const Main: React.FC<MainProps> = (props) => {
  const {fps} = useVideoConfig();
  let cumulative=0;
  return <AbsoluteFill style={{background:'#0b2027'}}>
    {props.sound_cues?.map((cue,index)=>props.edit_sounds?.[cue.sound] ? <Sequence key={index} from={cue.from_frame} durationInFrames={6}>
      <Audio src={staticFile(props.edit_sounds[cue.sound])} volume={.25}/>
    </Sequence> : null)}
    {props.background_music && <Audio src={staticFile(props.background_music)} volume={.04} loop/>}
    <div style={{position:'absolute',left:100,top:80,zIndex:60,fontFamily:'Barlow Condensed',fontSize:28,letterSpacing:5,color:'#d4e2d6'}}>FOOTYBITEZ</div>
    <div style={{position:'absolute',right:160,top:65,zIndex:60,display:'flex',gap:18}}>
      {props.club_logos?.map(src=><Img key={src} src={staticFile(src)} style={{width:80,height:80,objectFit:'contain',filter:'drop-shadow(0 3px 8px #0008)'}}/>)}
    </div>
    {props.segments.map((segment,index)=>{
      const frames=Math.max(1,Math.round(segment.duration*fps));
      const from=cumulative;cumulative+=frames;
      const fallback: ShortVisual = {from_frame:0,duration_frames:frames,headline:stripCaptionMarkup(segment.text).split(/\s+/).slice(0,5).join(' '),
        narration_snippet:segment.text,theme:'',src:segment.media?.find(src=>!/(editorial_|placeholder)/.test(src)) || '',kind:'editorial',graphic:{layout:'statement',label:'THE STORY',headline:'',detail:stripCaptionMarkup(segment.text),focus:''}};
      if(fallback.src) fallback.kind='media';
      const scenes=segment.visual_scenes?.length ? segment.visual_scenes : [fallback];
      return <Sequence key={index} from={from} durationInFrames={frames}>
        {segment.audio_path && <Audio src={staticFile(segment.audio_path)}/>}
        {scenes.map((scene,sceneIndex)=><Sequence key={sceneIndex} from={scene.from_frame} durationInFrames={scene.duration_frames}>
          <ShortsScene scene={scene} hook={segment.type==='hook'} hookText={segment.text} timing={segment.timing.filter(word=>word.start>=scene.from_frame/fps && word.start<(scene.from_frame+scene.duration_frames)/fps).map(word=>({...word,start:word.start-scene.from_frame/fps}))}/>
        </Sequence>)}
        {segment.type!=='hook' && <SpokenCaptions timing={segment.timing}/>}
      </Sequence>;
    })}
  </AbsoluteFill>;
};
