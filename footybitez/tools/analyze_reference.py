"""Download a bounded reference excerpt and measure cuts with FFmpeg.

Usage: python -m footybitez.tools.analyze_reference URL --start 30 --seconds 30
Reference excerpts are kept in a separate analysis directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse


def analyze_reference(url, start=0, seconds=30, root='footybitez/data/references'):
    if urlparse(url).scheme not in ('http', 'https') or start < 0 or not 1 <= seconds <= 60:
        raise ValueError('Use a public video URL and an excerpt of 1–60 seconds')
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import download_range_func
    output = Path(root) / hashlib.sha256(f'{url}:{start}:{seconds}'.encode()).hexdigest()[:12]
    output.mkdir(parents=True, exist_ok=True)
    options = {
        'js_runtimes': {'node': {}},
        'noplaylist': True, 'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        'merge_output_format': 'mp4', 'outtmpl': str(output / 'reference.%(ext)s'),
        'download_ranges': download_range_func(None, [(start, start+seconds)]),
        'force_keyframes_at_cuts': True, 'socket_timeout': 20, 'retries': 1,
        'max_filesize': 100_000_000,
    }
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=True)
    videos = [path for path in output.iterdir() if path.suffix.lower() in ('.mp4', '.webm', '.mkv')]
    if len(videos) != 1:
        raise RuntimeError('Expected a single reference excerpt')
    video = videos[0]
    probe = subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)],
                           capture_output=True, text=True, check=True, timeout=30)
    cuts = subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-an','-vf',
                           r'select=gt(scene\,0.30),showinfo','-f','null','-'],
                          capture_output=True, text=True, check=True, timeout=120)
    cut_times = [float(value) for value in re.findall(r'pts_time:([\d.]+)', cuts.stderr)]
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(video),'-vf',
                    'fps=1/3,scale=480:-2','-frames:v','12',str(output/'frame_%02d.jpg')],
                   capture_output=True, check=True, timeout=60)
    report = {'reference_url':url,'title':info.get('title'),'creator':info.get('uploader'),
              'excerpt_start':start,'requested_seconds':seconds,'cut_times':cut_times,
              'probe':json.loads(probe.stdout),'frames':[str(path) for path in sorted(output.glob('frame_*.jpg'))]}
    (output/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--start',type=float,default=0)
    parser.add_argument('--seconds',type=float,default=30)
    args = parser.parse_args()
    print(analyze_reference(args.url,args.start,args.seconds))
