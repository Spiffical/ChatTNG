import argparse
import os
import pysrt
import re
from moviepy.editor import VideoFileClip
from multiprocessing import Pool, cpu_count
import sys
from pathlib import Path
import tempfile
from moviepy.config import change_settings
import yaml
from tqdm import tqdm
import moviepy.editor as mpy
import json
from typing import List, Dict, Any
from backend.core.extraction.script_parser import ScriptParser
from backend.core.extraction.dialog_matcher import DialogMatcher
from backend.core.utils.text_utils import clean_dialog_text
from backend.core.utils.time_utils import time_to_seconds, seconds_to_time
from backend.core.storage.dialog_storage import DialogStorage
from backend.core.extraction.subtitle_processor import SubtitleExtractor

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

# Configure MoviePy to use system temp directory
change_settings({"TEMP_DIR": tempfile.gettempdir()})

def extract_clip(args):
    input_video, output_video, start_time, end_time, subtitle_group, group_index, total_groups = args
    
    # Convert group_index to string if it's not already
    group_index = str(group_index)
    total_groups = str(total_groups)
    
    print(f"\nProcessing group {group_index}/{total_groups}:")
    print(f"Extracting clip from {start_time} to {end_time}")

    try:
        with VideoFileClip(input_video) as video:
            # Convert string times to seconds
            if isinstance(start_time, str):
                # Parse time string in format HH:MM:SS,mmm
                h, m, s = map(float, start_time.replace(',', '.').split(':'))
                start_seconds = h * 3600 + m * 60 + s
            else:
                start_seconds = time_to_seconds(start_time)
                
            if isinstance(end_time, str):
                h, m, s = map(float, end_time.replace(',', '.').split(':'))
                end_seconds = h * 3600 + m * 60 + s
            else:
                end_seconds = time_to_seconds(end_time)
            
            new_clip = video.subclip(start_seconds, end_seconds)
            new_clip.write_videofile(output_video, codec="libx264", verbose=False, logger=None)
            
            # Extract and save subtitles
            subtitle_extractor = SubtitleExtractor()
            subtitle_segments = subtitle_extractor.extract_subtitle_segments(subtitle_group, start_seconds)
            
            # Save subtitles with same name as video but .srt extension
            subtitle_path = Path(output_video).with_suffix('.srt')
            subtitle_extractor.save_subtitles(subtitle_segments, subtitle_path)
        
        print(f"Clip and subtitles extracted successfully: {output_video}")
        return True, group_index
    except Exception as e:
        print(f"Error extracting clip: {e}")
        return False, group_index

def process_episode(video_file, subtitles_file, script_file, output_dir, padding_before, padding_after, force=False):
    # Extract season and episode from video filename
    video_filename = Path(video_file).stem
    match = re.match(r'S(\d+)E(\d+)', video_filename)
    if not match:
        print(f"Could not extract season/episode from filename: {video_filename}")
        return
    
    season = int(match.group(1))
    episode = int(match.group(2))
    
    # Initialize dialog storage with absolute path to config
    config_path = Path(project_root) / "config" / "app_config.yaml"
    storage = DialogStorage(str(config_path))
    
    # Check if episode exists in ChromaDB using $and operator
    where_clause = {
        "$and": [
            {"season": {"$eq": season}},
            {"episode": {"$eq": episode}}
        ]
    }
    
    existing_clips = storage.collection.get(
        where=where_clause
    )
    
    if existing_clips and existing_clips['ids'] and not force:
        print(f"Episode S{season:02d}E{episode:02d} already exists in database, skipping...")
        return
    elif existing_clips and existing_clips['ids'] and force:
        print(f"Force replacing episode S{season:02d}E{episode:02d}...")
        # Delete existing clips from storage
        for clip_id in existing_clips['ids']:
            storage.collection.delete(ids=[clip_id])
    
    # Create episode-specific output directory
    episode_dir = Path(output_dir) / f"S{season:02d}E{episode:02d}"
    episode_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse script file and match dialog
    parser = ScriptParser()
    script_segments = parser.parse_script(script_file)
    subs = pysrt.open(subtitles_file)
    matcher = DialogMatcher(script_segments, subs)
    matched_segments = matcher.match_dialog()
    
    # Calculate total number of potential clips
    total_clips = sum(1 for segment in matched_segments if segment['complete']) + \
                 sum(len(segment['sentences']) for segment in matched_segments)
    
    # Extract clips for matched segments
    extraction_args = []
    for i, segment in enumerate(matched_segments):
        # Handle complete match
        if segment['complete']:
            output_video = str(Path(episode_dir) / f'S{season:02d}E{episode:02d}_clip_{i:04d}.mp4')
            start_time = seconds_to_time(max(0, time_to_seconds(segment['complete']['start_time']) - padding_before))
            end_time = seconds_to_time(time_to_seconds(segment['complete']['end_time']) + padding_after)
            
            extraction_args.append((
                str(video_file), 
                output_video, 
                start_time, 
                end_time, 
                segment['complete']['subtitle_group'],
                f"{i}_complete", 
                str(total_clips)
            ))
        
        # Handle sentence matches
        for j, sentence_match in enumerate(segment['sentences']):
            output_video = str(Path(episode_dir) / f'S{season:02d}E{episode:02d}_clip_{i:04d}_s{j:02d}.mp4')
            start_time = seconds_to_time(max(0, time_to_seconds(sentence_match['start_time']) - padding_before))
            end_time = seconds_to_time(time_to_seconds(sentence_match['end_time']) + padding_after)
            
            extraction_args.append((
                str(video_file), 
                output_video, 
                start_time, 
                end_time, 
                sentence_match['subtitle_group'],
                f"{i}_s{j}", 
                str(total_clips)
            ))
    
    # Extract clips in parallel
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(extract_clip, extraction_args)
    
    # Add clips to storage
    for success, group_id in results:
        if success:
            # Parse the group_id to get original segment index and type
            if '_s' in group_id:
                segment_idx, sentence_idx = group_id.split('_s')
                segment_idx = int(segment_idx)
                sentence_idx = int(sentence_idx)
                segment = matched_segments[segment_idx]
                match_data = segment['sentences'][sentence_idx]
                clip_path = str(Path(episode_dir) / f'S{season:02d}E{episode:02d}_clip_{segment_idx:04d}_s{sentence_idx:02d}.mp4')
            else:
                segment_idx = int(group_id.split('_')[0])
                segment = matched_segments[segment_idx]
                match_data = segment['complete']
                clip_path = str(Path(episode_dir) / f'S{season:02d}E{episode:02d}_clip_{segment_idx:04d}.mp4')
            
            # Create clip ID and metadata
            clip_id = Path(clip_path).stem
            metadata = {
                "clip_path": clip_path,
                "start_time": str(match_data['start_time']),
                "end_time": str(match_data['end_time']),
                "season": season,
                "episode": episode,
                "speaker": segment['speaker'],
                "scene_info": segment['scene_info'],
                "match_ratio": match_data['match_ratio']
            }
            
            # Add to storage
            if storage.add_dialog(match_data['subtitle_text'], metadata, clip_id):
                if storage.get_dialog(clip_id):
                    print(f"Successfully verified storage of {clip_id}")
                else:
                    print(f"Warning: Failed to verify storage of {clip_id}")
            
            print(f"Processed clip {clip_id}")
        else:
            print(f"Failed to extract clip for group {group_id}")

