import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

interface LowerThirdProps {
  title: string;
  subtitle?: string;
}

export const LowerThird: React.FC<LowerThirdProps> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 8, 120, 128], [0, 1, 1, 0]);
  const translateX = interpolate(frame, [0, 8], [-20, 0], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        padding: '0 0 80px 80px',
        opacity,
      }}
    >
      <div
        style={{
          transform: `translateX(${translateX}px)`,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            backgroundColor: 'rgba(0,0,0,0.7)',
            color: 'white',
            fontFamily: 'Barlow Condensed',
            fontSize: 48,
            fontWeight: 700,
            padding: '10px 30px',
            textTransform: 'uppercase',
            borderLeft: '8px solid #F5A623',
            width: 'fit-content',
          }}
        >
          {title}
        </div>
        {subtitle && (
          <div
            style={{
              backgroundColor: 'rgba(245, 166, 35, 0.9)',
              color: 'black',
              fontFamily: 'Barlow Condensed',
              fontSize: 24,
              fontWeight: 700,
              padding: '5px 30px',
              textTransform: 'uppercase',
              width: 'fit-content',
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
