import {EditorialGraphic} from './EditorialGraphic';
import {SpokenCaptions} from '../SpokenCaptions';
import { cleanDisplayFields } from '../displayText';
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
import { MotionGraphicScene } from './MotionGraphicScene';
import { Chapter, MainVideoProps, VisualScene } from '../types';


// Ken Burns styles cycle — ensures consecutive images never repeat the same style
const KB_STYLES = [
  'zoom_in_center',
  'pan_left',
  'zoom_out_center',
  'pan_right',
  'zoom_in_topleft',
  'pan_diagonal',
  'tilt_up',
  'tilt_down',
];

// Cinematic bar letterbox overlay (adds cinematic top/bottom bars on image scenes)
const CinematicBars: React.FC = () => (
  <>
    <div style={{
      position: 'absolute', top: 0, left: 0, right: 0, height: 30,
      backgroundColor: '#000', zIndex: 10, pointerEvents: 'none',
    }} />
    <div style={{
      position: 'absolute', bottom: 0, left: 0, right: 0, height: 30,
      backgroundColor: '#000', zIndex: 10, pointerEvents: 'none',
    }} />
  </>
);

export const MainVideo: React.FC<MainVideoProps> = ({
  chapters,
  background_music,
  quiz,
  sound_effects = {},
}) => {
  const { fps } = useVideoConfig();
  chapters = cleanDisplayFields(chapters);
  quiz = cleanDisplayFields(quiz);

  let currentFrame = 0;


  let globalKbIndex = 0; // Global index for Ken Burns cycling across all scenes

  return (
    <AbsoluteFill style={{ backgroundColor: '#0a0a0a' }}>
      {/* Background Music */}
      {background_music && (
        <Audio
          src={staticFile(background_music)}
          loop
          volume={() => 0.04}
        />
      )}

      {chapters.map((chapter, chapterIdx) => {
        const CHAPTER_INTRO_DURATION = chapterIdx === 0 ? 0 : fps;
        const chapterStartTime = currentFrame;

        // ── Chapter Intro ───────────────────────────────────────────────────
        const chapterSfxPath = sound_effects['chapter'];

        const introSequence = CHAPTER_INTRO_DURATION > 0 ? (
          <React.Fragment key={`intro-frag-${chapterIdx}`}>
            <Sequence
              key={`intro-${chapterIdx}`}
              from={chapterStartTime}
              durationInFrames={CHAPTER_INTRO_DURATION}
            >
              <ChapterIntro
                number={chapter.chapter_number}
                title={chapter.chapter_title}
                durationInFrames={CHAPTER_INTRO_DURATION}
              />
            </Sequence>
            {chapterSfxPath && (
              <Sequence
                key={`sfx-chapter-${chapterIdx}`}
                from={chapterStartTime}
                durationInFrames={24}
              >
                <Audio src={staticFile(chapterSfxPath)} volume={() => 0.14} />
              </Sequence>
            )}
          </React.Fragment>
        ) : null;

        currentFrame += CHAPTER_INTRO_DURATION;

        // ── Visual Scenes ───────────────────────────────────────────────────
        const chapterContentDuration = chapter.duration_in_frames;
        let visualContent: React.ReactNode = null;

        if (chapter.visual_scenes && chapter.visual_scenes.length > 0) {
          const scenes = chapter.visual_scenes;
          const transitionChildren: React.ReactNode[] = [];

          let sceneStart=0;
          for (let i = 0; i < scenes.length; i++) {
            const scene = scenes[i];
            const sceneDuration = scene.duration_frames;

            // Auto-cycle Ken Burns for image-type scenes so consecutive images always differ
            const isImageType = scene.visual_type === 'image' || scene.visual_type === 'image_tag' || scene.visual_type === 'ai_video';
            let kbStyle = scene.ken_burns_style;
            if (isImageType && !kbStyle) {
              kbStyle = KB_STYLES[globalKbIndex % KB_STYLES.length];
              globalKbIndex++;
            } else if (isImageType) {
              globalKbIndex++; // Still advance index for next scene
            }

            let sceneComponent: React.ReactNode = null;

            // ── Scene type routing ────────────────────────────────────────
            if (scene.visual_type === 'editorial_graphic' && scene.graphic) {
              const timing=chapter.timing?.filter(word=>word.start>=sceneStart/fps && word.start<(sceneStart+sceneDuration)/fps).map(word=>({...word,start:word.start-sceneStart/fps}));
              sceneComponent = <EditorialGraphic brief={scene.graphic} durationInFrames={sceneDuration} timing={timing}/>;
            } else if (scene.visual_type === 'typewriter_text') {
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
                  bar_data={(scene.bar_data || []).map(b => ({ ...b, color: b.color as any }))}
                  durationInFrames={sceneDuration}
                />
              );
            } else if (
              scene.visual_type === 'data_visualization' ||
              scene.visual_type === 'leaderboard' ||
              scene.visual_type === 'head_to_head' ||
              scene.visual_type === 'timeline'
            ) {
              sceneComponent = (
                <DataVisualizationScene
                  title={scene.caption || 'DATA VIZ'}
                  chartType={(scene.visual_type === 'data_visualization' ? scene.chart_type : scene.visual_type) as any || 'bar_chart'}
                  data={scene.bar_data || []}
                  leaderboard_data={scene.leaderboard_data}
                  head_to_head_data={scene.head_to_head_data}
                  timeline_data={scene.timeline_data}
                  timeline_title={scene.timeline_title}
                />
              );
            } else if (scene.visual_type === 'motion_graphic') {
              sceneComponent = (
                <MotionGraphicScene
                  motion_style={scene.motion_style || 'lines'}
                  club_logos={scene.club_logos}
                  accent_color={scene.accent_color || '#F5A623'}
                  label={scene.motion_label || scene.caption}
                  counter_value={scene.counter_value}
                  counter_unit={scene.counter_unit}
                  durationInFrames={sceneDuration}
                />
              );
            } else if (scene.visual_type === 'ai_video') {
              const aiAssetType = scene.asset_type === 'image' ? 'image_fallback' : scene.asset_type || 'image_fallback';
              sceneComponent = (
                <AIVideoScene
                  assetPath={scene.asset_path || ''}
                  assetType={aiAssetType}
                  durationInFrames={sceneDuration}
                  aiLabel="AI GENERATED"
                />
              );
            } else {
              // image, image_tag, or default
              sceneComponent = (
                <>
                  <ImageScene
                    assetPath={scene.asset_path || 'assets/images/placeholder.jpg'}
                    durationInFrames={sceneDuration}
                    ken_burns_style={kbStyle || 'zoom_in_center'}
                    named_entity={scene.named_entity}
                    caption={scene.caption}
                    secondary_asset_path={scene.secondary_asset_path}
                  />
                  <CinematicBars />
                </>
              );
            }

            sceneStart+=sceneDuration;
            // Hard cuts preserve the exact narration timeline. TransitionSeries
            // overlaps shorten coverage and used to leave the end of chapters blank.

            transitionChildren.push(
              <TransitionSeries.Sequence key={`scene-${chapterIdx}-${i}`} durationInFrames={sceneDuration}>
                {sceneComponent}

              </TransitionSeries.Sequence>
            );
          }

          visualContent = (
            <Sequence from={currentFrame} durationInFrames={chapterContentDuration}>
              <TransitionSeries>
                {transitionChildren}
              </TransitionSeries>
            </Sequence>
          );

        } else {
          // ── Legacy fallback: image list ─────────────────────────────────
          const imagesArr = chapter.images && chapter.images.length > 0
            ? chapter.images
            : ['assets/images/placeholder.jpg'];

          // Hard-cap: never show one image > 96 frames (4s at 24fps)
          const MAX_FRAMES_PER_IMAGE = 96;
          const framesPerImage = Math.min(
            Math.floor(chapterContentDuration / imagesArr.length),
            MAX_FRAMES_PER_IMAGE
          );

          let remaining = chapterContentDuration;
          let slideFrame = currentFrame;
          let imgIdx = 0;
          const slides: React.ReactNode[] = [];

          while (remaining > 0) {
            const img = imagesArr[imgIdx % imagesArr.length];
            const duration = Math.min(framesPerImage, remaining);
            const kbStyle = KB_STYLES[globalKbIndex % KB_STYLES.length];
            globalKbIndex++;

            slides.push(
              <React.Fragment key={`slide-frag-${chapterIdx}-${imgIdx}`}>
                <Sequence from={slideFrame} durationInFrames={duration}>
                  <ImageScene
                    assetPath={img}
                    durationInFrames={duration}
                    ken_burns_style={kbStyle}
                  />
                  <CinematicBars />
                </Sequence>

              </React.Fragment>
            );
            slideFrame += duration;
            remaining -= duration;
            imgIdx++;
          }
          visualContent = slides;
        }

        currentFrame += chapterContentDuration;

        // ── Chapter Narration ───────────────────────────────────────────────
        const narration = (
          <Sequence
            key={`audio-${chapterIdx}`}
            from={chapterStartTime + CHAPTER_INTRO_DURATION}
            durationInFrames={chapterContentDuration}
          >
            <Audio src={staticFile(chapter.audio_path)} startFrom={0} />
          </Sequence>
        );

        return (
          <React.Fragment key={`chapter-${chapterIdx}`}>
            {introSequence}
            {visualContent}
            {narration}
            {chapter.timing?.length ? <Sequence from={chapterStartTime+CHAPTER_INTRO_DURATION} durationInFrames={chapterContentDuration}>
              <SpokenCaptions timing={chapter.timing}/>
            </Sequence> : null}
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
