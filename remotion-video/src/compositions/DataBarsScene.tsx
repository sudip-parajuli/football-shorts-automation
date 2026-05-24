import React from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export interface DataBar {
  label: string;
  value: number;
  color: "amber" | "teal" | "purple" | "gray" | string;
}

export interface DataBarsSceneProps {
  title?: string;
  bar_data?: DataBar[];
  durationInFrames: number;
}

const COLOR_MAP: Record<string, string> = {
  amber:  "#F5A623",
  teal:   "#1EC8C8",
  purple: "#8E44AD",
  gray:   "#7F8C8D",
};

export const DataBarsScene: React.FC<DataBarsSceneProps> = ({
  title = "COMPARISON",
  bar_data = [],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Find max value to calibrate bar widths percentage
  const maxValue = bar_data.length > 0 ? Math.max(...bar_data.map(b => b.value)) : 100;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#080810',
        padding: '80px 100px',
        fontFamily: 'Barlow Condensed, sans-serif',
        justifyContent: 'center',
      }}
    >
      {/* Title */}
      <div
        style={{
          fontSize: '48px',
          fontWeight: 700,
          color: '#FFFFFF',
          textTransform: 'uppercase',
          letterSpacing: '4px',
          marginBottom: '50px',
          textAlign: 'center',
          borderBottom: '2px solid rgba(255, 255, 255, 0.1)',
          paddingBottom: '16px',
        }}
      >
        {title}
      </div>

      {/* Bars container */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          width: '100%',
        }}
      >
        {bar_data.map((bar, idx) => {
          // Stagger: 7 frames (0.3s) delay between each bar
          const delay = idx * 7;
          
          const progress = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: {
              damping: 18,
              stiffness: 85,
              mass: 0.9,
            },
          });

          const currentWidth = progress * (bar.value / maxValue) * 100;
          const barColor = COLOR_MAP[bar.color] || COLOR_MAP.amber;

          // Reveal text label when bar is at least 80% finished
          const textOpacity = progress >= 0.8 ? interpolateTextOpacity(frame - delay) : 0;

          return (
            <div
              key={`bar-${idx}`}
              style={{
                marginBottom: '40px',
                display: 'flex',
                flexDirection: 'column',
                width: '100%',
              }}
            >
              {/* Label */}
              <div
                style={{
                  fontSize: '28px',
                  color: '#AAAAAA',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  marginBottom: '8px',
                  letterSpacing: '1px',
                }}
              >
                {bar.label}
              </div>

              {/* Bar Wrapper */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  width: '100%',
                }}
              >
                {/* Visual Bar */}
                <div
                  style={{
                    width: `${currentWidth}%`,
                    height: '36px',
                    backgroundColor: barColor,
                    borderRadius: '4px',
                    boxShadow: `0 0 10px ${barColor}33`,
                    transition: 'width 0.05s linear',
                  }}
                />

                {/* Numeric Value */}
                <div
                  style={{
                    marginLeft: '20px',
                    fontSize: '32px',
                    fontWeight: 700,
                    color: '#FFFFFF',
                    opacity: textOpacity,
                  }}
                >
                  {bar.value.toLocaleString()}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// Simple helper to fade in text values
function interpolateTextOpacity(frameOffset: number) {
  if (frameOffset <= 0) return 0;
  // Fade in over 6 frames
  return Math.min(1, frameOffset / 6);
}
