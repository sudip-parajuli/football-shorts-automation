import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

interface ChapterIntroProps {
  number: number;
  title: string;
}

export const ChapterIntro: React.FC<ChapterIntroProps> = ({ number, title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const totalFrames = 4 * fps; // 4 seconds

  const opacity = interpolate(frame, [0, 12, totalFrames - 18, totalFrames], [0, 1, 1, 0]);
  const translateY = interpolate(frame, [0, 18], [40, 0], {
    extrapolateRight: 'clamp',
  });
  const lineScale = interpolate(frame, [14, 28], [0, 1], {
    extrapolateLeft: 'clamp',
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
      <div style={{ textAlign: 'center', transform: `translateY(${translateY}px)`, padding: '0 80px' }}>
        <div
          style={{
            fontFamily: 'Barlow Condensed',
            fontSize: 48,
            color: '#F5A623',
            textTransform: 'uppercase',
            letterSpacing: 8,
            marginBottom: 16,
            fontWeight: 700,
          }}
        >
          Chapter {number}
        </div>
        <div
          style={{
            fontFamily: 'Barlow Condensed',
            fontSize: 140,
            color: 'white',
            fontWeight: 700,
            textTransform: 'uppercase',
            maxWidth: 1600,
            lineHeight: 1.05,
          }}
        >
          {title}
        </div>
        <div
          style={{
            width: `${lineScale * 120}px`,
            height: 5,
            backgroundColor: '#F5A623',
            margin: '40px auto 0',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
