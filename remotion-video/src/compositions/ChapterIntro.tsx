import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

interface ChapterIntroProps {
  number: number;
  title: string;
}

export const ChapterIntro: React.FC<ChapterIntroProps> = ({ number, title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, 10, 40, 48], [0, 1, 1, 0]);
  const translateY = interpolate(frame, [0, 10], [20, 0], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0a0a0a',
        justifyContent: 'center',
        alignItems: 'center',
        opacity,
      }}
    >
      <div style={{ textAlign: 'center', transform: `translateY(${translateY}px)` }}>
        <div
          style={{
            fontFamily: 'Barlow Condensed',
            fontSize: 24,
            color: '#F5A623',
            textTransform: 'uppercase',
            letterSpacing: 4,
            marginBottom: 10,
            fontWeight: 700,
          }}
        >
          Chapter {number}
        </div>
        <div
          style={{
            fontFamily: 'Barlow Condensed',
            fontSize: 80,
            color: 'white',
            fontWeight: 700,
            textTransform: 'uppercase',
            maxWidth: 800,
            lineHeight: 1.1,
          }}
        >
          {title}
        </div>
        <div
          style={{
            width: 100,
            height: 4,
            backgroundColor: '#F5A623',
            margin: '40px auto 0',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
