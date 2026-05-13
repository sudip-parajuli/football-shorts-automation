import { Composition, getInputProps } from 'remotion';
import { MainVideo, MainVideoProps } from './compositions/MainVideo';
import './style.css';

export const RemotionRoot: React.FC = () => {
  const inputProps = (getInputProps() as unknown) as MainVideoProps;
  
  // Calculate total duration
  const CHAPTER_INTRO_DURATION = 48; // 2 seconds at 24fps
  let totalDuration = 0;
  
  if (inputProps.chapters) {
    inputProps.chapters.forEach(chapter => {
      totalDuration += CHAPTER_INTRO_DURATION + chapter.duration_in_frames;
    });
  }

  if (inputProps.quiz) {
    totalDuration += 10 * 24; // 10 seconds at 24fps
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
    </>
  );
};
