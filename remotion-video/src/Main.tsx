import { AbsoluteFill, Audio, Img, Sequence, useVideoConfig, spring, useCurrentFrame, interpolate, staticFile, Video } from 'remotion';
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
    <div style={{
      position: 'absolute',
      bottom: '15%',
      left: 0,
      right: 0,
      display: 'flex',
      flexWrap: 'wrap',
      justifyContent: 'center',
      alignItems: 'center',
      gap: '12px 20px',
      padding: '0 60px',
      textAlign: 'center',
      fontFamily: 'Montserrat, Impact, sans-serif',
      zIndex: 20,
    }}>
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

        const baseSize = isHighlighted ? '82px' : '64px';
        const popAmount = isHighlighted ? 0.18 : 0.1;
        
        const scale = isActive ? 1 + (pop * popAmount) : 1;
        const rotation = isActive && isHighlighted ? pop * (idx % 2 === 0 ? 2 : -2) : 0;
        
        let color = 'white';
        if (isActive) {
           color = isHighlighted ? '#FDE047' : '#FFFFFF'; 
        } else if (isHighlighted) {
           color = isPast ? '#FEF08A' : '#FFFFFF';
        }

        return (
          <span 
            key={idx} 
            style={{
              transform: `scale(${scale}) rotate(${rotation}deg)`,
              color,
              textShadow: '0px 4px 12px rgba(0,0,0,1), 0px 0px 40px rgba(0,0,0,0.9)',
              WebkitTextStroke: isHighlighted ? '3px #000' : '2px #000',
              fontWeight: 900,
              fontSize: baseSize,
              display: 'inline-block',
              lineHeight: 1.1,
              background: isActive ? 'rgba(0,0,0,0.45)' : 'transparent',
              borderRadius: 8,
              padding: '2px 8px',
              transition: 'color 0.08s linear',
            }}
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
  
  if (!src) return <AbsoluteFill style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)' }} />;

  // Motion patterns
  const motionTypes = ['zoom-in', 'pan-right', 'zoom-out', 'pan-left', 'tilt-up', 'tilt-down'];
  const motion = motionTypes[index % motionTypes.length];
  
  let scale = 1.1; 
  let moveX = 0;
  let moveY = 0;
  
  const progress = Math.min(1, frame / Math.max(1, durationInFrames));
  
  const isCard = /^(pre_card\d|post_card\d|card_-?\d+|placeholder)/i.test(src);
  
  if (isCard) {
     scale = 1.0;
     moveX = 0;
     moveY = 0;
  } else if (motion === 'zoom-in') {
     scale = interpolate(progress, [0, 1], [1.1, 1.3]);
  } else if (motion === 'zoom-out') {
     scale = interpolate(progress, [0, 1], [1.3, 1.1]);
  } else if (motion === 'pan-right') {
     scale = 1.25;
     moveX = interpolate(progress, [0, 1], [-5, 5]);
  } else if (motion === 'pan-left') {
     scale = 1.25;
     moveX = interpolate(progress, [0, 1], [5, -5]);
  } else if (motion === 'tilt-up') {
     scale = 1.25;
     moveY = interpolate(progress, [0, 1], [4, -4]);
  } else if (motion === 'tilt-down') {
     scale = 1.25;
     moveY = interpolate(progress, [0, 1], [-4, 4]);
  }

  const isVideo = src.endsWith('.mp4') || src.endsWith('.mov') || src.endsWith('.webm');

  return (
    <AbsoluteFill style={{ background: '#000', overflow: 'hidden' }}>
      {/* Blurred background fill for portrait letterboxing */}
      <AbsoluteFill style={{ opacity: 0.5, filter: 'blur(20px)', transform: 'scale(1.2)' }}>
         {isVideo ? (
            <Video src={staticFile(src)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} muted />
         ) : (
            <Img src={staticFile(src)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
         )}
      </AbsoluteFill>
      
      {/* Primary Visual - Ken Burns motion */}
      <AbsoluteFill style={{ transform: `scale(${scale}) translate(${moveX}%, ${moveY}%)` }}>
         {isVideo ? (
            <Video src={staticFile(src)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} muted />
         ) : (
            <Img src={staticFile(src)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
         )}
      </AbsoluteFill>

      {/* Cinematic Overlays */}
      <AbsoluteFill style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 40%, rgba(0,0,0,0.3) 100%)', pointerEvents: 'none' }} />
      <AbsoluteFill style={{ boxShadow: 'inset 0 0 80px rgba(0,0,0,0.6)', pointerEvents: 'none' }} />
    </AbsoluteFill>
  );
};

// MEDIA FLASH TRANSITION COMPONENT
const MediaFlash: React.FC<{ fps: number }> = ({ fps }) => {
  const frame = useCurrentFrame();
  const spr = spring({ frame, fps, config: { stiffness: 200 } });
  const opacity = spr > 0.5 ? 0 : interpolate(spr, [0, 1], [0.3, 0]);
  
  return (
    <AbsoluteFill style={{ 
      background: 'white', 
      opacity,
      zIndex: 10,
      pointerEvents: 'none'
    }} />
  );
};

// MAIN COMPOSITION
export const Main: React.FC<MainProps> = (props) => {
  const { fps } = useVideoConfig();

  // Use a fallback for transitions length
  const TRANSITION_FRAMES = 15;

  return (
    <AbsoluteFill style={{ background: '#000' }}>
      {props.background_music && (
        <Audio src={staticFile(props.background_music)} volume={0.04} />
      )}
      
      {/* Custom Watermark */}
      <div style={{ position: 'absolute', top: 40, left: 0, right: 0, zIndex: 50, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10, fontFamily: 'Montserrat, sans-serif' }}>
          <div style={{ width: 12, height: 12, background: '#FDE047', borderRadius: '50%' }} />
          <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 36, fontWeight: 900, letterSpacing: 8 }}>FOOTYBITEZ</span>
      </div>

      {(() => {
        let cumulativeStart = 0;
        return props.segments.map((seg, idx) => {
           const durationFrames = Math.max(1, Math.round(seg.duration * fps));
           const startFrame = cumulativeStart;
           const isHook = seg.type === 'hook';
           let mediaList = (isHook && props.title_card) ? [props.title_card] : (seg.media && seg.media.length > 0 ? seg.media : [null]);

           cumulativeStart += durationFrames;
           // NO overlap subtraction — audio tracks must not overlap

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
                      
                      {/* Visuals - Dynamic Fast Cuts */}
                      {mediaList.map((src, mIdx) => {
                          const sliceDur = Math.round(durationFrames / mediaList.length);
                          const isLast = mIdx === mediaList.length - 1;
                          const actualDur = isLast ? durationFrames - (sliceDur * mIdx) : sliceDur;
                          
                          return (
                             <Sequence key={`media-${mIdx}`} from={mIdx * sliceDur} durationInFrames={actualDur}>
                                <KenBurnsMedia src={src} durationInFrames={actualDur} index={idx + mIdx} />
                                {mIdx > 0 && (
                                   <MediaFlash fps={fps} />
                                )}
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
