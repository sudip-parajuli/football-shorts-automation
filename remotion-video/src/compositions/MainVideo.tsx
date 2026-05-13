import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from 'remotion';
import { ChapterIntro } from './ChapterIntro';
import { ImageSlide } from './ImageSlide';

export interface Chapter {
  chapter_number: number;
  chapter_title: string;
  script: string;
  duration_in_frames: number;
  audio_path: string;
  images: string[];
}

export interface MainVideoProps {
  chapters: Chapter[];
  background_music: string;
  image_credits: string[];
}

export const MainVideo: React.FC<MainVideoProps> = ({ 
  chapters, 
  background_music 
}) => {
  const { fps } = useVideoConfig();
  
  let currentFrame = 0;
  const CHAPTER_INTRO_DURATION = 2 * fps; // 2 seconds

  return (
    <AbsoluteFill style={{ backgroundColor: '#0a0a0a' }}>
      {/* Background Music */}
      {background_music && (
        <Audio 
          src={staticFile(background_music)} 
          volume={(f) => {
            // Audio ducking logic: -18dB base
            return 0.12; 
          }}
        />
      )}

      {chapters.map((chapter, index) => {
        const chapterStartTime = currentFrame;
        
        // 1. Chapter Intro
        const introSequence = (
          <Sequence 
            key={`intro-${index}`} 
            from={chapterStartTime} 
            durationInFrames={CHAPTER_INTRO_DURATION}
          >
            <ChapterIntro 
              number={chapter.chapter_number} 
              title={chapter.chapter_title} 
            />
          </Sequence>
        );
        
        currentFrame += CHAPTER_INTRO_DURATION;
        
        // 2. Chapter Content (Slides)
        // For simplicity in this example, we assume one image per chapter or split logic
        // The real implementation would split script by cues.
        // For now, let's render the chapter's images sequentially.
        const chapterContentDuration = chapter.duration_in_frames;
        const imagesCount = chapter.images.length;
        const framesPerImage = Math.floor(chapterContentDuration / imagesCount);
        
        const slides = chapter.images.map((img, imgIndex) => {
          const slideStart = currentFrame;
          const duration = imgIndex === imagesCount - 1 
            ? chapterContentDuration - (imgIndex * framesPerImage) 
            : framesPerImage;
          
          currentFrame += duration;
          
          return (
            <Sequence 
              key={`slide-${index}-${imgIndex}`} 
              from={slideStart} 
              durationInFrames={duration}
            >
              <ImageSlide src={img} durationInFrames={duration} />
            </Sequence>
          );
        });

        // 3. Chapter Narration
        const narration = (
          <Audio 
            key={`audio-${index}`}
            src={staticFile(chapter.audio_path)}
            startFrom={0}
          />
        );

        return (
          <React.Fragment key={`chapter-${index}`}>
            {introSequence}
            {slides}
            <Sequence from={chapterStartTime + CHAPTER_INTRO_DURATION} durationInFrames={chapterContentDuration}>
               {narration}
            </Sequence>
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};
