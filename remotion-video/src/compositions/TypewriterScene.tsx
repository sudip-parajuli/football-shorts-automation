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

  // Find the last active spoken word index
  let lastActiveIdx = -1;
  typewriter_words.forEach((_, idx) => {
    const wt = word_timestamps[idx];
    const startFrame = wt ? wt.startFrame : 0;
    if (frame >= startFrame) {
      lastActiveIdx = idx;
    }
  });

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
        {lastActiveIdx === -1 && (
          <span
            style={{
              fontSize: 52,
              color: '#F5A623',
              opacity: Math.floor(frame / 12) % 2 === 0 ? 1 : 0,
              display: 'inline-block',
            }}
          >
            ▍
          </span>
        )}
        {typewriter_words.map((wordInfo, idx) => {
          const wt = word_timestamps[idx];
          const style = WEIGHT_STYLES[wordInfo.weight] || WEIGHT_STYLES.md;

          // If timing exists, use it; otherwise, fade in sequentially after the last timed word
          const startFrame = wt
            ? wt.startFrame
            : (word_timestamps.length > 0
                ? word_timestamps[word_timestamps.length - 1].startFrame + (idx - word_timestamps.length + 1) * 3
                : 0);

          // Animate word fade-in over 4 frames starting from startFrame
          const opacity = interpolate(
            frame,
            [startFrame, startFrame + 4],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
          );

          return (
            <React.Fragment key={`word-frag-${idx}`}>
              <span
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
              {idx === lastActiveIdx && (
                <span
                  style={{
                    fontSize: style.fontSize,
                    color: '#F5A623',
                    opacity: Math.floor(frame / 12) % 2 === 0 ? 1 : 0,
                    marginRight: '15px',
                    display: 'inline-block',
                  }}
                >
                  ▍
                </span>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
