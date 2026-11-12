import React from 'react';

// Neutral illustrations, not reconstructions of a real match or player reaction.
export const ContextIllustration:React.FC<{motif?:string; frame:number; accent:string}> = ({motif,frame,accent}) => {
  const reveal=Math.min(1,frame/18);
  if(!motif) return null;
  return <svg viewBox="0 0 400 300" style={{width:'100%',height:'100%',overflow:'visible'}} aria-label={`${motif} illustration`}>
    <g fill="none" stroke={accent} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" transform={`translate(0 ${5*Math.sin(frame/28)})`}>
      {motif==='contract' && <><rect x={110} y={35} width={180} height={225} rx={14}/><path d="M140 85 H255 M140 120 H245 M140 155 H225" opacity={.4}/><path d="M140 210 Q165 165 185 210 T250 210" strokeDasharray={180} strokeDashoffset={180*(1-reveal)}/></>}
      {motif==='trophy' && <><path d="M140 50 H260 V115 Q260 180 200 190 Q140 180 140 115 Z M200 190 V240 M155 250 H245 M140 75 H100 V110 Q100 155 150 155 M260 75 H300 V110 Q300 155 250 155"/><circle cx={200} cy={110} r={22} opacity={.3+.7*reveal}/></>}
      {motif==='calendar' && <><rect x={85} y={65} width={230} height={190} rx={16}/><path d="M85 120 H315 M145 40 V90 M255 40 V90"/>{[0,1,2].map(i=><path key={i} d={`M${125+i*70} 160 v45`} opacity={Math.min(1,Math.max(0,reveal*3-i))}/>)}</>}
      {motif==='recovery' && <><rect x={95} y={55} width={210} height={200} rx={24}/><path d="M180 105 H220 V135 H250 V175 H220 V205 H180 V175 H150 V135 H180 Z" opacity={.5+.5*reveal}/></>}
      {motif==='passing' && <><rect x={35} y={35} width={330} height={230} rx={16} opacity={.4}/><circle cx={100} cy={180} r={22}/><circle cx={300} cy={100} r={22}/><path d="M130 180 Q215 175 265 110" strokeDasharray={200} strokeDashoffset={200*(1-reveal)}/><path d="M245 108 L270 105 L262 130" opacity={reveal}/><circle cx={130+135*reveal} cy={180-70*reveal} r={7} fill={accent}/></>}
    </g>
  </svg>;
};
