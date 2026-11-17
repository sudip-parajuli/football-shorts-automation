import React from 'react';
import {AbsoluteFill,Img,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {fitHeadline} from '../shortLayout';
import style from '../editorialStyle.json';

// Original paper-photo staging. Source photographs stay whole; no fabricated cutout faces.
export const PaperPhotoStage:React.FC<{sources:string[];durationInFrames:number;caption?:string}> = ({sources,durationInFrames,caption=''}) => {
  const frame=useCurrentFrame();
  const {width,height}=useVideoConfig();
  const portrait=height>width;
  const photos=[...new Set(sources.filter(Boolean))].slice(0,2);
  const two=photos.length>1;
  const box={left:portrait?100:140,top:portrait?500:290,width:portrait?820:1640,height:portrait?850:500};
  const measure=(text:string,size:number)=>{
    const context=typeof document==='undefined'?null:document.createElement('canvas').getContext('2d');
    if(!context) return text.length*size*.65;
    context.font=`700 ${size}px "${style.font}"`;
    return context.measureText(text).width;
  };
  const title=fitHeadline(caption,portrait?800:1600,portrait?260:150,measure,portrait?78:70);
  return <AbsoluteFill style={{background:style.paper,color:style.ink,fontFamily:style.font,overflow:'hidden'}}>
    <AbsoluteFill style={{backgroundImage:'radial-gradient(#101b2418 .7px,transparent .7px)',backgroundSize:'7px 7px'}}/>
    <div style={{position:'absolute',left:box.left,top:portrait?230:100,color:style.ink,fontWeight:700,fontSize:title.fontSize,lineHeight:1.12}}>
      {title.lines.map((line,index)=><div key={index}>{line}</div>)}
    </div>
    <div style={{position:'absolute',...box,display:'flex',gap:portrait?26:55,alignItems:'stretch'}}>
      {photos.map((src,index)=>{
        const enter=Math.min(1,Math.max(0,(frame-index*5)/10));
        const eased=1-Math.pow(1-enter,3);
        return <div key={src} style={{position:'relative',flex:1,minWidth:0,padding:portrait?15:22,paddingBottom:portrait?45:50,boxSizing:'border-box',background:'#fffdf5',border:'1px solid #101b2430',boxShadow:'0 16px 30px #101b2430',transform:`translateY(${(1-eased)*28}px) rotate(${two?(index===0?-1.4:1.4):-1}deg)`,opacity:.8+.2*eased}}>
          <Img src={staticFile(src)} style={{width:'100%',height:'100%',objectFit:'contain',filter:'saturate(.7) contrast(1.04)',background:'#e7e1d6'}}/>
        </div>;
      })}
    </div>
    <div style={{position:'absolute',left:box.left,bottom:portrait?390:190,fontSize:24,letterSpacing:3,color:'#526569'}}>FOOTYBITEZ / PHOTO ESSAY</div>
    <div style={{position:'absolute',left:box.left,right:portrait?160:140,bottom:portrait?200:35,height:3,background:'#101b2420'}}><div style={{width:`${Math.min(1,frame/Math.max(1,durationInFrames-1))*100}%`,height:3,background:style.ink}}/></div>
  </AbsoluteFill>;
};
