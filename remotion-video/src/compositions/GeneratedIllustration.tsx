import React from 'react';
import {Img} from 'remotion';
import {Artwork,ArtLayer,layerStartFrames} from '../artwork';
import type {CaptionWord} from '../SpokenCaptions';

const Layer:React.FC<{artwork:ArtLayer;frame:number;accent:string;duration:number}> = ({artwork,frame,accent,duration}) => {
  if(frame<0) return null;
  const reveal=Math.min(1,frame/Math.max(2,Math.min(16,duration/3)));
  const svg=artwork.svg.replace(/currentColor/g,accent);
  const y=artwork.motion==='float'?Math.sin(frame/28)*4:0;
  const scale=artwork.motion==='pulse'?1+Math.sin(frame/32)*.012:1;
  return <div style={{position:'absolute',inset:0,transform:`translateY(${y}px) scale(${scale})`,
    clipPath:artwork.motion==='draw'?`inset(0 ${(1-reveal)*100}% 0 0)`:undefined,opacity:.7+.3*reveal}}>
    <Img src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`} style={{width:'100%',height:'100%',objectFit:'contain'}}/>
  </div>;
};

export const GeneratedIllustration:React.FC<{artwork:Artwork;frame:number;accent:string;timing?:CaptionWord[];durationInFrames?:number;fps?:number}> = ({artwork,frame,accent,timing=[],durationInFrames=120,fps=24}) => {
  const layers=artwork.layers?.length?artwork.layers:[artwork];
  const starts=layerStartFrames(layers,timing,fps,durationInFrames);
  return <div style={{position:'relative',width:'100%',height:'100%'}}>
    {layers.map((layer,index)=><Layer key={index} artwork={layer} frame={frame-starts[index]} accent={accent} duration={durationInFrames-starts[index]}/>)}
  </div>;
};
