import { Composition } from 'remotion';
import { Main, MainSchema } from './Main';
import './style.css';
import { loadFont } from '@remotion/google-fonts/Montserrat';

loadFont();


// Try to load generated props; if missing, provide a fallback.
let generatedProps: any = {};
try {
  generatedProps = require('../props.json');
} catch (e) {
  generatedProps = {
    title_card: '',
    profile_image: '',
    background_music: '',
    segments: [
      {
        type: 'hook',
        text: 'Welcome to FootyBitez',
        start: 0,
        duration: 5,
        media: [''],
        timing: [],
      },
    ]
  };
}

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="Main"
				component={Main}
				durationInFrames={300} // Dynamic in run-time
				fps={30}
				width={1080}
				height={1920}
				schema={MainSchema}
				defaultProps={generatedProps}
        calculateMetadata={({ props }) => {
          let totalDurationExSeconds = 0;
          for (const seg of props.segments) {
              totalDurationExSeconds += seg.duration;
          }
          if (totalDurationExSeconds === 0) totalDurationExSeconds = 10;
          
          let baseDuration = Math.round(totalDurationExSeconds * 30);
          
          // Compensate for Transition overlaps
          const TRANSITION_FRAMES = 15;
          const numTransitions = Math.max(0, props.segments.length - 1);
          let actualDurationInFrames = baseDuration - (numTransitions * TRANSITION_FRAMES);

          return {
             durationInFrames: Math.max(1, actualDurationInFrames),
             props
          };
        }}
			/>
			<Composition
				id="LongForm"
				component={Main}
				durationInFrames={300} // Dynamic in run-time
				fps={30}
				width={1920}
				height={1080}
				schema={MainSchema}
				defaultProps={generatedProps}
        calculateMetadata={({ props }) => {
          let totalDurationExSeconds = 0;
          for (const seg of props.segments) {
              totalDurationExSeconds += seg.duration;
          }
          if (totalDurationExSeconds === 0) totalDurationExSeconds = 10;
          
          let baseDuration = Math.round(totalDurationExSeconds * 30);
          
          const TRANSITION_FRAMES = 15;
          const numTransitions = Math.max(0, props.segments.length - 1);
          let actualDurationInFrames = baseDuration - (numTransitions * TRANSITION_FRAMES);

          return {
             durationInFrames: Math.max(1, actualDurationInFrames),
             props
          };
        }}
			/>
		</>
	);
};
