import argparse
from pathlib import Path
import subprocess
import json
import sys
from tqdm import tqdm
import re

def get_subtitle_streams(video_file):
    """Get all subtitle streams from the video file"""
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        '-select_streams', 's',
        str(video_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error getting subtitle info for {video_file}: {result.stderr}")
        return []
    
    data = json.loads(result.stdout)
    streams = data.get('streams', [])
    print(f"Found {len(streams)} subtitle streams:")
    for stream in streams:
        print(f"  - Stream {stream.get('index')}: codec={stream.get('codec_name')}, language={stream.get('tags', {}).get('language')}")
    return streams

def extract_episode_info(filename):
    """Extract season and episode numbers from filename"""
    pattern = r'S(\d{2})E(\d{2})'
    match = re.search(pattern, filename)
    if match:
        return f"S{match.group(1)}E{match.group(2)}"
    return None

def extract_subtitles(video_file, output_dir):
    """Extract English subtitles from video file"""
    video_file = Path(video_file)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Try to extract episode info from filename
    episode_name = extract_episode_info(video_file.stem)
    print(f"Extracted episode info: {episode_name}")
    # Use episode format (S01E01) if found, otherwise use original filename
    output_filename = f"{episode_name}.srt" if episode_name else f"{video_file.stem}.srt"
    
    # Check if output file already exists
    output_file = output_dir / output_filename
    if output_file.exists():
        print(f"Subtitle file already exists: {output_file}")
        return output_file  # Return existing file path
    
    # Get all subtitle streams
    subtitle_streams = get_subtitle_streams(video_file)
    
    if not subtitle_streams:
        print(f"No subtitle streams found in {video_file}")
        return None
    
    # Find English subtitles, preferring SRT/text-based formats
    english_stream = None
    for stream in subtitle_streams:
        tags = stream.get('tags', {})
        language = tags.get('language', '').lower()
        codec = stream.get('codec_name', '').lower()
        
        print(f"Checking stream: language={language}, codec={codec}")
        
        if language in ['eng', 'en']:
            # Prefer text-based subtitle formats
            if codec in ['subrip', 'ass', 'ssa']:
                print(f"Found preferred text-based English subtitle stream: {stream['index']}")
                english_stream = stream
                break
            # Fallback to first English stream if no text-based format is found
            elif not english_stream:
                print(f"Found fallback English subtitle stream: {stream['index']}")
                english_stream = stream
    
    if not english_stream:
        print(f"No English subtitles found in {video_file}")
        return None
    
    # Extract the subtitles
    output_file = output_dir / output_filename
    stream_index = english_stream['index']
    
    print(f"Extracting subtitle stream {stream_index} to {output_file}")
    
    cmd = [
        'ffmpeg',
        '-i', str(video_file),
        '-map', f'0:{stream_index}',
        '-c:s', 'srt',
        str(output_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error extracting subtitles from {video_file}: {result.stderr}")
        return None
    
    return output_file

def process_video_folder(input_dir, output_dir):
    """Process all video files in a directory"""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    
    # List all video files
    video_files = []
    for ext in ['.mkv', '.mp4', '.avi']:
        video_files.extend(input_dir.glob(f'*{ext}'))
    
    if not video_files:
        print(f"No video files found in {input_dir}")
        return
    
    print(f"Found {len(video_files)} video files")
    successful = 0
    failed = 0
    
    # Process each video file
    for video_file in tqdm(sorted(video_files), desc="Extracting subtitles"):
        output_file = extract_subtitles(video_file, output_dir)
        if output_file:
            print(f"Extracted subtitles from {video_file.name} to {output_file}")
            successful += 1
        else:
            print(f"Failed to extract subtitles from {video_file.name}")
            failed += 1
    
    print(f"\nProcessing complete:")
    print(f"Successfully processed: {successful}")
    print(f"Failed: {failed}")

def main():
    parser = argparse.ArgumentParser(description='Extract English subtitles from video files')
    parser.add_argument('input_dir', help='Directory containing video files')
    parser.add_argument('--output_dir', default='data/raw/subtitles/srt', 
                       help='Directory to save extracted subtitles')
    args = parser.parse_args()
    
    process_video_folder(args.input_dir, args.output_dir)

if __name__ == '__main__':
    main()
