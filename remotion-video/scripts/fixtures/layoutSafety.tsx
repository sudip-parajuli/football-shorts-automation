import React from 'react';
import {AbsoluteFill,Composition,registerRoot} from 'remotion';
import {RenderSafety} from '../../src/RenderSafety';
import {SafeHeadline} from '../../src/compositions/ShortsScene';
import '../../src/style.css';
const Good:React.FC=()=> <RenderSafety><AbsoluteFill><SafeHeadline hook text="A complete long headline remains safely inside its measured composition"/></AbsoluteFill></RenderSafety>;
const Bad:React.FC=()=> <RenderSafety><AbsoluteFill><div style={{position:'absolute',left:100,top:300,fontSize:80,whiteSpace:'nowrap'}}>{'OVERFLOW'.repeat(100)}</div></AbsoluteFill></RenderSafety>;
registerRoot(()=> <><Composition id="SafeText" component={Good} width={1080} height={1920} fps={24} durationInFrames={3}/><Composition id="UnsafeText" component={Bad} width={1080} height={1920} fps={24} durationInFrames={3}/></>);
