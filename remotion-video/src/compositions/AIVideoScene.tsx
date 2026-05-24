import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, Video } from 'remotion';

export interface AIVideoSceneProps {
  assetPath: string;
  assetType: "video" | "image_fallback";
  durationInFrames: number;
  aiLabel?: string;
}

export const AIVideoScene: React.FC<AIVideoSceneProps> = ({
  assetPath,
  assetType,
  durationInFrames,
  aiLabel = "AI GENERATED",
}) => {
  const frame = useCurrentFrame();

  // Clean relative paths
  const cleanSrc = assetPath.replace(/^(\.\.\/)+/, '');

  // Aggressive Ken Burns for Image fallback
  const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.15], {
    extrapolateRight: 'clamp',
  });

  // Fade in
  const opacity = interpolate(frame, [0, 6], [0, 1], { extrapolateRight: 'clamp' });

  // Generate deterministic floating particles
  const particles = Array.from({ length: 20 }).map((_, idx) => {
    // Deterministic random seed values
    const seedX = (idx * 73.13) % 1;
    const seedY = (idx * 47.97) % 1;
    const size = 2 + (idx % 3);
    const speedX = 0.2 + ((idx % 3) * 0.15);
    const speedY = -0.3 - ((idx % 2) * 0.2);

    const x = (seedX * 100 + frame * speedX) % 100;
    const y = (seedY * 100 + frame * speedY + 100) % 100;

    return { id: idx, x, y, size };
  });

  return (
    <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#0a0a0a', opacity }}>
      {assetType === "video" ? (
        <Video
          src={staticFile(cleanSrc)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
          loop
          muted
        />
      ) : (
        <Img
          src={staticFile(cleanSrc)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${scale})`,
          }}
        />
      )}

      {/* Floating Dust Particles Overlay (5% opacity) */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          pointerEvents: 'none',
          opacity: 0.05,
        }}
      >
        {particles.map((p) => (
          <div
            key={p.id}
            style={{
              position: 'absolute',
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: `${p.size}px`,
              height: `${p.size}px`,
              borderRadius: '50%',
              backgroundColor: '#FFFFFF',
            }}
          />
        ))}
      </div>

      {/* Dark Vignette */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'radial-gradient(circle, rgba(0,0,0,0) 50%, rgba(0,0,0,0.6) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* AI Label Badge */}
      {aiLabel && (
        <div
          style={{
            position: 'absolute',
            top: '40px',
            left: '40px',
            border: '2px solid #F5A623',
            backgroundColor: 'rgba(6, 6, 16, 0.75)',
            color: '#F5A623',
            fontFamily: 'Barlow Condensed, sans-serif',
            fontSize: '18px',
            fontWeight: 700,
            letterSpacing: '3px',
            padding: '6px 16px',
            textTransform: 'uppercase',
            borderRadius: '2px',
            boxShadow: '0 2px 10px rgba(0, 0, 0, 0.5)',
          }}
        >
          {aiLabel}
        </div>
      )}
    </AbsoluteFill>
  );
};
