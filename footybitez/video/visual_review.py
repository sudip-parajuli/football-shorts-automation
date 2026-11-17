"""Bounded rendered-frame review: scene edges, contact sheet and blank-frame warnings."""
import json
import logging
from pathlib import Path
import subprocess
from PIL import Image,ImageDraw,ImageStat

logger=logging.getLogger(__name__)


def scene_spans(props,fps=24):
    spans=[];cursor=0
    for chapter_index,chapter in enumerate(props.get('chapters',[])):
        cursor+=0 if chapter_index==0 else fps
        chapter_start=cursor
        for scene in chapter.get('visual_scenes',[]):
            duration=scene.get('duration_frames',0)
            if duration>0: spans.append((cursor/fps,(cursor+duration)/fps))
            cursor+=duration
        cursor=chapter_start+chapter.get('duration_in_frames',cursor-chapter_start)
    for segment in props.get('segments',[]):
        for scene in segment.get('visual_scenes',[]):
            start=cursor+scene.get('from_frame',0)
            spans.append((start/fps,(start+scene['duration_frames'])/fps))
        cursor+=round(segment['duration']*fps)
    return spans


def review_render(video,output_dir,props=None,duration=None):
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    if duration is None:
        result=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(video)],capture_output=True,text=True,check=True,timeout=30)
        duration=float(json.loads(result.stdout)['format']['duration'])
    spans=scene_spans(props or {}) or [(0,duration)]
    if len(spans)>6:
        spans=[spans[round(index*(len(spans)-1)/5)] for index in range(6)]
    samples=[]
    for index,(start,end) in enumerate(spans):
        end=min(end,duration)
        for label,time in [('start',start),('middle',(start+end)/2),('end',max(start,end-2/24))]:
            time=min(max(0,time),max(0,duration-2/24))
            path=output/f'frame-{index:02d}-{label}.jpg'
            subprocess.run(['ffmpeg','-y','-v','error','-ss',str(time),'-i',str(video),'-frames:v','1',
                '-vf','scale=360:360:force_original_aspect_ratio=decrease','-threads','1',str(path)],capture_output=True,check=True,timeout=40)
            with Image.open(path) as image:
                stats=ImageStat.Stat(image.convert('L'))
                samples.append({'scene':index,'position':label,'seconds':round(time,3),
                    'frame':path.name,'possibly_blank':stats.mean[0]<4 and stats.stddev[0]<3})
    sheet=Image.new('RGB',(1080,420*((len(samples)+2)//3)),'#101b24')
    draw=ImageDraw.Draw(sheet)
    for index,sample in enumerate(samples):
        x=(index%3)*360;y=(index//3)*420
        with Image.open(output/sample['frame']) as image:
            sheet.paste(image,(x+(360-image.width)//2,y+35+(360-image.height)//2))
        draw.text((x+12,y+12),f"Scene {sample['scene']+1}: {sample['position']} / {sample['seconds']:.2f}s",fill='#f4efe4')
    sheet.save(output/'contact-sheet.jpg',quality=90)
    report={'duration_seconds':duration,'sampled_frames':len(samples),'samples':samples,
            'note':'Sampled visual review; font and text bounds are checked on every Remotion frame.'}
    (output/'visual-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def try_review_render(video,output_dir,props,duration):
    try:
        return review_render(video,output_dir,props,duration)
    except Exception as error:
        logger.warning('Contact-sheet generation failed (%s); render and preflight results are preserved',type(error).__name__)
        Path(output_dir).mkdir(parents=True,exist_ok=True)
        (Path(output_dir)/'visual-review.json').write_text(json.dumps({'status':'review_failed','error_type':type(error).__name__}),encoding='utf-8')
