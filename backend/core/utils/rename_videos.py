import argparse
from pathlib import Path
import re

def extract_season_episode(filename):
    """Extract season and episode numbers from filename"""
    pattern = r'S(\d{2})E(\d{2})'
    match = re.search(pattern, filename, re.IGNORECASE)
    if match:
        return f"S{match.group(1)}E{match.group(2)}"
    return None

def rename_videos(input_dir):
    """Rename video files to season and episode format"""
    input_dir = Path(input_dir)
    
    # List all video files
    video_files = []
    for ext in ['.mkv', '.mp4', '.avi']:
        video_files.extend(input_dir.glob(f'*{ext}'))
    
    if not video_files:
        print(f"No video files found in {input_dir}")
        return
    
    print(f"Found {len(video_files)} video files")
    renamed = 0
    failed = 0
    
    for video_file in sorted(video_files):
        season_episode = extract_season_episode(video_file.name)
        if season_episode:
            new_name = video_file.parent / f"{season_episode}{video_file.suffix}"
            try:
                video_file.rename(new_name)
                print(f"Renamed: {video_file.name} -> {new_name.name}")
                renamed += 1
            except Exception as e:
                print(f"Error renaming {video_file.name}: {e}")
                failed += 1
        else:
            print(f"Could not extract season/episode from: {video_file.name}")
            failed += 1
    
    print(f"\nRenaming complete:")
    print(f"Successfully renamed: {renamed}")
    print(f"Failed: {failed}")

def main():
    parser = argparse.ArgumentParser(description='Rename video files to season/episode format')
    parser.add_argument('input_dir', help='Directory containing video files')
    args = parser.parse_args()
    
    rename_videos(args.input_dir)

if __name__ == '__main__':
    main()
