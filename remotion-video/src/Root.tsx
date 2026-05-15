import { Composition, getInputProps } from 'remotion';
import { MainVideo, MainVideoProps } from './compositions/MainVideo';
import { Main } from './Main';
import './style.css';

export const RemotionRoot: React.FC = () => {
  const inputProps = (getInputProps() as unknown) as MainVideoProps & { segments?: any[] };
  
  // Calculate total duration for long form
  const CHAPTER_INTRO_DURATION = 96; // 4 seconds at 24fps
  let totalDuration = 0;
  
  if (inputProps.chapters) {
    inputProps.chapters.forEach(chapter => {
      totalDuration += CHAPTER_INTRO_DURATION + chapter.duration_in_frames;
    });
  }

  if (inputProps.quiz) {
    totalDuration += 10 * 24; // 10 seconds at 24fps
  }

  // Calculate total duration for shorts
  let shortDuration = 0;
  if (inputProps.segments) {
    inputProps.segments.forEach(seg => {
      shortDuration += Math.max(1, Math.round(seg.duration * 24));
    });
  }

  return (
    <>
      <Composition
        id="MainVideo"
        component={MainVideo as any}
        durationInFrames={Math.max(1, totalDuration)}
        fps={24}
        width={1920}
        height={1080}
        defaultProps={{
          chapters: [],
          background_music: '',
          image_credits: []
        } as MainVideoProps}
      />
      <Composition
        id="Main"
        component={Main as any}
        durationInFrames={Math.max(1, shortDuration)}
        fps={24}
        width={1080}
        height={1920}
        defaultProps={{
          title_card: '',
          profile_image: '',
          background_music: '',
          segments: []
        }}
      />
    </>
  );
};
