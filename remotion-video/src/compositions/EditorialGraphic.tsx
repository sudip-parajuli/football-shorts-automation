import React, {useMemo} from 'react';
import {fitHeadline} from '../shortLayout';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import style from '../editorialStyle.json';

export interface GraphicBrief {
  layout: string;
  label: string;
  headline: string;
  detail: string;
  focus: string;
  actors?: string[];
  status?: string;
}

export const EditorialGraphic: React.FC<{brief: GraphicBrief; durationInFrames: number}> = ({brief, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const portrait = height > width;
  const enter = interpolate(frame, [0, style.transitionFrames], [0, 1], {extrapolateRight:'clamp'});
  const progress = Math.min(1, frame / Math.max(1, durationInFrames));
  const number = brief.layout === 'number' && brief.focus;
  const decision = brief.layout === 'decision';
  const background = number ? style.numberBackground : decision ? style.decisionBackground : style.ink;
  const foreground = number ? style.ink : style.paper;
  const accent = number ? style.numberAccent : style.accent;
  const top = portrait ? 400 : 175;
  const fitted = useMemo(() => {
    const context = typeof document === 'undefined' ? null : document.createElement('canvas').getContext('2d');
    return fitHeadline(brief.detail, portrait?780:1450, portrait?(number?500:600):350,
      (text,size) => {
        if (!context) return text.length*size*.6;
        context.font = `700 ${size}px "${style.font}"`;
        return context.measureText(text).width;
      }, portrait?92:86);
  }, [brief.detail, portrait, number]);
  const fontSize = fitted.fontSize;
  return <AbsoluteFill style={{background, color:foreground, fontFamily:style.font, overflow:'hidden'}}>
    <AbsoluteFill style={{backgroundImage:'linear-gradient(#a9bbc209 1px, transparent 1px), linear-gradient(90deg,#a9bbc209 1px,transparent 1px)', backgroundSize:'80px 80px'}}/>
    <div style={{position:'absolute',left:100,right:100,top,borderTop:`2px solid ${style.muted}55`,paddingTop:28,
      transform:`translateY(${(1-enter)*24}px)`,opacity:1}}>
      <div style={{display:'flex',alignItems:'center',gap:16,color:style.secondary,fontSize:portrait?28:30,letterSpacing:4}}>
        <span style={{width:12,height:12,background:accent,display:'inline-block'}}/>{brief.label}
      </div>
      {number && <div style={{fontSize:portrait?220:190,lineHeight:1.1,color:accent,marginTop:38,border:`2px solid ${foreground}`,borderRadius:14,padding:'8px 22px',display:'inline-block',transform:`scale(${.96+enter*.04})`,transformOrigin:'left'}}>{brief.focus}</div>}
      <div style={{display:'flex',gap:portrait?24:42,marginTop:portrait?48:38,alignItems:'stretch'}}>
        {decision && <div style={{width:8,flexShrink:0,background:accent,transform:`scaleY(${enter})`,transformOrigin:'top'}}/>}
        <div style={{fontWeight:700,fontSize,lineHeight:1.1,maxWidth:portrait?800:1450,overflowWrap:'anywhere'}}>
          {fitted.lines.map((line,index)=><div key={index} style={{opacity:interpolate(frame,[index*2,index*2+4],[.65,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>{line}</div>)}
        </div>
      </div>
      <div style={{marginTop:42,width:portrait?140:240,height:3,background:style.secondary,transform:`scaleX(${enter})`,transformOrigin:'left'}}/>
    </div>
    {decision && (brief.status || (brief.actors?.length || 0)>1) && <div style={{position:'absolute',left:100,right:portrait?150:100,top:portrait?1160:660,
      display:'flex',alignItems:'center',gap:24,opacity:enter}}>
      {(brief.actors || []).map((actor,index)=><React.Fragment key={actor}>
        {index>0 && <div style={{height:2,flex:1,minWidth:40,background:style.secondary,transform:`scaleX(${enter})`,transformOrigin:'left'}}/>}
        <div style={{border:`2px solid ${style.secondary}`,borderRadius:14,padding:'24px 32px',fontSize:portrait?36:42,color:foreground,textTransform:'uppercase'}}>{actor}</div>
      </React.Fragment>)}
      {brief.status && <div style={{marginLeft:'auto',padding:'20px 28px',background:accent,color:style.ink,fontSize:portrait?30:36,textTransform:'uppercase',borderRadius:8}}>{brief.status}</div>}
    </div>}
    <div style={{position:'absolute',left:100,right:portrait?150:100,bottom:portrait?200:35,height:3,background:`${style.muted}33`}}>
      <div style={{height:3,width:`${progress*100}%`,background:accent}}/>
    </div>
    <div style={{position:'absolute',left:100,bottom:portrait?380:150,fontSize:portrait?22:25,letterSpacing:3,color:style.muted}}>FOOTBALL EXPLAINED</div>
  </AbsoluteFill>;
};