def process_matches(matches, output_dir, season, episode, base_idx):
    """Process both complete and sentence-level matches"""
    clip_infos = []
    
    # Process complete match if it exists
    if matches['complete']:
        clip_info = create_clip_info(matches['complete'], output_dir, season, episode, base_idx)
        if clip_info:
            clip_infos.append(clip_info)
    
    # Process sentence matches
    for i, sentence_match in enumerate(matches['sentences']):
        clip_info = create_clip_info(
            sentence_match, 
            output_dir, 
            season, 
            episode, 
            f"{base_idx}_s{i}"
        )
        if clip_info:
            clip_infos.append(clip_info)
    
    return clip_infos

def create_clip_info(match, output_dir, season, episode, idx):
    """Helper to create clip info dictionary"""
    if not match:
        return None
        
    return {
        'output_video': str(Path(output_dir) / f'S{season:02d}E{episode:02d}_clip_{idx}.mp4'),
        'start_time': match['start_time'],
        'end_time': match['end_time'],
        'subtitle_group': match['subtitle_group'],
        'metadata': {
            'speaker': match['speaker'],
            'text': match['text'],
            'scene_info': match['scene_info'],
            'match_ratio': match['match_ratio']
        }
    }

def main(input_path, subtitles_path, script_path, output_dir, padding_before, padding_after, force=False):
    input_path = Path(input_path)
    subtitles_path = Path(subtitles_path)
    script_path = Path(script_path)
    output_dir = Path(output_dir)
    
    if input_path.is_file():
        # Process single video file
        video_file = input_path
        subtitles_file = subtitles_path / video_file.with_suffix('.srt').name
        script_file = script_path / video_file.with_suffix('.txt').name
        if not subtitles_file.exists() or not script_file.exists():
            print(f"Subtitle file or script file not found: {subtitles_file} or {script_file}")
            return
        process_episode(video_file, subtitles_file, script_file, output_dir, padding_before, padding_after, force)
    
    elif input_path.is_dir():
        # Process all video files in directory
        video_files = []
        for ext in ['.mkv', '.mp4', '.avi']:
            video_files.extend(input_path.glob(f'*{ext}'))
        
        for video_file in sorted(video_files):
            subtitles_file = subtitles_path / video_file.with_suffix('.srt').name
            script_file = script_path / video_file.with_suffix('.txt').name
            if not subtitles_file.exists() or not script_file.exists():
                print(f"Subtitle file or script file not found: {subtitles_file} or {script_file}")
                continue
            print(f"\nProcessing {video_file.name}")
            process_episode(video_file, subtitles_file, script_file, output_dir, padding_before, padding_after, force)
    
    else:
        print(f"Input path does not exist: {input_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract video clips based on SRT subtitles.')
    parser.add_argument('input_path', help='Path to input video file or directory containing video files')
    parser.add_argument('subtitles_path', help='Path to directory containing subtitle files')
    parser.add_argument('script_path', help='Path to directory containing script files')
    parser.add_argument('output_dir', help='Directory to save extracted clips')
    parser.add_argument('--padding_before', type=float, default=0.1, 
                       help='Padding in seconds to add before each clip (default: 0.1)')
    parser.add_argument('--padding_after', type=float, default=0.1, 
                       help='Padding in seconds to add after each clip (default: 0.1)')
    parser.add_argument('--force', action='store_true',
                       help='Force replace existing episodes in database')
    args = parser.parse_args()

    main(args.input_path, args.subtitles_path, args.script_path, args.output_dir, 
         args.padding_before, args.padding_after, args.force)
