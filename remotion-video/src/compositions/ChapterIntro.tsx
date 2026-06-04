import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, spring } from 'remotion';

interface ChapterIntroProps {
  number: number;
  title: string;
  durationInFrames?: number;
}

export const ChapterIntro: React.FC<ChapterIntroProps> = ({ number, title, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const totalFrames = durationInFrames || (4 * fps); // Default to 4 seconds (96 frames at 24fps)

  // 1. Black frame for first 6 frames, then line sweeps across
  const lineProgress = interpolate(frame, [6, 18], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });
  
  // 2. "CHAPTER X" text slams in from top (frames 12-20)
  const chapterScale = spring({
    frame: frame - 12,
    fps,
    config: { damping: 12, stiffness: 200 },
  });
  
  // 3. Title fades in below (frames 20-30)
  const titleOpacity = interpolate(frame, [20, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  
  // 4. Fade to black on last 8 frames
  const fadeOut = interpolate(frame, [totalFrames - 8, totalFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0A12", opacity: fadeOut, justifyContent: 'center', alignItems: 'center' }}>
      {/* Amber sweep line */}
      <div style={{
        position: "absolute",
        top: "45%",
        left: 0,
        width: `${lineProgress * 100}%`,
        height: 3,
        backgroundColor: "#F5A623"
      }} />
      
      {/* CHAPTER X */}
      <div style={{
        position: "absolute",
        top: "32%",
        left: "50%",
        transform: `translateX(-50%) scale(${chapterScale})`,
        color: "#F5A623",
        fontSize: 36,
        fontFamily: "Barlow Condensed, sans-serif",
        fontWeight: 700,
        letterSpacing: 8,
        textTransform: "uppercase",
        opacity: frame >= 12 ? 1 : 0,
      }}>
        Chapter {number}
      </div>
      
      {/* Chapter title */}
      <div style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translateX(-50%)",
        opacity: titleOpacity,
        color: "#FFFFFF",
        fontSize: 56,
        fontFamily: "Barlow Condensed, sans-serif",
        fontWeight: 700,
        textAlign: "center",
        maxWidth: 1000,
        textTransform: "uppercase",
      }}>
        {title}
      </div>
    </AbsoluteFill>
  );
};
