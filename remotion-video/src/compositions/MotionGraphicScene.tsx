import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export interface MotionGraphicSceneProps {
  motion_style?: 'pulse' | 'lines' | 'grid' | 'particles' | 'counter' | 'slash';
  accent_color?: string;
  label?: string;
  counter_value?: number;
  counter_unit?: string;
  durationInFrames: number;
}

// ─── Pulse Style ─────────────────────────────────────────────────────────────
const PulseMotion: React.FC<{ frame: number; fps: number; color: string; label?: string }> = ({
  frame, fps, color, label,
}) => {
  const rings = [0, 6, 12, 18, 24];
  return (
    <AbsoluteFill style={{ backgroundColor: '#06060F', alignItems: 'center', justifyContent: 'center' }}>
      {rings.map((delay, i) => {
        const p = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 20, stiffness: 60 } });
        const scale = 0.3 + p * (0.9 + i * 0.25);
        const opacity = interpolate(p, [0, 0.3, 1], [0, 0.6, 0], { extrapolateRight: 'clamp' });
        return (
          <div key={i} style={{
            position: 'absolute',
            width: 300,
            height: 300,
            borderRadius: '50%',
            border: `${3 - i * 0.4}px solid ${color}`,
            opacity,
            transform: `scale(${scale})`,
          }} />
        );
      })}
      {/* Core dot */}
      <div style={{
        width: 30,
        height: 30,
        borderRadius: '50%',
        backgroundColor: color,
        boxShadow: `0 0 40px ${color}, 0 0 80px ${color}66`,
        opacity: spring({ frame, fps, config: { damping: 10, stiffness: 80 } }),
      }} />
      {label && (
        <div style={{
          position: 'absolute',
          bottom: '20%',
          color: '#fff',
          fontFamily: 'Barlow Condensed, sans-serif',
          fontSize: 38,
          fontWeight: 700,
          letterSpacing: 6,
          textTransform: 'uppercase',
          opacity: interpolate(frame, [15, 25], [0, 1], { extrapolateRight: 'clamp' }),
          textShadow: `0 0 20px ${color}`,
        }}>
          {label}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ─── Lines Style ─────────────────────────────────────────────────────────────
const LinesMotion: React.FC<{ frame: number; fps: number; color: string; label?: string }> = ({
  frame, fps, color, label,
}) => {
  const lines = [
    { y: '15%', delay: 0, width: 65 },
    { y: '28%', delay: 3, width: 45 },
    { y: '42%', delay: 6, width: 85 },
    { y: '57%', delay: 9, width: 55 },
    { y: '71%', delay: 12, width: 70 },
    { y: '84%', delay: 15, width: 40 },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: '#060610', overflow: 'hidden' }}>
      {/* Diagonal accent */}
      <div style={{
        position: 'absolute',
        right: 0,
        top: 0,
        width: '40%',
        height: '100%',
        background: `linear-gradient(135deg, transparent 40%, ${color}18 100%)`,
      }} />

      {lines.map((line, i) => {
        const p = spring({ frame: Math.max(0, frame - line.delay), fps, config: { damping: 14, stiffness: 90 } });
        return (
          <div key={i} style={{
            position: 'absolute',
            left: '8%',
            top: line.y,
            width: `${line.width * p}%`,
            height: i % 2 === 0 ? 3 : 1.5,
            backgroundColor: i === 2 ? color : `${color}55`,
            borderRadius: 2,
            boxShadow: i === 2 ? `0 0 12px ${color}` : 'none',
          }} />
        );
      })}

      {label && (
        <div style={{
          position: 'absolute',
          left: '8%',
          top: '38%',
          color: '#fff',
          fontFamily: 'Barlow Condensed, sans-serif',
          fontSize: 52,
          fontWeight: 800,
          textTransform: 'uppercase',
          letterSpacing: 4,
          opacity: interpolate(frame, [20, 32], [0, 1], { extrapolateRight: 'clamp' }),
          transform: `translateX(${interpolate(frame, [20, 32], [-40, 0], { extrapolateRight: 'clamp' })}px)`,
        }}>
          {label}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ─── Grid Style ──────────────────────────────────────────────────────────────
const GridMotion: React.FC<{ frame: number; fps: number; color: string; label?: string }> = ({
  frame, fps, color, label,
}) => {
  const gridOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
  const scanY = interpolate(frame, [0, 60], ['-10%', '110%'], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ backgroundColor: '#040410', overflow: 'hidden' }}>
      {/* Grid */}
      <div style={{
        position: 'absolute',
        inset: 0,
        opacity: gridOpacity * 0.25,
        backgroundImage: `
          linear-gradient(${color}66 1px, transparent 1px),
          linear-gradient(90deg, ${color}66 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px',
      }} />

      {/* Scan line */}
      <div style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: scanY,
        height: 2,
        background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
        boxShadow: `0 0 20px ${color}`,
      }} />

      {/* Corner brackets */}
      {[
        { top: '15%', left: '10%', borderTop: true, borderLeft: true },
        { top: '15%', right: '10%', borderTop: true, borderRight: true },
        { bottom: '15%', left: '10%', borderBottom: true, borderLeft: true },
        { bottom: '15%', right: '10%', borderBottom: true, borderRight: true },
      ].map((corner, i) => {
        const p = spring({ frame: Math.max(0, frame - i * 4), fps, config: { damping: 15, stiffness: 120 } });
        const { borderTop, borderLeft, borderRight, borderBottom, ...pos } = corner;
        return (
          <div key={i} style={{
            position: 'absolute',
            ...pos,
            width: 40 * p,
            height: 40 * p,
            borderTop: borderTop ? `2px solid ${color}` : 'none',
            borderLeft: borderLeft ? `2px solid ${color}` : 'none',
            borderRight: borderRight ? `2px solid ${color}` : 'none',
            borderBottom: borderBottom ? `2px solid ${color}` : 'none',
            opacity: p,
          }} />
        );
      })}

      {label && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          color: color,
          fontFamily: 'Barlow Condensed, monospace',
          fontSize: 44,
          fontWeight: 700,
          letterSpacing: 10,
          textTransform: 'uppercase',
          opacity: interpolate(frame, [18, 28], [0, 1], { extrapolateRight: 'clamp' }),
          textShadow: `0 0 20px ${color}`,
        }}>
          {label}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ─── Counter Style ────────────────────────────────────────────────────────────
const CounterMotion: React.FC<{
  frame: number; fps: number; color: string; label?: string;
  counter_value?: number; counter_unit?: string; durationInFrames: number;
}> = ({ frame, fps, color, label, counter_value = 100, counter_unit = '', durationInFrames }) => {
  const p = interpolate(frame, [10, durationInFrames - 10], [0, 1], { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' });
  const displayed = Math.round(p * counter_value);
  const labelOpacity = interpolate(frame, [5, 15], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ backgroundColor: '#080812', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
      {/* Background glow */}
      <div style={{
        position: 'absolute',
        width: 500,
        height: 500,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${color}22 0%, transparent 70%)`,
      }} />

      {label && (
        <div style={{
          color: '#AAA',
          fontFamily: 'Barlow Condensed, sans-serif',
          fontSize: 30,
          fontWeight: 600,
          letterSpacing: 8,
          textTransform: 'uppercase',
          marginBottom: 20,
          opacity: labelOpacity,
        }}>
          {label}
        </div>
      )}

      <div style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 12,
      }}>
        <span style={{
          color: '#fff',
          fontFamily: 'Barlow Condensed, sans-serif',
          fontSize: 160,
          fontWeight: 900,
          lineHeight: 1,
          textShadow: `0 0 40px ${color}99`,
          letterSpacing: -4,
        }}>
          {displayed.toLocaleString()}
        </span>
        {counter_unit && (
          <span style={{
            color: color,
            fontFamily: 'Barlow Condensed, sans-serif',
            fontSize: 50,
            fontWeight: 700,
            textTransform: 'uppercase',
            opacity: labelOpacity,
          }}>
            {counter_unit}
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div style={{
        width: '50%',
        height: 4,
        backgroundColor: '#333',
        borderRadius: 2,
        marginTop: 30,
        overflow: 'hidden',
        opacity: labelOpacity,
      }}>
        <div style={{
          width: `${p * 100}%`,
          height: '100%',
          backgroundColor: color,
          boxShadow: `0 0 12px ${color}`,
          borderRadius: 2,
          transition: 'width 0.05s',
        }} />
      </div>
    </AbsoluteFill>
  );
};

// ─── Slash Style ─────────────────────────────────────────────────────────────
const SlashMotion: React.FC<{ frame: number; fps: number; color: string; label?: string }> = ({
  frame, fps, color, label,
}) => {
  const slashP = spring({ frame: Math.max(0, frame - 2), fps, config: { damping: 12, stiffness: 120 } });
  const labelP = spring({ frame: Math.max(0, frame - 10), fps, config: { damping: 14, stiffness: 100 } });

  return (
    <AbsoluteFill style={{ backgroundColor: '#050510', overflow: 'hidden' }}>
      {/* Primary slash */}
      <div style={{
        position: 'absolute',
        left: '-5%',
        top: 0,
        width: `${slashP * 110}%`,
        height: '100%',
        background: `linear-gradient(90deg, transparent, ${color}33 40%, ${color}55 50%, ${color}33 60%, transparent)`,
        transform: 'skewX(-12deg)',
      }} />

      {/* Accent slash */}
      <div style={{
        position: 'absolute',
        left: '20%',
        top: 0,
        width: `${spring({ frame: Math.max(0, frame - 5), fps, config: { damping: 12, stiffness: 100 } }) * 60}%`,
        height: 4,
        backgroundColor: color,
        top: '48%',
        boxShadow: `0 0 16px ${color}`,
      }} />

      {label && (
        <div style={{
          position: 'absolute',
          left: '8%',
          top: '35%',
          color: '#fff',
          fontFamily: 'Barlow Condensed, sans-serif',
          fontSize: 64,
          fontWeight: 900,
          textTransform: 'uppercase',
          letterSpacing: 2,
          opacity: labelP,
          transform: `translateY(${(1 - labelP) * 30}px)`,
          textShadow: '0 2px 20px rgba(0,0,0,0.8)',
        }}>
          {label}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ─── Main Component ───────────────────────────────────────────────────────────
export const MotionGraphicScene: React.FC<MotionGraphicSceneProps> = ({
  motion_style = 'lines',
  accent_color = '#F5A623',
  label,
  counter_value,
  counter_unit,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeOut = interpolate(frame, [durationInFrames - 8, durationInFrames], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  const content = (() => {
    switch (motion_style) {
      case 'pulse':
        return <PulseMotion frame={frame} fps={fps} color={accent_color} label={label} />;
      case 'grid':
        return <GridMotion frame={frame} fps={fps} color={accent_color} label={label} />;
      case 'counter':
        return (
          <CounterMotion
            frame={frame} fps={fps} color={accent_color} label={label}
            counter_value={counter_value} counter_unit={counter_unit}
            durationInFrames={durationInFrames}
          />
        );
      case 'slash':
        return <SlashMotion frame={frame} fps={fps} color={accent_color} label={label} />;
      case 'lines':
      default:
        return <LinesMotion frame={frame} fps={fps} color={accent_color} label={label} />;
    }
  })();

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      {content}
    </AbsoluteFill>
  );
};
