
import os
import numpy as np
from moviepy.editor import AudioClip
import logging
import random

logger = logging.getLogger(__name__)

class SFXManager:
    def __init__(self, sfx_dir="footybitez/media/sfx"):
        self.sfx_dir = sfx_dir
        os.makedirs(sfx_dir, exist_ok=True)
        self.sample_rate = 44100

    def get_sfx(self, effect_type="whoosh", duration=None):
        """
        Returns an AudioFileClip (from disk) or AudioClip (generated) for the requested effect.
        effect_type: 'whoosh', 'impact', 'riser', 'camera'
        """
        # 1. Try to find existing file
        try:
            filename = f"{effect_type}.mp3"
            filepath = os.path.join(self.sfx_dir, filename)
            
            # Check for variations (whoosh_1.mp3, etc)
            if os.path.exists(self.sfx_dir):
                candidates = [f for f in os.listdir(self.sfx_dir) if f.startswith(effect_type) and f.endswith('.mp3')]
                if candidates:
                    filepath = os.path.join(self.sfx_dir, random.choice(candidates))
            
            if os.path.exists(filepath):
                logger.info(f"Using existing SFX: {filepath}")
                from moviepy.editor import AudioFileClip
                clip = AudioFileClip(filepath)
                if clip is None:
                    logger.error(f"AudioFileClip returned None for {filepath}")
                    raise ValueError("AudioFileClip returned None")
                return clip
        except Exception as e:
            logger.error(f"Error loading SFX file: {e}")
            
        logger.info(f"SFX not found: {effect_type}. Generating procedural fallback.")
        clip = self._generate_procedural_sfx(effect_type, duration)
        if clip is None:
            logger.error(f"_generate_procedural_sfx returned None for {effect_type}")
            # Fallback to whoosh
            return self._make_whoosh(1.0)
        return clip

    def _generate_procedural_sfx(self, effect_type, duration):
        """Generates simple placeholders using numpy."""
        if effect_type == "whoosh":
            dur = duration or 0.6 # Faster default
            return self._make_whoosh(dur)
        elif effect_type == "impact":
            dur = duration or 2.0
            return self._make_impact(dur)
        elif effect_type == "kick":
            dur = duration or 0.5
            return self._make_kick(dur)
        elif effect_type == "riser":
            dur = duration or 3.0
            return self._make_riser(dur)
        else:
            return self._make_whoosh(0.6)

    def _to_stereo(self, audio_array):
        """Converts mono (N,) or (N, 1) to stereo (N, 2)."""
        if len(audio_array.shape) == 1:
            return np.column_stack((audio_array, audio_array))
        elif audio_array.shape[1] == 1:
             return np.column_stack((audio_array, audio_array))
        return audio_array

    def _make_whoosh(self, duration):
        """White noise with fast pass filter sweep."""
        def make_frame(t):
            t_arr = np.atleast_1d(t)
            noise = np.random.uniform(-0.5, 0.5, t_arr.shape)
            
            # Sharper envelope for "Fast" whoosh
            t_norm = t_arr / duration 
            envelope = np.sin(np.pi * t_norm) ** 2 # Squared sine for tighter peak
            
            result = noise * envelope
            if np.isscalar(t):
                return np.array([result, result]) 
            return self._to_stereo(result)

    def _make_kick(self, duration):
        """Punchy 'Ball Kick' sound (Impact + Thud)."""
        def make_frame(t):
            t_arr = np.atleast_1d(t)
            
            # 1. Low Thud (60Hz -> 30Hz fast drop)
            freq_thud = 60 * np.exp(-10 * t_arr)
            thud = np.sin(2 * np.pi * freq_thud * t_arr) * np.exp(-10 * t_arr)
            
            # 2. Impact Noise (Leather hit) - high decay
            noise = np.random.uniform(-1, 1, t_arr.shape) * np.exp(-20 * t_arr)
            
            result = (thud * 0.7) + (noise * 0.3)
            
            if np.isscalar(t):
                return np.array([result, result])
            return self._to_stereo(result)

    def _make_impact(self, duration):
        """Cinematic Boom."""
        def make_frame(t):
            t_arr = np.atleast_1d(t)
            freq = 100 * np.exp(-3 * t_arr) 
            wave = np.sin(2 * np.pi * freq * t_arr)
            envelope = np.exp(-2 * t_arr)
            noise = np.random.uniform(-0.2, 0.2, t_arr.shape) * envelope * 0.3
            result = (wave * envelope) + noise
            if np.isscalar(t):
                return np.array([result, result])
            return self._to_stereo(result)

        return AudioClip(make_frame, duration=duration, fps=self.sample_rate)

    def _make_riser(self, duration):
        """Sine sweep up with volume fade in."""
        def make_frame(t):
            t_arr = np.atleast_1d(t)
            
            # Freq: 100Hz -> 800Hz
            # Linear sweep
            freq = 100 + (700 * (t_arr / duration))
            wave = np.sin(2 * np.pi * freq * t_arr)
            
            # Volume ramp up
            envelope = (t_arr / duration) ** 2 # Exponential ramp
            
            result = wave * envelope
            if np.isscalar(t):
                return np.array([result, result])
            return self._to_stereo(result)

if __name__ == "__main__":
    man = SFXManager()
    # Test generation
    try:
        w = man.get_sfx("whoosh")
        w.write_audiofile("footybitez/media/sfx/test_whoosh.mp3", fps=44100)
    except:
        pass
