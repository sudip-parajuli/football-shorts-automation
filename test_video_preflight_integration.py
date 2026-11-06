"""Real post-render inspection, including the dependency missed by mocked tests."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from footybitez.video.preflight import inspect_video, require_media_tools


class VideoPreflightTests(unittest.TestCase):
    def test_missing_ffprobe_reports_setup_error(self):
        with patch('footybitez.video.preflight.shutil.which', side_effect=lambda name: '/usr/bin/ffmpeg' if name == 'ffmpeg' else None):
            with self.assertRaisesRegex(RuntimeError, 'Missing media tools: ffprobe'):
                require_media_tools()

    def make_video(self, directory, audio):
        tools = require_media_tools()
        output = Path(directory) / 'test.mp4'
        command = [tools['ffmpeg'], '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=green:s=108x192:r=24:d=1']
        if audio:
            command += ['-f', 'lavfi', '-i', audio, '-shortest', '-c:a', 'aac']
        command += ['-c:v', 'libx264', str(output)]
        subprocess.run(command, capture_output=True, check=True, timeout=30)
        return output

    def test_real_rendered_video_passes_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            report = inspect_video(self.make_video(directory, 'sine=frequency=440:duration=1'))
            self.assertGreaterEqual(report['duration_seconds'], 1)
            self.assertGreater(report['mean_volume_db'], -45)

    def test_real_silent_audio_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'silent'):
                inspect_video(self.make_video(directory, 'anullsrc=r=44100:cl=mono:d=1'))

    def test_real_video_without_audio_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'no audio'):
                inspect_video(self.make_video(directory, None))


if __name__ == '__main__':
    unittest.main()
