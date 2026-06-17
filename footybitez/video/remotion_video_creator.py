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
        self.voice_gen = VoiceGenerator(key_pool="shorts")
        self.sfx_man = SFXManager()

    def _copy_to_public(self, filepath, fallback=""):
        if not filepath or not os.path.exists(filepath):
            return fallback
        filename = os.path.basename(filepath)
        dest = os.path.join(self.remotion_public, filename)
        shutil.copy2(filepath, dest)
        return filename

    def cleanup_public_assets(self):
        """
        Deletes old generated or copied images, audios, and temporary files from the public folder.
        Preserves static assets like fonts and necessary templates.
        """
        logger.info("Cleaning up old assets in remotion public folder...")
        
        # 1. Clean public root
        if os.path.exists(self.remotion_public):
            for filename in os.listdir(self.remotion_public):
                file_path = os.path.join(self.remotion_public, filename)
                if os.path.isfile(file_path):
                    # Preserved files
                    if filename in ["dummy.jpg", "dummy_verif.jpg", "metadata.json"]:
                        continue
                    # Delete old jpg, mp3, mp4, json
                    if filename.endswith((".jpg", ".mp3", ".mp4", ".json")):
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            logger.warning(f"Failed to delete {filename}: {e}")
                            
        # 2. Clean assets/images
        images_dir = os.path.join(self.remotion_public, "assets", "images")
        if os.path.exists(images_dir):
            for filename in os.listdir(images_dir):
                file_path = os.path.join(images_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete {filename} in assets/images: {e}")

        # 3. Clean assets/audio
        audio_dir = os.path.join(self.remotion_public, "assets", "audio")
        if os.path.exists(audio_dir):
            for filename in os.listdir(audio_dir):
                if filename in ["hook.json", "outro.json", "segment_0.json", "segment_1.json"]:
                    continue
                file_path = os.path.join(audio_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete {filename} in assets/audio: {e}")

        # 4. Clean public/music
        music_dir = os.path.join(self.remotion_public, "music")
        if os.path.exists(music_dir):
            for filename in os.listdir(music_dir):
                file_path = os.path.join(music_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete {filename} in public/music: {e}")

    def create_video(self, script_data, visual_assets, background_music_path=None):
        logger.info("Starting Remotion Video Creation...")
        
        # Clean public directory first to ensure no stale cached assets are reused
        self.cleanup_public_assets()
        
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
                media_files = [remotion_props["title_card"]] if remotion_props["title_card"] else []
            elif chunk["type"] == "outro":
                # Use custom outro image if provided, otherwise reuse title card
                if visual_assets.get("outro_image"):
                    media_files = [self._copy_to_public(visual_assets.get("outro_image"))]
                else:
                    media_files = [remotion_props["title_card"]] if remotion_props["title_card"] else []
            else:
                segment_media_pool = visual_assets.get('segment_media', [])
                if segment_media_pool:
                    idx = chunk.get("index", 0)
                    if idx < len(segment_media_pool):
                        pool = segment_media_pool[idx]
                        if not isinstance(pool, list): pool = [pool]
                        media_files = [self._copy_to_public(p) for p in pool if p]
                
                # Fallback: if no media found for this segment, reuse title card
                if not media_files and remotion_props["title_card"]:
                    media_files = [remotion_props["title_card"]]
                elif not media_files and remotion_props["profile_image"]:
                    media_files = [remotion_props["profile_image"]]

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
        # Use relative path for output to avoid absolute path quirks in CI/containers
        output_rel_path = os.path.join("..", self.output_dir, "final_short.mp4")
        output_abs_path = os.path.abspath(os.path.join(self.output_dir, "final_short.mp4"))
        
        # Execute remotion process
        cmd = [
            "npx", "remotion", "render", 
            "src/index.ts", "Main", 
            output_rel_path, 
            "--props=props.json"
        ]
        
        # On POSIX (Linux), shell=True requires the command to be a single string
        import platform
        if platform.system() != "Windows":
             import shlex
             cmd_str = shlex.join(cmd)
             logger.info(f"Linux/Mac detected. Using shlex joined command.")
        else:
             # On Windows, joins with spaces
             cmd_str = " ".join(cmd)

        try:
            logger.info(f"Environment: {platform.platform()} | CWD: {os.getcwd()}")
            logger.info(f"Target Render Directory: {os.path.abspath(self.remotion_dir)}")
            logger.info(f"Executing Rendering Command: {cmd_str}")

            # Capture output for debugging in CI
            process = subprocess.run(
                cmd_str, 
                cwd=self.remotion_dir, 
                check=True, 
                shell=True,
                capture_output=True,
                text=True
            )
            
            if process.stdout:
                logger.info(f"Remotion Render Output: {process.stdout}")
            if process.stderr:
                logger.warning(f"Remotion Render Warnings/Errors: {process.stderr}")
                
            logger.info("Remotion rendering completed successfully.")
            
            # Post-render check
            if os.path.exists(output_abs_path):
                logger.info(f"Verified: Output file exists at {output_abs_path}")
            else:
                logger.error(f"Post-render ALERT: Output file NOT FOUND at {output_abs_path}")
                
            return output_abs_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Remotion Render Failed (Code {e.returncode})")
            logger.error(f"RENDER STDOUT: {e.stdout}")
            logger.error(f"RENDER STDERR: {e.stderr}")
            raise Exception(f"Remotion failed to render video: {e.stderr}")
