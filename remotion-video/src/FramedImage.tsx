import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';

// The foreground always contains the complete source; only the decorative backdrop crops.
export const FramedImage:React.FC<{src:string; durationInFrames:number; reverse?:boolean}> = ({src,durationInFrames,reverse=false}) => {
  const progress=Math.min(1,useCurrentFrame()/Math.max(1,durationInFrames-1));
  const scale=reverse?1-progress*.035:.965+progress*.035;
  return <AbsoluteFill style={{overflow:'hidden',background:'#101b24'}}>
    <Img src={staticFile(src)} style={{position:'absolute',width:'100%',height:'100%',objectFit:'cover',filter:'blur(32px) brightness(.28)',transform:'scale(1.1)'}}/>
    <div style={{position:'absolute',left:'6%',right:'6%',top:'16%',bottom:'20%',transform:`scale(${scale})`,transformOrigin:'center'}}>
      <Img src={staticFile(src)} style={{width:'100%',height:'100%',objectFit:'contain',objectPosition:'center',filter:'drop-shadow(0 12px 30px #0006)'}}/>
    </div>
  </AbsoluteFill>;
};
