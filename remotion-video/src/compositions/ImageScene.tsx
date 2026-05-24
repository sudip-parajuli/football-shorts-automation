import React from 'react';
import { AbsoluteFill, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { LowerThird } from './LowerThird';

export interface ImageSceneProps {
  assetPath: string;
  durationInFrames: number;
  ken_burns_style?: "zoom_in_center" | "zoom_in_topleft" | "pan_left" | "pan_right" | string;
  named_entity?: { name: string; description: string };
  caption?: string;
}

export const ImageScene: React.FC<ImageSceneProps> = ({
  assetPath,
  durationInFrames,
  ken_burns_style = "zoom_in_center",
  named_entity,
  caption,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Clean any relative path segments (e.g. ../../footybitez/...)
  const cleanSrc = assetPath.replace(/^(\.\.\/)+/, '');

  // Ken Burns Animation Setup
  let scale = 1.0;
  let translateX = 0;
  let translateY = 0;

  if (ken_burns_style === "zoom_in_topleft") {
    scale = interpolate(frame, [0, durationInFrames], [1.0, 1.10], { extrapolateRight: 'clamp' });
    translateX = interpolate(frame, [0, durationInFrames], [0, -30], { extrapolateRight: 'clamp' });
    translateY = interpolate(frame, [0, durationInFrames], [0, -15], { extrapolateRight: 'clamp' });
  } else if (ken_burns_style === "pan_left") {
    scale = 1.04;
    translateX = interpolate(frame, [0, durationInFrames], [30, -30], { extrapolateRight: 'clamp' });
  } else if (ken_burns_style === "pan_right") {
    scale = 1.04;
    translateX = interpolate(frame, [0, durationInFrames], [-30, 30], { extrapolateRight: 'clamp' });
  } else {
    // zoom_in_center (default)
    scale = interpolate(frame, [0, durationInFrames], [1.0, 1.08], { extrapolateRight: 'clamp' });
  }

  // Fade in over first 6 frames
  const opacity = interpolate(frame, [0, 6], [0, 1], { extrapolateRight: 'clamp' });

  const ltStart = Math.round(0.5 * fps);
  const ltDuration = Math.round(3.0 * fps);

  return (
    <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#0a0a0a', opacity }}>
      {/* Sourced Image with Ken Burns and Cinematic Color Grading */}
      <Img
        src={staticFile(cleanSrc)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale}) translate(${translateX}px, ${translateY}px)`,
          filter: 'contrast(1.15) saturate(0.88)',
        }}
      />

      {/* Cinematic Vignette Overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'radial-gradient(circle, rgba(0,0,0,0) 40%, rgba(0,0,0,0.65) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Optional Top or Bottom Caption */}
      {caption && (
        <div
          style={{
            position: 'absolute',
            bottom: '40px',
            left: '5%',
            right: '5%',
            textAlign: 'center',
            color: 'white',
            fontFamily: 'Barlow Condensed, sans-serif',
            fontSize: '32px',
            fontWeight: 600,
            textShadow: '0 2px 10px rgba(0,0,0,0.9)',
            textTransform: 'uppercase',
            backgroundColor: 'rgba(0,0,0,0.5)',
            padding: '10px 20px',
            borderRadius: '4px',
          }}
        >
          {caption}
        </div>
      )}

      {/* Named Entity Lower Third */}
      {named_entity && named_entity.name && (
        <Sequence from={ltStart} durationInFrames={ltDuration}>
          <LowerThird title={named_entity.name} subtitle={named_entity.description} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};
