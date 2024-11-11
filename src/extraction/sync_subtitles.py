import glob
import subprocess
import os
import argparse
import sys
from pathlib import Path

def sync_subtitles(video_dir, subs_dir, output_dir, alass_path):
    os.makedirs(output_dir, exist_ok=True)
    
    video_files = glob.glob(os.path.join(video_dir, "S*.mkv"))
    
    if not video_files:
        print(f"No video files found in {video_dir}")
        return
    
    for video_file in video_files:
        episode_code = Path(video_file).stem
        subtitle_file = os.path.join(subs_dir, f"{episode_code}.srt")
        
        if os.path.exists(subtitle_file):
            output_file = os.path.join(output_dir, f"{episode_code}.srt")
            
            # Use the provided alass path
            cmd = [alass_path, video_file, subtitle_file, output_file, '--no-split']
            print(f"Processing {episode_code}...")
            
            try:
                subprocess.run(cmd, check=True)
                print(f"Successfully processed {episode_code}")
            except subprocess.CalledProcessError as e:
                print(f"Error processing {episode_code}: {e}")
            except FileNotFoundError:
                print(f"Error: Could not find alass executable at {alass_path}")
                sys.exit(1)
        else:
            print(f"No subtitle file found for {episode_code}")

def main():
    parser = argparse.ArgumentParser(description='Sync subtitles with video files using alass')
    parser.add_argument('video_dir', help='Directory containing video files')
    parser.add_argument('subs_dir', help='Directory containing subtitle files')
    parser.add_argument('output_dir', help='Directory for synced subtitle files')
    parser.add_argument('--alass', default='alass', 
                        help='Path to alass executable (default: searches in PATH)')
    
    args = parser.parse_args()
    
    # Convert to absolute paths
    video_dir = os.path.abspath(args.video_dir)
    subs_dir = os.path.abspath(args.subs_dir)
    output_dir = os.path.abspath(args.output_dir)
    alass_path = os.path.expanduser(args.alass)  # Expand ~ to home directory
    
    # Check if directories exist
    if not os.path.isdir(video_dir):
        print(f"Error: Video directory '{video_dir}' does not exist")
        sys.exit(1)
    if not os.path.isdir(subs_dir):
        print(f"Error: Subtitles directory '{subs_dir}' does not exist")
        sys.exit(1)
        
    sync_subtitles(video_dir, subs_dir, output_dir, alass_path)

if __name__ == "__main__":
    main()
