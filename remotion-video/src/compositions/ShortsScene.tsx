import React, { useMemo } from 'react';
import { AbsoluteFill, Img, Video, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { fitHeadline } from '../shortLayout';

export interface ShortVisual {
  from_frame: number;
  duration_frames: number;
  headline: string;
  narration_snippet: string;
  theme: string;
  src: string;
  kind: string;
}

export const SafeHeadline: React.FC<{text: string; hook?: boolean}> = ({text, hook = false}) => {
  const frame = useCurrentFrame();
  const layout = useMemo(() => {
    const canvas = typeof document === 'undefined' ? null : document.createElement('canvas');
    const context = canvas?.getContext('2d');
    return fitHeadline(text, 820, hook ? 350 : 220, (value, size) => {
      if (!context) return value.length * size * 0.64;
      context.font = `700 ${size}px "Barlow Condensed"`;
      return context.measureText(value).width;
    }, hook ? 98 : 76);
  }, [text, hook]);
  return <div style={{position:'absolute', left:100, top:hook ? 220 : 185, width:820, height:hook ? 350 : 220,
    boxSizing:'border-box', zIndex:30, fontFamily:'Barlow Condensed', fontWeight:700,
    fontSize:layout.fontSize, lineHeight:1.12, color:'#fffbed', textAlign:'left',
    opacity:interpolate(frame,[0,4],[0,1],{extrapolateRight:'clamp'}),
    textShadow:'0 4px 18px #000a'}}>
    {layout.lines.map((line, index) => <div key={index} style={{width:820, whiteSpace:'pre-wrap', overflowWrap:'anywhere'}}>{line}</div>)}
  </div>;
};

const Ball: React.FC<{x:number;y:number;r?:number}> = ({x,y,r=20}) => <g transform={`translate(${x} ${y})`}>
  <circle r={r+9} fill="#0005" cy={7}/><circle r={r} fill="#fffbed"/>
  <path d={`M0 ${-r*.55} L${r*.55} ${-r*.1} L${r*.32} ${r*.5} L${-r*.32} ${r*.5} L${-r*.55} ${-r*.1} Z`} fill="#17343d"/>
</g>;

const Player: React.FC<{x:number;y:number;color?:string}> = ({x,y,color='#f7c64d'}) => <g transform={`translate(${x} ${y})`}>
  <ellipse cy={64} rx={39} ry={10} fill="#0004"/><circle cy={-38} r={22} fill={color}/>
  <path d="M-29 -8 Q0 -24 29 -8 L39 44 L18 48 L11 16 L13 68 L-10 68 L-13 16 L-21 47 L-40 40 Z" fill={color}/>
</g>;

const Label: React.FC<{x:number;y:number;children:React.ReactNode;color?:string}> = ({x,y,children,color='#d8e8de'}) =>
  <text x={x} y={y} textAnchor="middle" fill={color} fontSize={28} fontWeight={700} fontFamily="Barlow Condensed">{children}</text>;

const Pitch: React.FC<{t:number;tactics?:boolean;training?:boolean}> = ({t,tactics,training}) => <g>
  <rect x={85} y={90} width={630} height={660} rx={24} fill="#103f39" stroke="#6baf8b" strokeWidth={3}/>
  {[0,1,2,3,4,5].map(i=><rect key={i} x={88} y={94+i*109} width={624} height={54} fill="#1d5444" opacity={.4}/>)}
  <path d="M85 420 H715 M250 90 V215 H550 V90 M250 750 V625 H550 V750" fill="none" stroke="#94c4a0" strokeWidth={3}/>
  <circle cx={400} cy={420} r={84} fill="none" stroke="#94c4a0" strokeWidth={3}/>
  <Player x={260} y={550} /><Player x={540} y={310} color="#e7ece6"/>
  <Player x={275} y={290} color="#7da6d8"/><Player x={535} y={545} color="#7da6d8"/>
  {tactics && <><path d="M95 335 H705" stroke="#f7c64d" strokeWidth={5} strokeDasharray="14 12"/>
    <Label x={400} y={320} color="#f7c64d">POSITION MATTERS</Label></>}
  {training && [0,1,2].map(i=><path key={i} d={`M${340+i*55} 610 l-13 30 h26 Z`} fill="#f5a14e"/>)}
  <path d="M275 540 Q410 530 530 330" fill="none" stroke="#f7c64d88" strokeWidth={4} strokeDasharray="12 14"/>
  <Ball x={275+255*t} y={540-210*t} />
  <Label x={400} y={800}>{tactics ? 'TACTICAL ILLUSTRATION' : training ? 'TRAINING / MOVEMENT' : 'THE GAME ON THE PITCH'}</Label>
</g>;

const Contract: React.FC<{t:number}> = ({t}) => <g>
  <g transform={`translate(0 ${Math.sin(t*Math.PI*2)*10})`}>
    <rect x={205} y={125} width={390} height={500} rx={22} fill="#fff9e9"/>
    <rect x={245} y={170} width={130} height={12} rx={6} fill="#17343d"/>
    {[0,1,2,3].map(i=><rect key={i} x={245} y={240+i*46} width={300-i*22} height={9} rx={4} fill="#a9bcb6"/>)}
    <path d="M255 515 Q280 450 310 510 T375 505 Q400 460 465 510" fill="none" stroke="#17343d" strokeWidth={7}
      strokeDasharray="400" strokeDashoffset={400*(1-Math.min(1,t*2))}/>
    <circle cx={555} cy={595} r={65} fill="#f7c64d"/><path d="M523 593 l23 25 40 -48" fill="none" stroke="#17343d" strokeWidth={10}/>
  </g>
  <Label x={400} y={735}>CONTRACTS / REPRESENTATION</Label>
</g>;

const Network: React.FC<{t:number;transfer?:boolean}> = ({t,transfer}) => <g>
  <path d="M170 430 L400 230 L630 430 L400 640 Z M170 430 H630 M400 230 V640" fill="none" stroke="#71928a" strokeWidth={4}/>
  {[{x:170,y:430,label:'PLAYER'},{x:400,y:230,label:transfer?'DEAL':'AGENT'},{x:630,y:430,label:'CLUB'}].map(({x,y,label},i)=><g key={label}>
    <circle cx={x} cy={y} r={75} fill={i===1?'#f7c64d':'#244d4b'} stroke="#90b3a3" strokeWidth={3}/>
    <Label x={x} y={y+10} color={i===1?'#17343d':'#fffbed'}>{label}</Label>
  </g>)}
  <Ball x={170+460*t} y={430} r={14}/>
  <rect x={300} y={585} width={200} height={90} rx={20} fill="#1b393b"/>
  <Label x={400} y={640}>NEGOTIATION</Label>
  <Label x={400} y={790}>{transfer?'HOW A TRANSFER MOVES':'WHO CONNECTS THE DEAL'}</Label>
</g>;

const Pressure: React.FC<{t:number}> = ({t}) => <g>
  {[0,1,2].map(i=><circle key={i} cx={400} cy={425} r={130+i*70+Math.sin(t*6+i)*10} fill="none" stroke={i===0?'#f7c64d':'#45605e'} strokeWidth={3} opacity={1-i*.22}/>)}
  <Player x={400} y={415}/><Ball x={465} y={490}/>
  <path d="M125 425 H230 M570 425 H675 M400 130 V230" stroke="#ef8a6b" strokeWidth={6} strokeDasharray="12 8"/>
  <Label x={400} y={785}>PRESSURE / FOCUS</Label>
</g>;

const Kit: React.FC<{t:number}> = ({t}) => <g>
  {[0,1].map(i=><g key={i} transform={`translate(${125+i*320} ${230+Math.sin(t*6+i)*10})`}>
    <path d="M55 0 L100 28 L145 0 L210 55 L175 125 L148 105 V330 H52 V105 L25 125 L-10 55 Z" fill={i?'#e9ede4':'#f7c64d'} stroke="#89a59a" strokeWidth={3}/>
    <path d="M60 15 Q100 65 140 15" fill="none" stroke="#17343d" strokeWidth={8}/>
    <Label x={100} y={400}>DESIGN {i+1}</Label>
  </g>)}
  <Label x={400} y={800}>FOOTBALL KIT / ILLUSTRATION</Label>
</g>;

export const ShortsScene: React.FC<{scene:ShortVisual; hook?:boolean; hookText?:string}> = ({scene,hook=false,hookText=''}) => {
  const frame = useCurrentFrame();
  const progress = Math.min(1,frame/Math.max(1,scene.duration_frames));
  const t = .5-.5*Math.cos(progress*Math.PI*2);
  const hasMedia = scene.kind==='media' && Boolean(scene.src);
  return <AbsoluteFill style={{background:'#0b2027',overflow:'hidden'}}>
    {hasMedia ? <>
      {/\.(mp4|mov|webm)$/i.test(scene.src)
        ? <Video src={staticFile(scene.src)} muted loop style={{width:'100%',height:'100%',objectFit:'cover'}}/>
        : <Img src={staticFile(scene.src)} style={{width:'100%',height:'100%',objectFit:'cover',transform:`scale(${1+progress*.04})`}}/>}
      <AbsoluteFill style={{background:'linear-gradient(#04131bd9 0%,#04131b22 42%,#04131bd9 85%)'}}/>
      <div style={{position:'absolute',left:100,top:1380,color:'#a5c5bb',fontSize:24,fontFamily:'Barlow Condensed'}}>ILLUSTRATIVE FOOTAGE</div>
    </> : <>
      <AbsoluteFill style={{background:'radial-gradient(ellipse at 70% 45%,#28514d 0%,#0b2027 60%)'}}/>
      <svg viewBox="0 0 800 900" style={{position:'absolute',left:80,top:hook?520:440,width:880,height:990}}>
        {scene.theme==='contract' ? <Contract t={t}/> : scene.theme==='network' || scene.theme==='transfer'
          ? <Network t={t} transfer={scene.theme==='transfer'}/> : scene.theme==='pressure' ? <Pressure t={t}/>
          : scene.theme==='kit' ? <Kit t={t}/> : <Pitch t={t} tactics={scene.theme==='tactics'} training={scene.theme==='training'}/>}
      </svg>
      <div style={{position:'absolute',left:100,top:1450,color:'#9cb8ae',fontSize:22,fontFamily:'Barlow Condensed',letterSpacing:2}}>ANIMATED EXPLAINER / NOT MATCH FOOTAGE</div>
    </>}
    <SafeHeadline text={hook ? hookText : scene.headline} hook={hook}/>
    <div style={{position:'absolute',left:100,right:150,bottom:200,height:4,background:'#36534c'}}>
      <div style={{height:4,width:`${progress*100}%`,background:'#f7c64d'}}/>
    </div>
  </AbsoluteFill>;
};
