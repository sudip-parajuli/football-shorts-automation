import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from 'remotion';

interface ImageSlideProps {
  src: string;
  durationInFrames: number;
  effectIndex?: number; // 0-4 for different Ken Burns effects
}

export const ImageSlide: React.FC<ImageSlideProps> = ({ src, durationInFrames, effectIndex = 0 }) => {
  const frame = useCurrentFrame();

  // Fade in over first 8 frames
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: 'clamp' });

  // 5 different Ken Burns effects based on effectIndex
  let scale = 1;
  let translateX = 0;
  let translateY = 0;

  const effect = effectIndex % 5;

  if (effect === 0) {
    // Slow zoom in (classic)
    scale = interpolate(frame, [0, durationInFrames], [1.0, 1.12], { extrapolateRight: 'clamp' });
  } else if (effect === 1) {
    // Zoom out
    scale = interpolate(frame, [0, durationInFrames], [1.12, 1.0], { extrapolateRight: 'clamp' });
  } else if (effect === 2) {
    // Pan left to right
    scale = 1.08;
    translateX = interpolate(frame, [0, durationInFrames], [-40, 40], { extrapolateRight: 'clamp' });
  } else if (effect === 3) {
    // Pan right to left
    scale = 1.08;
    translateX = interpolate(frame, [0, durationInFrames], [40, -40], { extrapolateRight: 'clamp' });
  } else {
    // Diagonal zoom: bottom-left to top-right
    scale = interpolate(frame, [0, durationInFrames], [1.0, 1.12], { extrapolateRight: 'clamp' });
    translateX = interpolate(frame, [0, durationInFrames], [-20, 20], { extrapolateRight: 'clamp' });
    translateY = interpolate(frame, [0, durationInFrames], [10, -10], { extrapolateRight: 'clamp' });
  }

  // Clean any relative path segments (e.g. ../../footybitez/...) 
  const cleanSrc = src.replace(/^(\.\.\/)+/, '');

  return (
    <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: 'black', opacity }}>
      <Img
        src={staticFile(cleanSrc)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale}) translate(${translateX}px, ${translateY}px)`,
        }}
      />
    </AbsoluteFill>
  );
};

