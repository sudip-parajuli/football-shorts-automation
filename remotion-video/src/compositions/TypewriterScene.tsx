import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

const PITCH_LINES_SVG = ({ opacity = 0.06 }: { opacity?: number }) => (
  <svg
    width="1280"
    height="720"
    viewBox="0 0 1280 720"
    style={{
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      opacity,
      pointerEvents: 'none',
    }}
  >
    <rect width="1280" height="720" fill="#1A3A1A" />
    <line x1="640" y1="0" x2="640" y2="720" stroke="#FFFFFF" strokeWidth="2" />
    <circle cx="640" cy="360" r="60" fill="none" stroke="#FFFFFF" strokeWidth="2" />
    <circle cx="640" cy="360" r="4" fill="#FFFFFF" />
    <rect x="430" y="0" width="420" height="120" fill="none" stroke="#FFFFFF" strokeWidth="2" />
    <line x1="640" y1="0" x2="640" y2="120" stroke="#FFFFFF" strokeWidth="2" />
    <rect x="430" y="600" width="420" height="120" fill="none" stroke="#FFFFFF" strokeWidth="2" />
    <line x1="640" y1="600" x2="640" y2="720" stroke="#FFFFFF" strokeWidth="2" />
    <rect x="540" y="0" width="160" height="60" fill="none" stroke="#FFFFFF" strokeWidth="2" />
    <rect x="540" y="660" width="160" height="60" fill="none" stroke="#FFFFFF" strokeWidth="2" />
  </svg>
);

export interface TypewriterWord {
  word: string;
  weight: "xl_accent" | "xl_amber" | "lg" | "md" | "dim" | string;
}

export interface WordTimestamp {
  word: string;
  startFrame: number;
}

export interface TypewriterSceneProps {
  typewriter_words?: TypewriterWord[];
  word_timestamps?: WordTimestamp[];
  durationInFrames: number;
}

const WEIGHT_STYLES: Record<string, React.CSSProperties> = {
  xl_accent: { fontSize: 72, color: "#F5A623", fontWeight: 700 },
  xl_amber:  { fontSize: 72, color: "#FFFFFF", fontWeight: 700 },
  lg:        { fontSize: 52, color: "#FFFFFF", fontWeight: 700 },
  md:        { fontSize: 38, color: "#AAAAAA", fontWeight: 500 },
  dim:       { fontSize: 28, color: "#444444", fontWeight: 400 },
};

export const TypewriterScene: React.FC<TypewriterSceneProps> = ({
  typewriter_words = [],
  word_timestamps = [],
}) => {
  const frame = useCurrentFrame();

  // Find all words that have started displaying
  const activeWordIndices: number[] = [];
  word_timestamps.forEach((wt, idx) => {
    if (frame >= wt.startFrame) {
      activeWordIndices.push(idx);
    }
  });

  // Limit to rolling window of the last 10 active words
  const visibleIndices = activeWordIndices.slice(-10);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0A0A12',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '0 80px',
      }}
    >
      <PITCH_LINES_SVG />
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          alignItems: 'center',
          maxWidth: '95%',
          fontFamily: 'Barlow Condensed, sans-serif',
          lineHeight: '1.4',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {visibleIndices.map((idx) => {
          const wt = word_timestamps[idx];
          const wordInfo = typewriter_words[idx] || { word: wt.word, weight: 'md' };
          const style = WEIGHT_STYLES[wordInfo.weight] || WEIGHT_STYLES.md;
          
          // Animate word fade-in over 4 frames starting from startFrame
          const opacity = interpolate(
            frame,
            [wt.startFrame, wt.startFrame + 4],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
          );

          return (
            <span
              key={`word-${idx}`}
              style={{
                ...style,
                opacity,
                marginRight: '15px',
                display: 'inline-block',
                textTransform: 'uppercase',
              }}
            >
              {wordInfo.word}
            </span>
          );
        })}
{/* Blinking amber cursor */}
         <span
           style={{
             fontSize: visibleIndices.length > 0 
               ? 38 
               : 52,
             color: '#F5A623',
             opacity: Math.floor(frame / 12) % 2 === 0 ? 1 : 0,
             marginLeft: '2px',
           }}
         >
           ▍
         </span>
      </div>
    </AbsoluteFill>
  );
};
