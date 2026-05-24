import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

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
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          alignItems: 'center',
          maxWidth: '95%',
          fontFamily: 'Barlow Condensed, sans-serif',
          lineHeight: '1.4',
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
              ? (WEIGHT_STYLES[typewriter_words[visibleIndices[visibleIndices.length - 1]]?.weight || 'md']?.fontSize || 38)
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
