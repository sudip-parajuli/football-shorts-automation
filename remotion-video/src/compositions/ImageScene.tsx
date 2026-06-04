import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

export interface ImageSceneProps {
  assetPath: string;
  durationInFrames: number;
  ken_burns_style?: string;
  named_entity?: { name: string; description: string };
  caption?: string;
  secondary_asset_path?: string; // Optional corner overlay image
}

// Subtle animated film-grain noise via SVG feTurbulence
const FilmGrain: React.FC<{ frame: number }> = ({ frame }) => (
  <svg
    style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', opacity: 0.06 }}
    xmlns="http://www.w3.org/2000/svg"
  >
    <filter id={`grain-${frame % 4}`}>
      <feTurbulence
        type="fractalNoise"
        baseFrequency={0.65 + (frame % 4) * 0.01}
        numOctaves={3}
        stitchTiles="stitch"
      />
      <feColorMatrix type="saturate" values="0" />
    </filter>
    <rect width="100%" height="100%" filter={`url(#grain-${frame % 4})`} />
  </svg>
);

// Subtle animated light-leak flash on cut-in
const LightLeak: React.FC<{ frame: number; color?: string }> = ({ frame, color = '#F5A623' }) => {
  const opacity = interpolate(frame, [0, 3, 10], [0.25, 0.08, 0], { extrapolateRight: 'clamp' });
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `radial-gradient(ellipse at 20% 10%, ${color}66 0%, transparent 60%)`,
        opacity,
        pointerEvents: 'none',
        mixBlendMode: 'screen',
      }}
    />
  );
};

