import React from 'react';
import {Img} from 'remotion';

export const GeneratedIllustration:React.FC<{artwork:{svg:string;motion:string};frame:number;accent:string}> = ({artwork,frame,accent}) => {
  const reveal=Math.min(1,frame/20);
  // A generated SVG is an inert image, never executable markup in the page.
  // Python permits only bounded geometry and no links, scripts, text or styles.
  const svg=artwork.svg.replace(/currentColor/g,accent);
  const motion=artwork.motion;
  const y=motion==='float'?Math.sin(frame/28)*5:0;
  const scale=motion==='pulse'?1+Math.sin(frame/32)*.015:1;
  return <div style={{width:'100%',height:'100%',transform:`translateY(${y}px) scale(${scale})`,clipPath:motion==='draw'?`inset(0 ${(1-reveal)*100}% 0 0)`:undefined,opacity:.75+.25*reveal}}>
    <Img src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`} style={{width:'100%',height:'100%',objectFit:'contain'}}/>
  </div>;
};
