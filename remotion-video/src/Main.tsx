import { AbsoluteFill, Audio, Img, Sequence, useVideoConfig, spring, useCurrentFrame, interpolate, staticFile, Video } from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import { slide } from '@remotion/transitions/slide';
import { useWindowedAudioData, visualizeAudioWaveform, createSmoothSvgPath } from '@remotion/media-utils';
import { z } from 'zod';
import React, { useMemo } from 'react';

// SCHEMAS
export const WordTimingSchema = z.object({
  word: z.string(),
  start: z.number(),
  duration: z.number(),
});

// CUSTOM TRANSITION OVERLAY
const TransitionOverlay: React.FC<{ children: React.ReactNode, isFirst: boolean, duration: number, type: 'fade' | 'slide', direction?: 'top' | 'right' }> = ({ children, isFirst, duration, type, direction }) => {
   const frame = useCurrentFrame();
   const { width, height } = useVideoConfig();
   
   if (isFirst) return <AbsoluteFill>{children}</AbsoluteFill>;

   let style: React.CSSProperties = { position: 'absolute', width: '100%', height: '100%' };

   if (type === 'fade') {
       const opacity = interpolate(Math.min(frame, duration), [0, duration], [0, 1]);
       style.opacity = opacity;
   } else if (type === 'slide') {
       const distance = direction === 'top' ? height : width;
       const move = interpolate(Math.min(frame, duration), [0, duration], [distance, 0], { extrapolateRight: 'clamp' });
       if (direction === 'top') style.transform = `translateY(${move}px)`;
       else style.transform = `translateX(${move}px)`;
   }

   return <div style={style}>{children}</div>;
};

export const SegmentSchema = z.object({
  type: z.string(),
  text: z.string(),
  start: z.number(),
  duration: z.number(),
  media: z.array(z.string()),
  timing: z.array(WordTimingSchema),
  audio_path: z.string().optional(),
});

export const MainSchema = z.object({
  title_card: z.string(),
  profile_image: z.string(),
  background_music: z.string().optional(),
  segments: z.array(SegmentSchema),
});

type MainProps = z.infer<typeof MainSchema>;

// TIKTOK CAPTIONS COMPONENT
const TikTokCaptions: React.FC<{ timing: z.infer<typeof WordTimingSchema>[], fps: number }> = ({ timing, fps }) => {
  const frame = useCurrentFrame();

  // Group words into pages of ~4 words or split on punctuation
  const pages = useMemo(() => {
    const chunks: typeof timing[] = [];
    let currentChunk: typeof timing = [];
    
    for (const t of timing) {
      currentChunk.push(t);
      // Chunk at punctuation or max length
      if (currentChunk.length >= 4 || t.word.includes('.') || t.word.includes(',') || t.word.includes('?')) {
        chunks.push(currentChunk);
        currentChunk = [];
      }
    }
    if (currentChunk.length > 0) chunks.push(currentChunk);
    return chunks;
  }, [timing]);

  // Find active page
  let activePage = pages[0];
  for (const page of pages) {
    const firstWordMs = page[0].start;
    const lastWordMs = page[page.length - 1].start + page[page.length - 1].duration;
    
    const firstWordFrame = Math.round(firstWordMs * fps);
    const lastWordFrame = Math.round(lastWordMs * fps);
    
    if (frame >= firstWordFrame && frame <= lastWordFrame + (fps * 0.5)) { // Allow 0.5s linger
      activePage = page;
    }
  }

  if (!activePage) return null;

  return (
    <div className="absolute inset-0 flex flex-wrap justify-center content-center items-center px-12 gap-x-5 gap-y-4 text-center" style={{ fontFamily: 'Montserrat, sans-serif' }}>
      {activePage.map((t, idx) => {
        const startFrame = Math.round(t.start * fps);
        const durationFrames = Math.round(t.duration * fps);
        const endFrame = startFrame + durationFrames;
        
        const isActive = frame >= startFrame && frame < endFrame;
        const isPast = frame >= endFrame;
        const isHighlighted = t.word.includes('*');
        const displayWord = t.word.replace(/\*/g, '').toUpperCase();

        const pop = spring({
           frame: isActive ? frame - startFrame : 0,
           fps,
           config: { damping: 12, mass: 0.5, stiffness: 220 }
        });

        // Unique bold styling for highlighted words
        const baseSize = isHighlighted ? '6.5rem' : '5rem';
        const popAmount = isHighlighted ? 0.25 : 0.15;
        
        const scale = isActive ? 1 + (pop * popAmount) : 1;
        const rotation = isActive && isHighlighted ? pop * (idx % 2 === 0 ? 3 : -3) : 0;
        
        let color = 'white';
        if (isActive) {
           color = isHighlighted ? '#FDE047' : '#E5E7EB'; 
        } else if (isHighlighted) {
           color = isPast ? '#FEF08A' : 'white';
        }

        return (
          <span 
            key={idx} 
            style={{
              transform: `scale(${scale}) rotate(${rotation}deg)`,
              color,
              textShadow: '0px 10px 20px rgba(0,0,0,0.8), 0px 4px 8px rgba(0,0,0,0.6)',
              WebkitTextStroke: isHighlighted ? '4px black' : '3px black',
              fontWeight: 900,
              fontSize: baseSize,
              display: 'inline-block'
            }}
            className="transition-colors duration-100 ease-linear"
          >
            {displayWord}
          </span>
        );
      })}
    </div>
  );
};

