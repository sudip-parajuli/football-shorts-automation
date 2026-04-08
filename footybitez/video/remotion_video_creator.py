import os
import json
import logging
from moviepy.editor import AudioFileClip
import shutil
import subprocess

logger = logging.getLogger(__name__)

class RemotionVideoCreator:
    def __init__(self, output_dir="footybitez/output", remotion_dir="remotion-video"):
        self.output_dir = output_dir
        self.remotion_dir = remotion_dir
        self.remotion_public = os.path.join(remotion_dir, "public")
        
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(self.remotion_public, exist_ok=True)
        
        from footybitez.media.voice_generator import VoiceGenerator
        from footybitez.media.sfx_manager import SFXManager
        self.voice_gen = VoiceGenerator()
        self.sfx_man = SFXManager()

    def _copy_to_public(self, filepath, fallback=""):
        if not filepath or not os.path.exists(filepath):
            return fallback
        filename = os.path.basename(filepath)
        dest = os.path.join(self.remotion_public, filename)
        shutil.copy2(filepath, dest)
        return filename

    def create_video(self, script_data, visual_assets, background_music_path=None):
        logger.info("Starting Remotion Video Creation...")
        
        # 1. Flatten Script chunks (Hook, Segments, Outro)
        chunks = []
        chunks.append({"type": "hook", "text": script_data.get("hook", ""), "is_title": True})
        
        segments = script_data.get("segments", [])
        for i, seg in enumerate(segments):
            text = seg['text'] if isinstance(seg, dict) else seg
            chunks.append({"type": f"segment_{i}", "text": text, "is_title": False, "index": i})
        
        chunks.append({"type": "outro", "text": script_data.get("outro", ""), "is_title": False})

        # 2. Setup Remotion Data Structure
        remotion_props = {
            "title_card": self._copy_to_public(visual_assets.get("title_card")),
            "profile_image": self._copy_to_public(visual_assets.get("profile_image")),
            "background_music": self._copy_to_public(background_music_path),
            "segments": []
        }

        # 3. Process Audio & Timings
        current_time = 0.0
        
        for i, chunk in enumerate(chunks):
            # Generate Audio
            audio_path = self.voice_gen.generate(chunk['text'], f"{chunk['type']}.mp3")
            json_path = audio_path.replace('.mp3', '.json')
            
            # Get duration
            audio_duration = 0
            if os.path.exists(audio_path):
                clip = AudioFileClip(audio_path)
                audio_duration = clip.duration
                clip.close()

            # Load word timings
            timing_data = []
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    try:
                        timing_data = json.load(f)
                        # Ensure timings are relative to this segment
                        for t in timing_data:
                            # EdgeTTS outputs absolute time within the generated chunk!
                            # Since we play the chunk in a <Sequence> via Remotion, `start` is relative to Sequence.
                            pass
                    except:
                        logger.warning(f"Failed to parse timing JSON for {chunk['type']}")
            
            # Prepare Visual Media List
            media_files = []
            if chunk["is_title"]:
                media_files = [remotion_props["title_card"]]
            else:
                segment_media_pool = visual_assets.get('segment_media', [])
                if segment_media_pool:
                    idx = chunk.get("index", len(segment_media_pool) - 1)
                    if idx < len(segment_media_pool):
                        pool = segment_media_pool[idx]
                        if not isinstance(pool, list): pool = [pool]
                        media_files = [self._copy_to_public(p) for p in pool]

            # Append segment
            remotion_props["segments"].append({
                "type": chunk["type"],
                "text": chunk["text"],
                "start": current_time,
                "duration": audio_duration,
                "media": media_files,
                "timing": timing_data,
                "audio_path": self._copy_to_public(audio_path)
            })

            current_time += audio_duration

        # 4. Save props.json
        props_path = os.path.join(self.remotion_dir, "props.json")
        with open(props_path, 'w', encoding='utf-8') as f:
            json.dump(remotion_props, f, indent=2)
            
        logger.info(f"Saved properties to {props_path}")

        # 5. Render Video via Remotion CLI
        output_file = os.path.abspath(os.path.join(self.output_dir, "final_short.mp4"))
        
        # Execute remotion process
        cmd = [
            "npx", "remotion", "render", 
            "src/index.ts", "Main", 
            output_file, 
            "--props=props.json"
        ]
        
        try:
            # Change directory to remotion project to run the render
            logger.info("Starting Remotion Render...")
            subprocess.run(cmd, cwd=self.remotion_dir, check=True, shell=True)
            logger.info("Remotion rendering completed successfully.")
            return output_file
        except subprocess.CalledProcessError as e:
            logger.error(f"Remotion Render Failed: {e}")
            raise Exception("Remotion failed to render video")
