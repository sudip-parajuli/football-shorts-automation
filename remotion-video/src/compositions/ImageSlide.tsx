import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from 'remotion';

interface ImageSlideProps {
  src: string;
  durationInFrames: number;
}

export const ImageSlide: React.FC<ImageSlideProps> = ({ src, durationInFrames }) => {
  const frame = useCurrentFrame();

  // Ken Burns: Slow zoom in (100% -> 108%)
  const scale = interpolate(
    frame,
    [0, durationInFrames],
    [1, 1.08],
    {
      extrapolateRight: 'clamp',
    }
  );

  return (
    <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: 'black' }}>
      <Img
        src={staticFile(src)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale})`,
        }}
      />
    </AbsoluteFill>
  );
};