// Animated corner accent lines (top-left + bottom-right)
const CornerAccents: React.FC<{ frame: number; color?: string }> = ({ frame, color = '#F5A623' }) => {
  const p = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' });
  const SIZE = 40;
  const THICKNESS = 2;
  return (
    <>
      {/* Top-left */}
      <div style={{ position: 'absolute', top: 20, left: 20, pointerEvents: 'none' }}>
        <div style={{ width: SIZE * p, height: THICKNESS, backgroundColor: color, opacity: 0.7 }} />
        <div style={{ width: THICKNESS, height: SIZE * p, backgroundColor: color, opacity: 0.7 }} />
      </div>
      {/* Bottom-right */}
      <div style={{ position: 'absolute', bottom: 20, right: 20, pointerEvents: 'none', display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
        <div style={{ width: SIZE * p, height: THICKNESS, backgroundColor: color, opacity: 0.7 }} />
        <div style={{ width: THICKNESS, height: SIZE * p, backgroundColor: color, opacity: 0.7, alignSelf: 'flex-end' }} />
      </div>
    </>
  );
};

export const ImageScene: React.FC<ImageSceneProps> = ({
  assetPath,
  durationInFrames,
  ken_burns_style = 'zoom_in_center',
  named_entity,
  caption,
  secondary_asset_path,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cleanSrc = assetPath.replace(/^(\.\.\/)+ /, '').replace(/^(\.\.\/)/, '');
  const cleanSecondarySrc = secondary_asset_path?.replace(/^(\.\.\/)+ /, '').replace(/^(\.\.\/)/, '');

  // ── Ken Burns ─────────────────────────────────────────────────────────────
  let scale = 1.0;
  let translateX = 0;
  let translateY = 0;

  const t = frame / Math.max(1, durationInFrames);

  switch (ken_burns_style) {
    case 'zoom_in_topleft':
      scale = interpolate(frame, [0, durationInFrames], [1.0, 1.11], { extrapolateRight: 'clamp' });
      translateX = interpolate(frame, [0, durationInFrames], [0, -35], { extrapolateRight: 'clamp' });
      translateY = interpolate(frame, [0, durationInFrames], [0, -20], { extrapolateRight: 'clamp' });
      break;
    case 'zoom_out_center':
      scale = interpolate(frame, [0, durationInFrames], [1.12, 1.0], { extrapolateRight: 'clamp' });
      break;
    case 'pan_left':
      scale = 1.06;
      translateX = interpolate(frame, [0, durationInFrames], [40, -40], { extrapolateRight: 'clamp' });
      break;
    case 'pan_right':
      scale = 1.06;
      translateX = interpolate(frame, [0, durationInFrames], [-40, 40], { extrapolateRight: 'clamp' });
      break;
    case 'pan_diagonal':
      scale = 1.07;
      translateX = interpolate(frame, [0, durationInFrames], [-30, 30], { extrapolateRight: 'clamp' });
      translateY = interpolate(frame, [0, durationInFrames], [20, -20], { extrapolateRight: 'clamp' });
      break;
    case 'tilt_up':
      scale = 1.06;
      translateY = interpolate(frame, [0, durationInFrames], [40, -20], { extrapolateRight: 'clamp' });
      break;
    case 'tilt_down':
      scale = 1.06;
      translateY = interpolate(frame, [0, durationInFrames], [-20, 40], { extrapolateRight: 'clamp' });
      break;
    case 'zoom_in_center':
    default:
      scale = interpolate(frame, [0, durationInFrames], [1.0, 1.09], { extrapolateRight: 'clamp' });
      break;
  }

  // Fade in over first 6 frames
  const opacity = interpolate(frame, [0, 6], [0, 1], { extrapolateRight: 'clamp' });

  const ltStart = Math.round(0.5 * fps); // used for named entity tag fade-in

  const isMissingAsset = !cleanSrc || cleanSrc === 'assets/images/placeholder.jpg';

  // Secondary image reveal spring
  const secondaryOpacity = interpolate(frame, [fps * 0.8, fps * 1.3], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#0a0a0a', opacity }}>
      {/* Primary Image with Ken Burns */}
      {isMissingAsset ? (
        <AbsoluteFill
          style={{
            background: 'linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 40%, #16213e 70%, #0f3460 100%)',
          }}
        />
      ) : (
        <Img
          src={staticFile(cleanSrc)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${scale}) translate(${translateX}px, ${translateY}px)`,
            filter: 'contrast(1.18) saturate(0.85) brightness(0.92)',
          }}
        />
      )}

      {/* Cinematic Vignette */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 35%, rgba(0,0,0,0.72) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Bottom gradient for text readability */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '35%',
          background: 'linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Film Grain */}
      <FilmGrain frame={frame} />

      {/* Light Leak on cut-in */}
      <LightLeak frame={frame} />

      {/* Corner accents */}
      <CornerAccents frame={frame} />

      {/* Secondary entity image (corner badge) */}
      {cleanSecondarySrc && (
        <div
          style={{
            position: 'absolute',
            top: 30,
            right: 30,
            width: 180,
            height: 130,
            borderRadius: 8,
            overflow: 'hidden',
            opacity: secondaryOpacity,
            border: '2px solid rgba(245,166,35,0.6)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
          }}
        >
          <Img
            src={staticFile(cleanSecondarySrc)}
            style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'contrast(1.1)' }}
          />
        </div>
      )}

      {/* Caption Tag — top-left amber chip */}
      {caption && (
        <div
          style={{
            position: 'absolute',
            top: 68,
            left: 20,
            color: '#fff',
            fontFamily: 'Barlow Condensed, Oswald, sans-serif',
            fontSize: 26,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            backgroundColor: 'rgba(245,166,35,0.92)',
            padding: '5px 16px 5px 14px',
            borderRadius: '3px',
            boxShadow: '0 2px 12px rgba(0,0,0,0.55)',
            borderLeft: '4px solid #fff',
            opacity: interpolate(frame, [4, 14], [0, 1], { extrapolateRight: 'clamp' }),
            pointerEvents: 'none',
            zIndex: 20,
          }}
        >
          {caption}
        </div>
      )}

      {/* Named Entity Tag — top-left below caption if both present */}
      {named_entity && named_entity.name && (
        <div
          style={{
            position: 'absolute',
            top: caption ? 110 : 68,
            left: 20,
            opacity: interpolate(frame, [ltStart, ltStart + 10], [0, 1], { extrapolateRight: 'clamp' }),
            pointerEvents: 'none',
            zIndex: 20,
          }}
        >
          {/* Name strip */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}
          >
            <div
              style={{
                backgroundColor: 'rgba(10,10,10,0.88)',
                color: '#F5A623',
                fontFamily: 'Barlow Condensed, Oswald, sans-serif',
                fontSize: 22,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '1px',
                padding: '4px 14px',
                borderLeft: '4px solid #F5A623',
                boxShadow: '0 2px 10px rgba(0,0,0,0.5)',
              }}
            >
              {named_entity.name}
            </div>
            {named_entity.description && (
              <div
                style={{
                  backgroundColor: 'rgba(245,166,35,0.85)',
                  color: '#fff',
                  fontFamily: 'Barlow Condensed, Oswald, sans-serif',
                  fontSize: 16,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.8px',
                  padding: '3px 14px',
                }}
              >
                {named_entity.description}
              </div>
            )}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