// KEN BURNS MEDIA COMPONENT
const KenBurnsMedia: React.FC<{ src: string | null, durationInFrames: number, index: number }> = ({ src, durationInFrames, index }) => {
  const frame = useCurrentFrame();
  
  if (!src) return <AbsoluteFill className="bg-zinc-800" />;

  // Motion patterns
  const motionTypes = ['zoom-in', 'pan-right', 'zoom-out', 'pan-left'];
  const motion = motionTypes[index % motionTypes.length];
  
  let scaleX = 1;
  let scaleY = 1;
  let moveX = 0;
  
  const progress = Math.min(1, frame / durationInFrames);
  
  if (motion === 'zoom-in') {
     scaleX = interpolate(progress, [0, 1], [1, 1.15]);
     scaleY = scaleX;
  } else if (motion === 'zoom-out') {
     scaleX = interpolate(progress, [0, 1], [1.15, 1]);
     scaleY = scaleX;
  } else if (motion === 'pan-right') {
     scaleX = 1.15;
     scaleY = 1.15;
     moveX = interpolate(progress, [0, 1], [-20, 20]);
  } else if (motion === 'pan-left') {
     scaleX = 1.15;
     scaleY = 1.15;
     moveX = interpolate(progress, [0, 1], [20, -20]);
  }

  const isVideo = src.endsWith('.mp4') || src.endsWith('.mov') || src.endsWith('.webm');

  return (
    <AbsoluteFill className="bg-black justify-center items-center overflow-hidden">
      {/* Background Blur duplicate for smart cropping */}
      <AbsoluteFill className="opacity-40 blur-2xl scale-125">
         {isVideo ? (
            <Video src={staticFile(src)} className="w-full h-full object-cover" muted />
         ) : (
            <Img src={staticFile(src)} className="w-full h-full object-cover" />
         )}
      </AbsoluteFill>
      
      {/* Primary Visual */}
      <div style={{ transform: `scale(${scaleX}, ${scaleY}) translateX(${moveX}px)`, width: '100%', height: '100%', position: 'absolute' }}>
         {isVideo ? (
            <Video src={staticFile(src)} className="w-full h-full object-contain" muted />
         ) : (
            <Img src={staticFile(src)} className="w-full h-full object-cover" />
         )}
      </div>

      {/* Cinematic Overlays */}
      <AbsoluteFill className="bg-gradient-to-t from-black/80 via-transparent to-black/30 pointer-events-none" />
      <AbsoluteFill className="pointer-events-none" style={{ boxShadow: 'inset 0 0 100px rgba(0,0,0,0.5)' }} />
    </AbsoluteFill>
  );
};

