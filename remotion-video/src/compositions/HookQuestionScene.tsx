import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

export interface HookQuestionSceneProps {
  question_text?: string;
  emphasis_phrase?: string;
  durationInFrames: number;
}

const escapeRegExp = (str: string) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

export const HookQuestionScene: React.FC<HookQuestionSceneProps> = ({
  question_text = '',
  emphasis_phrase = '',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Full text fades in over 12 frames (0.5s at 24fps)
  const textOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' });

  // Animate lines width from 0 to 180px over 8 frames
  const lineWidth = interpolate(frame, [0, 8], [0, 180], { extrapolateRight: 'clamp' });

  const renderHighlightedText = (text: string, phrase?: string) => {
    if (!phrase) return <span>{text}</span>;
    const regex = new RegExp(`(${escapeRegExp(phrase)})`, 'gi');
    const parts = text.split(regex);
    return (
      <>
        {parts.map((part, i) => (
          <span
            key={i}
            style={{
              color: part.toLowerCase() === phrase.toLowerCase() ? '#F5A623' : '#FFFFFF',
            }}
          >
            {part}
          </span>
        ))}
      </>
    );
  };

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#050510',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '0 100px',
      }}
    >
      {/* Top Line */}
      <div
        style={{
          width: `${lineWidth}px`,
          height: '4px',
          backgroundColor: '#F5A623',
          marginBottom: '40px',
          boxShadow: '0 0 10px rgba(245, 166, 35, 0.4)',
        }}
      />

      {/* Rhetorical/Hook Question Text */}
      <div
        style={{
          fontFamily: 'Georgia, serif',
          fontSize: '64px',
          fontWeight: 'normal',
          fontStyle: 'italic',
          textAlign: 'center',
          lineHeight: '1.4',
          opacity: textOpacity,
          maxWidth: '85%',
        }}
      >
        {renderHighlightedText(question_text, emphasis_phrase)}
      </div>

      {/* Bottom Line */}
      <div
        style={{
          width: `${lineWidth}px`,
          height: '4px',
          backgroundColor: '#F5A623',
          marginTop: '40px',
          boxShadow: '0 0 10px rgba(245, 166, 35, 0.4)',
        }}
      />
    </AbsoluteFill>
  );
};
