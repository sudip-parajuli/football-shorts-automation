import json
import os
import shutil
from footybitez.content.long_form_script_generator import LongFormScriptGenerator
from footybitez.media.media_sourcer import MediaSourcer
from footybitez.video.long_form_video_creator import LongFormVideoCreator

def run_test():
    topic = "The Mystery of Inter Milan 2010"
    
    # 1. Script
    print("--- 1. Generating Cinematic Script ---")
    script_gen = LongFormScriptGenerator()
    script_data = script_gen.generate_long_script(topic)
    
    if not script_data:
        print("Script generation failed!")
        return
        
    print(json.dumps(script_data, indent=2))
    
    # 2. Media
    print("--- 2. Fetching Media ---")
    media_sourcer = MediaSourcer()
    
    visual_assets = {
        'segment_media': []
    }
    
    # Gather all visual_keywords from the payload
    keywords = []
    if 'hook' in script_data: keywords.append(script_data['hook']['visual_keyword'])
    if 'intro' in script_data: keywords.append(script_data['intro']['visual_keyword'])
    for chap in script_data.get('chapters', []):
        for fact in chap.get('facts', []):
            keywords.append(fact['visual_keyword'])
            
    print(f"Found {len(keywords)} visual keywords to fetch.")
    
    for kw in keywords[:5]: # Just fetch a small pool for testing speed
        paths = media_sourcer.get_media(kw, count=1, orientation="horizontal")
        if paths:
            visual_assets['segment_media'].extend(paths)
            
    if not visual_assets['segment_media']:
        print("No media fetched.")
        return
        
    print(f"Fetched {len(visual_assets['segment_media'])} visuals.")
    
    # 3. Assemble
    print("--- 3. Assembling Cinematic Video ---")
    video_creator = LongFormVideoCreator(output_dir="footybitez/output")
    out_path = video_creator.create_long_video(script_data, visual_assets)
    
    print(f"--- SUCCESS: Video created at {out_path} ---")
    
if __name__ == "__main__":
    run_test()
