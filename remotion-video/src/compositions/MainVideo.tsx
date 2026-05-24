import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import { ChapterIntro } from './ChapterIntro';
import { QuizSlide } from './QuizSlide';
import { TypewriterScene } from './TypewriterScene';
import { KineticStatScene } from './KineticStatScene';
import { ImageScene } from './ImageScene';
import { AIVideoScene } from './AIVideoScene';
import { HookQuestionScene } from './HookQuestionScene';
import { DataBarsScene } from './DataBarsScene';
import { DataVisualizationScene } from './DataVisualizationScene';
import { Chapter, MainVideoProps, VisualScene } from '../types';

const SFX_ROTATION = ['whoosh', 'transition', 'rise', 'impact', 'drum'];

// A simple flash transition component
const FlashTransition: React.FC<{ durationInFrames: number }> = ({ durationInFrames }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: 'white', opacity: 1 }} />
  );
};

export const MainVideo: React.FC<MainVideoProps> = ({
  chapters,
  background_music,
  quiz,
  sound_effects = {},
}) => {
  const { fps } = useVideoConfig();

  let currentFrame = 0;
  const CHAPTER_INTRO_DURATION = 4 * fps; // 4 seconds

  let globalImageIndex = 0;
  let sfxIndex = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: '#0a0a0a' }}>
      {/* Background Music — quiet underneath narration */}
      {background_music && (
        <Audio
          src={staticFile(background_music)}
          volume={() => 0.06}
        />
      )}

      {chapters.map((chapter, index) => {
        const chapterStartTime = currentFrame;

        // 1. Chapter Intro (4s) + whoosh sound
        const chapterSfxCategory = SFX_ROTATION[sfxIndex % SFX_ROTATION.length];
        const chapterSfxPath = sound_effects[chapterSfxCategory];
        sfxIndex++;

        const introSequence = (
          <React.Fragment key={`intro-frag-${index}`}>
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
            {chapterSfxPath && (
              <Sequence
                key={`sfx-chapter-${index}`}
                from={chapterStartTime}
                durationInFrames={24}
              >
                <Audio src={staticFile(chapterSfxPath)} volume={() => 0.45} />
              </Sequence>
            )}
          </React.Fragment>
        );

        currentFrame += CHAPTER_INTRO_DURATION;

        // 2. Visual Scenes
        const chapterContentDuration = chapter.duration_in_frames;
        
        let visualContent: React.ReactNode = null;
        
        if (chapter.visual_scenes && chapter.visual_scenes.length > 0) {
           const scenes = chapter.visual_scenes;
           const transitionSeriesChildren: React.ReactNode[] = [];
           
           for (let i = 0; i < scenes.length; i++) {
             const scene = scenes[i];
             const sceneDuration = scene.duration_frames;
             const isLast = i === scenes.length - 1;
             
             let sceneComponent: React.ReactNode = null;
             
              if (scene.visual_type === 'typewriter_text') {
               sceneComponent = (
                 <TypewriterScene 
                   typewriter_words={scene.typewriter_words || []} 
                   word_timestamps={scene.word_timestamps || []}
                   durationInFrames={sceneDuration}
                 />
               );
             } else if (scene.visual_type === 'kinetic_stat') {
               sceneComponent = (
                 <KineticStatScene 
                   stat_data={scene.stat_data || { value: 0, unit: '', label: '' }}
                   durationInFrames={sceneDuration}
                 />
               );
             } else if (scene.visual_type === 'hook_question') {
               sceneComponent = (
                 <HookQuestionScene 
                   question_text={scene.question_text || ''}
                   emphasis_phrase={scene.emphasis_phrase || ''}
                   durationInFrames={sceneDuration}
                 />
               );
             } else if (scene.visual_type === 'data_bars') {
               sceneComponent = (
                 <DataBarsScene 
                   title="Comparison"
                   bars={(scene.bar_data || []).map(b => ({ ...b, color: b.color as any }))}
                   durationInFrames={sceneDuration}
                 />
               );
             } else if (scene.visual_type === 'data_visualization') {
               sceneComponent = (
                 <DataVisualizationScene 
                   title={scene.caption || 'DATA VIZ'}
                   chartType={(scene.chart_type as any) || 'bar_chart'}
                   data={scene.bar_data || []}
                 />
               );
             } else if (scene.visual_type === 'ai_video') {
               sceneComponent = (
                 <AIVideoScene 
                   assetPath={scene.asset_path || ''}
                   assetType={scene.asset_type || 'image_fallback'}
                   durationInFrames={sceneDuration}
                   aiLabel="AI GENERATED"
                 />
               );
             } else {
               // default to image
               sceneComponent = (
                 <ImageScene 
                   assetPath={scene.asset_path || 'assets/images/placeholder.jpg'}
                   durationInFrames={sceneDuration}
                   kenBurnsStyle={(scene.ken_burns_style as any) || 'zoom_in_center'}
                   namedEntity={scene.named_entity}
                   caption={scene.caption}
                 />
               );
             }

             // Handle Transitions
             if (scene.transition === 'flash' && i > 0) {
               transitionSeriesChildren.push(
                 <TransitionSeries.Transition
                   key={`trans-${index}-${i}`}
                   presentation={fade()}
                   timing={linearTiming({ durationInFrames: 6 })}
                 />
               );
             } else if (scene.transition === 'fade' && i > 0) {
               transitionSeriesChildren.push(
                 <TransitionSeries.Transition
                   key={`trans-${index}-${i}`}
                   presentation={fade()}
                   timing={linearTiming({ durationInFrames: 15 })}
                 />
               );
             }
             
             // In TransitionSeries, Sequence is a wrapper around the component
             transitionSeriesChildren.push(
               <TransitionSeries.Sequence key={`scene-${index}-${i}`} durationInFrames={sceneDuration}>
                 {sceneComponent}
                 {/* Play sound effect on transitions except first */}
                 {i > 0 && sound_effects[SFX_ROTATION[sfxIndex % SFX_ROTATION.length]] && (
                    <Sequence from={0} durationInFrames={18}>
                      <Audio src={staticFile(sound_effects[SFX_ROTATION[sfxIndex % SFX_ROTATION.length]])} volume={() => 0.25} />
                    </Sequence>
                 )}
               </TransitionSeries.Sequence>
             );
             
             if (i > 0) sfxIndex++;
           }
           
           visualContent = (
             <Sequence from={currentFrame} durationInFrames={chapterContentDuration}>
               <TransitionSeries>
                 {transitionSeriesChildren}
               </TransitionSeries>
             </Sequence>
           );
        } else {
           // Fallback to legacy image logic
           const imagesArr = chapter.images && chapter.images.length > 0 ? chapter.images : ['assets/images/placeholder.jpg'];
           const framesPerImage = Math.min(Math.floor(chapterContentDuration / imagesArr.length), 72);
           
           let remaining = chapterContentDuration;
           let slideFrame = currentFrame;
           let imgIdx = 0;
           const slides: React.ReactNode[] = [];
           
           while (remaining > 0) {
             const img = imagesArr[imgIdx % imagesArr.length];
             const duration = Math.min(framesPerImage, remaining);
             const effectIdx = globalImageIndex % 5;
             const isFirstSlide = imgIdx === 0 && index === 0;
             const sfxCat = SFX_ROTATION[sfxIndex % SFX_ROTATION.length];
             const sfxPath = sound_effects[sfxCat];
             sfxIndex++;
             
             slides.push(
               <React.Fragment key={`slide-frag-${index}-${imgIdx}`}>
                 <Sequence from={slideFrame} durationInFrames={duration}>
                   <ImageScene assetPath={img} durationInFrames={duration} ken_burns_style="zoom_in_center" />
                 </Sequence>
                 {sfxPath && !isFirstSlide && (
                   <Sequence from={slideFrame} durationInFrames={18}>
                     <Audio src={staticFile(sfxPath)} volume={() => 0.25} />
                   </Sequence>
                 )}
               </React.Fragment>
             );
             slideFrame += duration;
             remaining -= duration;
             imgIdx++;
             globalImageIndex++;
           }
           visualContent = slides;
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
            {visualContent}
            {narration}
          </React.Fragment>
        );
      })}

      {/* Interactive Quiz at the end */}
      {quiz && (
        <Sequence from={currentFrame} durationInFrames={10 * fps}>
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