// AUDIO VISUALIZER
const VisualizerOverlay: React.FC<{ audioSrc: string }> = ({ audioSrc }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  
  const { audioData, dataOffsetInSeconds } = useWindowedAudioData({
    src: staticFile(audioSrc),
    frame,
    fps,
    windowInSeconds: 30,
  });

  if (!audioData) return null;

  const waveform = visualizeAudioWaveform({
    fps,
    frame,
    audioData,
    numberOfSamples: 128,
    windowInSeconds: 0.1,
    dataOffsetInSeconds,
  });

  const HEIGHT = 100;
  const path = createSmoothSvgPath({
    points: waveform.map((y, i) => ({
      x: (i / (waveform.length - 1)) * width,
      y: HEIGHT / 2 + (y * HEIGHT) / 2,
    })),
  });

  return (
    <div className="absolute inset-x-0 bottom-4 opacity-50 z-10 pointers-events-none">
      <svg width={width} height={HEIGHT} className="opacity-60 drop-shadow-lg">
        <path d={path} fill="none" stroke="#FDE047" strokeWidth={4} />
      </svg>
    </div>
  );
};

// MAIN COMPOSITION
export const Main: React.FC<MainProps> = (props) => {
  const { fps } = useVideoConfig();

  // Use a fallback for transitions length
  const TRANSITION_FRAMES = 15;

  return (
    <AbsoluteFill className="bg-black">
      {props.background_music && (
        <Audio src={staticFile(props.background_music)} volume={0.03} />
      )}
      
      {/* Waveform Visualizer anchored to background music if exists */}
      {props.background_music && (
         <VisualizerOverlay audioSrc={props.background_music} />
      )}
      
      {/* Custom Watermark */}
      <div className="absolute top-8 left-8 z-50 text-white/50 text-2xl font-bold tracking-widest flex items-center gap-2" style={{ fontFamily: 'Montserrat, sans-serif' }}>
          <div className="w-3 h-3 bg-yellow-400 rounded-full animate-pulse" />
          FOOTYBITEZ
      </div>

      {(() => {
        let cumulativeStart = 0;
        return props.segments.map((seg, idx) => {
           const durationFrames = Math.max(1, Math.round(seg.duration * fps));
           const startFrame = cumulativeStart;
           const isHook = seg.type === 'hook';
           let mediaList = (isHook && props.title_card) ? [props.title_card] : (seg.media && seg.media.length > 0 ? seg.media : [null]);

           cumulativeStart += durationFrames;
           if (idx < props.segments.length - 1) {
              cumulativeStart -= TRANSITION_FRAMES;
           }

           // Determine custom transition
           const isFade = idx % 2 === 0;
           const dirFrames = isFade ? 0 : (idx % 4 === 0 ? 1080 : 1920);

           return (
             <Sequence key={`seq-${idx}`} from={startFrame} durationInFrames={durationFrames}>
                <TransitionOverlay 
                    isFirst={idx === 0} 
                    duration={TRANSITION_FRAMES}
                    type={isFade ? 'fade' : 'slide'}
                    direction={idx % 4 === 0 ? 'top' : 'right'}
                >
                    <AbsoluteFill>
                      {seg.audio_path && <Audio src={staticFile(seg.audio_path)} />}
                      {/* Transition SFX overlaid on start */}
                      {idx > 0 && <Audio src="https://remotion.media/whoosh.wav" volume={0.3} />}
                      
                      {/* Visuals - Dynamic Fast Cuts */}
                      {mediaList.map((src, mIdx) => {
                          const sliceDur = Math.round(durationFrames / mediaList.length);
                          const isLast = mIdx === mediaList.length - 1;
                          const actualDur = isLast ? durationFrames - (sliceDur * mIdx) : sliceDur;
                          
                          return (
                             <Sequence key={`media-${mIdx}`} from={mIdx * sliceDur} durationInFrames={actualDur}>
                                <KenBurnsMedia src={src} durationInFrames={actualDur} index={idx + mIdx} />
                             </Sequence>
                          );
                      })}

                      
                      {/* Captions */}
                      <TikTokCaptions timing={seg.timing} fps={fps} />
                    </AbsoluteFill>
                </TransitionOverlay>
             </Sequence>
           );
        });
      })()}
    </AbsoluteFill>
  );
};
