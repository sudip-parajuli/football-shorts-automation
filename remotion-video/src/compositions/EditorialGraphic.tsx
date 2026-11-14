import {GeneratedIllustration} from './GeneratedIllustration';
import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {fitHeadline} from '../shortLayout';
import {editorialPages} from '../editorialPages';
import type {CaptionWord} from '../SpokenCaptions';
import {ContextIllustration} from './ContextIllustration';
import style from '../editorialStyle.json';
export interface GraphicBrief {
  layout:string; label:string; headline:string; detail:string; focus:string;
  actors?:string[]; status?:string; motif?:string; artwork?:{svg:string;anchor:string;motion:'draw'|'float'|'pulse'};
}
export const EditorialGraphic:React.FC<{brief:GraphicBrief;durationInFrames:number;timing?:CaptionWord[]}> = ({brief,durationInFrames,timing=[]}) => {
  const frame=useCurrentFrame();
  const {width,height,fps}=useVideoConfig();
  const portrait=height>width;
  const pages=useMemo(()=>editorialPages(brief.detail,durationInFrames/fps,timing),[brief.detail,durationInFrames,fps,timing]);
  const page=pages.filter(value=>value.start<=frame/fps).at(-1) || pages[0];
  const number=brief.layout==='number' && Boolean(brief.focus);
  const decision=brief.layout==='decision';
  const background=number?style.numberBackground:decision?style.decisionBackground:style.ink;
  const foreground=number?style.ink:style.paper;
  const accent=number?style.numberAccent:style.accent;
  const motif=['contract','trophy','calendar','recovery','passing'].includes(brief.motif || '')?brief.motif:undefined;
  const illustrated=Boolean(motif || brief.artwork);
  const textWidth=portrait?830:illustrated?1040:1640;
  const textHeight=portrait?(number?410:570):(number?330:450);
  const measure=(text:string,size:number)=>{
    const context=typeof document==='undefined'?null:document.createElement('canvas').getContext('2d');
    if(!context) return text.length*size*.65;
    context.font=`700 ${size}px "${style.font}"`;
    return context.measureText(text).width;
  };
  const fitted=fitHeadline(page?.text || brief.detail,textWidth,textHeight,measure,portrait?88:86);
  const focus=fitHeadline(brief.focus,textWidth-48,portrait?180:150,measure,portrait?170:145);
  return <AbsoluteFill style={{background,color:foreground,fontFamily:style.font,overflow:'hidden'}}>
    <AbsoluteFill style={{backgroundImage:'linear-gradient(#a9bbc209 1px,transparent 1px),linear-gradient(90deg,#a9bbc209 1px,transparent 1px)',backgroundSize:'80px 80px'}}/>
    <div style={{position:'absolute',left:100,top:portrait?280:140,width:textWidth}}>
      <div style={{borderTop:`2px solid ${style.muted}66`,paddingTop:24,color:accent,fontSize:28,letterSpacing:4}}>{brief.label}</div>
      {number && <div style={{boxSizing:'border-box',marginTop:30,padding:'8px 22px',border:`2px solid ${foreground}`,borderRadius:14,fontSize:focus.fontSize,fontWeight:700,lineHeight:1.12,color:accent}}>
        {focus.lines.map((line,index)=><div key={index}>{line}</div>)}
      </div>}
      <div style={{marginTop:38,fontSize:fitted.fontSize,fontWeight:700,lineHeight:1.12,width:textWidth,borderLeft:decision?`6px solid ${accent}`:undefined,boxSizing:'border-box'}}>
        {fitted.lines.map((line,index)=><div key={index} style={{whiteSpace:'pre-wrap'}}>{line}</div>)}
      </div>
    </div>
    {illustrated && <div style={{position:'absolute',left:portrait?300:1250,top:portrait?1070:280,width:portrait?430:470,height:portrait?320:390}}>
      {brief.artwork?<GeneratedIllustration artwork={brief.artwork} frame={frame} accent={accent}/>:<ContextIllustration motif={motif} frame={frame} accent={accent}/>}
    </div>}
    {decision && brief.status && <div style={{position:'absolute',left:100,top:portrait?1440:810,padding:'12px 22px',border:`2px solid ${accent}`,borderRadius:8,color:accent,fontSize:28,textTransform:'uppercase'}}>{brief.status}</div>}
    <div style={{position:'absolute',left:100,bottom:portrait?380:150,fontSize:24,letterSpacing:3,color:number?style.ink:style.muted}}>FOOTBALL EXPLAINED</div>
    <div style={{position:'absolute',left:100,right:portrait?150:100,bottom:portrait?200:35,height:3,background:`${style.muted}33`}}>
      <div style={{height:3,width:`${Math.min(1,frame/Math.max(1,durationInFrames-1))*100}%`,background:accent}}/>
    </div>
  </AbsoluteFill>;
};
