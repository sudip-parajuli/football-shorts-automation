import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from 'remotion';
import { ChapterIntro } from './ChapterIntro';
import { ImageSlide } from './ImageSlide';
import { QuizSlide } from './QuizSlide';

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
  quiz?: {
    question: string;
    options: string[];
    correct_answer_index: number;
    explanation: string;
  };
}

const MAX_FRAMES_PER_IMAGE = 72; // 3 seconds max per image at 24fps

export const MainVideo: React.FC<MainVideoProps> = ({
  chapters,
  background_music,
  quiz
}) => {
  const { fps } = useVideoConfig();

  let currentFrame = 0;
  const CHAPTER_INTRO_DURATION = 4 * fps; // 4 seconds

  // Global image counter for cycling through effects
  let globalImageIndex = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: '#0a0a0a' }}>
      {/* Background Music — quiet so narration is clear */}
      {background_music && (
        <Audio
          src={staticFile(background_music)}
          volume={() => 0.06}
        />
      )}

      {chapters.map((chapter, index) => {
        const chapterStartTime = currentFrame;

        // 1. Chapter Intro (4s)
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

        // 2. Chapter Content — images capped at MAX_FRAMES_PER_IMAGE each
        const chapterContentDuration = chapter.duration_in_frames;
        const imagesArr = chapter.images && chapter.images.length > 0
          ? chapter.images
          : ['assets/images/placeholder.jpg'];

        // Calculate how many slots we need to fill chapterContentDuration
        const framesPerImage = Math.min(
          Math.floor(chapterContentDuration / imagesArr.length),
          MAX_FRAMES_PER_IMAGE
        );

        const slides: React.ReactNode[] = [];
        let slideFrame = currentFrame;
        let remaining = chapterContentDuration;
        let imgIdx = 0;

        while (remaining > 0) {
          const img = imagesArr[imgIdx % imagesArr.length];
          const duration = Math.min(framesPerImage, remaining);
          const effectIdx = globalImageIndex % 5;
          globalImageIndex++;

          slides.push(
            <Sequence
              key={`slide-${index}-${imgIdx}`}
              from={slideFrame}
              durationInFrames={duration}
            >
              <ImageSlide src={img} durationInFrames={duration} effectIndex={effectIdx} />
            </Sequence>
          );

          slideFrame += duration;
          remaining -= duration;
          imgIdx++;
        }

        currentFrame += chapterContentDuration;

        // 3. Chapter Narration
        const narration = (
          <Sequence
            key={`audio-${index}`}
            from={chapterStartTime + CHAPTER_INTRO_DURATION}
            durationInFrames={chapterContentDuration}
          >
            <Audio src={staticFile(chapter.audio_path)} startFrom={0} />
          </Sequence>
        );

        return (
          <React.Fragment key={`chapter-${index}`}>
            {introSequence}
            {slides}
            {narration}
          </React.Fragment>
        );
      })}

      {/* Interactive Quiz at the end */}
      {quiz && (
        <Sequence
          from={currentFrame}
          durationInFrames={10 * fps}
        >
          <QuizSlide
            question={quiz.question}
            options={quiz.options}
            correct_answer_index={quiz.correct_answer_index}
            explanation={quiz.explanation}
          />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};
