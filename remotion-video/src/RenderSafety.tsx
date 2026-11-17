import React,{useEffect,useLayoutEffect,useRef,useState} from 'react';
import {AbsoluteFill,cancelRender,continueRender,delayRender,useCurrentFrame} from 'remotion';
import {findTextOverflow} from './layoutSafety';
import style from './editorialStyle.json';

export const RenderSafety:React.FC<{children:React.ReactNode}> = ({children}) => {
  const [handle]=useState(()=>delayRender('Loading typography for measured safe layouts'));
  const [ready,setReady]=useState(false);
  const root=useRef<HTMLDivElement>(null);
  const frame=useCurrentFrame();
  const released=useRef(false);
  useEffect(()=>{
    let mounted=true;
    document.fonts.load(`700 80px "${style.font}"`).then(()=>document.fonts.ready).then(()=>{
      if(mounted) {setReady(true);}
    }).catch(error=>cancelRender(error));
    return ()=>{mounted=false;};
  },[handle]);
  useLayoutEffect(()=>{
    if(!ready || !root.current) return;
    const failures=findTextOverflow(root.current);
    if(failures.length) cancelRender(new Error(`Text outside its safe layout at frame ${frame}: ${failures.join(' | ')}`));
    if(!released.current) {released.current=true;continueRender(handle);}
  },[ready,frame,handle]);
  return <AbsoluteFill ref={root}>{ready?children:null}</AbsoluteFill>;
};
