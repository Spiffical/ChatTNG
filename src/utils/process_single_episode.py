import argparse
from pathlib import Path
import sys

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

from src.extraction.extract_video_clips import process_episode

def process_single_episode(season: int, episode: int, video_dir: str, subtitles_dir: str, 
                         scripts_dir: str, output_dir: str, padding_before: float = 0.1, 
                         padding_after: float = 0.1):
    # Construct file paths
    episode_code = f"S{season:02d}E{episode:02d}"
    video_path = Path(video_dir) / f"{episode_code}.mkv"
    subtitle_path = Path(subtitles_dir) / f"{episode_code}.srt"
    script_path = Path(scripts_dir) / f"{episode_code}.txt"
    
    # Verify files exist
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        return
    if not subtitle_path.exists():
        print(f"Subtitle file not found: {subtitle_path}")
        return
    if not script_path.exists():
        print(f"Script file not found: {script_path}")
        return
    
    print(f"Processing {episode_code}...")
    process_episode(
        str(video_path),
        str(subtitle_path),
        str(script_path),
        output_dir,
        padding_before,
        padding_after,
        force=True  # Always force processing
    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process a single episode')
    parser.add_argument('season', type=int, help='Season number')
    parser.add_argument('episode', type=int, help='Episode number')
    parser.add_argument('--video_dir', default='data/raw/videos', help='Directory containing video files')
    parser.add_argument('--subtitles_dir', default='data/raw/subtitles/srt', help='Directory containing subtitle files')
    parser.add_argument('--scripts_dir', default='data/raw/scripts', help='Directory containing script files')
    parser.add_argument('--output_dir', default='data/processed/clips', help='Directory to save extracted clips')
    parser.add_argument('--padding_before', type=float, default=0.1, help='Padding before each clip (seconds)')
    parser.add_argument('--padding_after', type=float, default=0.1, help='Padding after each clip (seconds)')
    
    args = parser.parse_args()
    
    process_single_episode(
        args.season,
        args.episode,
        args.video_dir,
        args.subtitles_dir,
        args.scripts_dir,
        args.output_dir,
        args.padding_before,
        args.padding_after
    ) 