import React from 'react';
import {useCurrentFrame,useVideoConfig} from 'remotion';
import {stripCaptionMarkup} from './displayText';
import style from './editorialStyle.json';
export interface CaptionWord {word:string; start:number; duration:number;}

// Captions follow spoken words; diagrams/headlines never display a paragraph.
export const SpokenCaptions: React.FC<{timing:CaptionWord[]}> = ({timing}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const portrait = height > width;
  let groups: typeof timing[] = [];
  let page: typeof timing = [];
  for (const word of timing) {
    const nextLength = [...page,word].map(item=>stripCaptionMarkup(item.word)).join(' ').length;
    if (page.length && (page.length>=style.captionWords || nextLength>24)) { groups.push(page); page=[]; }
    page.push(word);
    if (/[.!?;:]$/.test(word.word)) {groups.push(page);page=[];}
  }
  if(page.length) groups.push(page);
  const seconds=frame/fps;
  const active=groups.find((group,index)=>seconds>=group[0].start && seconds<(groups[index+1]?.[0].start ?? group[group.length-1].start+group[group.length-1].duration+.12));
  if(!active) return null;
  return <div style={{position:'absolute',left:portrait?100:200,width:portrait?780:1520,bottom:portrait?style.shortCaptionBottom:70,zIndex:50,textAlign:'center',
    fontFamily:style.font,fontSize:portrait?64:54,fontWeight:700,lineHeight:1.12,color:'#fffbed',
    textShadow:'0 3px 8px #000',overflowWrap:'anywhere'}}>
    {active.map((word,index)=><span key={index} style={{color:seconds>=word.start && seconds<word.start+word.duration ? style.accent:'#fffbed',
      background:'#031017c9',padding:'3px 8px',boxDecorationBreak:'clone'}}>{stripCaptionMarkup(word.word)} </span>)}
  </div>;
};

