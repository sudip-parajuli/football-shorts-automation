import React from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from 'remotion';

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

export interface KineticStatSceneProps {
  stat_data?: {
    value: number;
    unit: string;
    label: string;
  };
  durationInFrames: number;
}

export const KineticStatScene: React.FC<KineticStatSceneProps> = ({
  stat_data = { value: 0, unit: '', label: '' },
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const { value, unit, label } = stat_data;

  // Spring animation for counting up
  const progress = spring({
    frame,
    fps,
    config: {
      damping: 15,
      stiffness: 80,
      mass: 0.8,
    },
  });

  const currentValue = Math.round(progress * value);

  // Animation for the entry details
  const scale = spring({
    frame,
    fps,
    config: { damping: 12 },
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#060610',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '0 80px',
        fontFamily: 'Barlow Condensed, sans-serif',
      }}
    >
      <PITCH_LINES_SVG />
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          transform: `scale(${scale})`,
          maxWidth: '85%',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {/* Unit Above */}
        {unit && (
          <div
            style={{
              fontSize: 28,
              color: '#AAAAAA',
              letterSpacing: 6,
              textTransform: 'uppercase',
              marginBottom: 10,
              fontWeight: 500,
            }}
          >
            {unit}
          </div>
        )}

        {/* Large Number */}
        <div
          style={{
            fontSize: 200,
            color: '#F5A623',
            fontWeight: 800,
            lineHeight: '0.9',
            textShadow: '0 0 20px rgba(245, 166, 35, 0.2)',
          }}
        >
          {currentValue.toLocaleString()}
        </div>

        {/* Thin Amber Separator Line */}
        <div
          style={{
            width: '120px',
            height: '4px',
            backgroundColor: '#F5A623',
            margin: '25px 0',
          }}
        />

        {/* Label Below */}
        {label && (
          <div
            style={{
              fontSize: 48,
              color: '#FFFFFF',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: 2,
              lineHeight: '1.2',
            }}
          >
            {label}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
