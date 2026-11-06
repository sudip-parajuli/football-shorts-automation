import React from 'react';
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
  })).optional(),
});

export const MainSchema = z.object({
  title_card: z.string(),
  profile_image: z.string(),
  background_music: z.string().optional(),
  club_logos: z.array(z.string()).optional(),
  segments: z.array(SegmentSchema),
});

type MainProps = z.infer<typeof MainSchema>;

// Captions follow spoken words; diagrams/headlines never display a paragraph.
const SpokenCaptions: React.FC<{timing:z.infer<typeof WordTimingSchema>[]}> = ({timing}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  let groups: typeof timing[] = [];
  let page: typeof timing = [];
  for (const word of timing) {
    const nextLength = [...page,word].map(item=>stripCaptionMarkup(item.word)).join(' ').length;
    if (page.length && (page.length>=4 || nextLength>24)) { groups.push(page); page=[]; }
    page.push(word);
    if (/[.!?;:]$/.test(word.word)) {groups.push(page);page=[];}
  }
  if(page.length) groups.push(page);
  const seconds=frame/fps;
  const active=groups.find((group,index)=>seconds>=group[0].start && seconds<(groups[index+1]?.[0].start ?? group[group.length-1].start+group[group.length-1].duration+.12));
  if(!active) return null;
  return <div style={{position:'absolute',left:100,width:780,bottom:275,zIndex:50,textAlign:'center',
    fontFamily:'Barlow Condensed',fontSize:64,fontWeight:700,lineHeight:1.12,color:'#fffbed',
    textShadow:'0 3px 8px #000',overflowWrap:'anywhere'}}>
    {active.map((word,index)=><span key={index} style={{color:seconds>=word.start && seconds<word.start+word.duration ? '#f7c64d':'#fffbed',
      background:'#031017c9',padding:'3px 8px',boxDecorationBreak:'clone'}}>{stripCaptionMarkup(word.word)} </span>)}
  </div>;
};

export const Main: React.FC<MainProps> = (props) => {
  const {fps} = useVideoConfig();
  let cumulative=0;
  return <AbsoluteFill style={{background:'#0b2027'}}>
    {props.background_music && <Audio src={staticFile(props.background_music)} volume={.04} loop/>}
    <div style={{position:'absolute',left:100,top:80,zIndex:60,fontFamily:'Barlow Condensed',fontSize:28,letterSpacing:5,color:'#d4e2d6'}}>FOOTYBITEZ</div>
    <div style={{position:'absolute',right:160,top:65,zIndex:60,display:'flex',gap:18}}>
      {props.club_logos?.map(src=><Img key={src} src={staticFile(src)} style={{width:80,height:80,objectFit:'contain',filter:'drop-shadow(0 3px 8px #0008)'}}/>)}
    </div>
    {props.segments.map((segment,index)=>{
      const frames=Math.max(1,Math.round(segment.duration*fps));
      const from=cumulative;cumulative+=frames;
      const fallback: ShortVisual = {from_frame:0,duration_frames:frames,headline:stripCaptionMarkup(segment.text).split(/\s+/).slice(0,5).join(' '),
        narration_snippet:segment.text,theme:'',src:segment.media?.find(src=>!/(editorial_|placeholder)/.test(src)) || '',kind:'unavailable'};
      if(fallback.src) fallback.kind='media';
      const scenes=segment.visual_scenes?.length ? segment.visual_scenes : [fallback];
      return <Sequence key={index} from={from} durationInFrames={frames}>
        {segment.audio_path && <Audio src={staticFile(segment.audio_path)}/>}
        {scenes.map((scene,sceneIndex)=><Sequence key={sceneIndex} from={scene.from_frame} durationInFrames={scene.duration_frames}>
          <ShortsScene scene={scene} hook={segment.type==='hook'} hookText={segment.text}/>
        </Sequence>)}
        {segment.type!=='hook' && <SpokenCaptions timing={segment.timing}/>}
      </Sequence>;
    })}
  </AbsoluteFill>;
};
