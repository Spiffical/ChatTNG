import argparse
from pathlib import Path
import sys

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

from src.playback.video_player import VideoPlayer

def list_clips(clips_dir: Path):
    """List all clips in the directory"""
    clips = sorted(clips_dir.glob('*.mp4'))
    if not clips:
        print(f"No clips found in {clips_dir}")
        return []
    
    print("\nAvailable clips:")
    for i, clip in enumerate(clips):
        # Check if corresponding subtitle file exists
        srt_file = clip.with_suffix('.srt')
        subtitle_status = "✓" if srt_file.exists() else "✗"
        print(f"{i}: {clip.name} [Subtitles: {subtitle_status}]")
    
    return clips

def main():
    parser = argparse.ArgumentParser(description='Test video playback with subtitles')
    parser.add_argument('clips_dir', help='Directory containing video clips')
    args = parser.parse_args()
    
    clips_dir = Path(args.clips_dir)
    if not clips_dir.exists():
        print(f"Directory not found: {clips_dir}")
        return
    
    player = VideoPlayer()
    
    while True:
        clips = list_clips(clips_dir)
        if not clips:
            break
            
        print("\nEnter clip number to play (or 'q' to quit):")
        choice = input("> ").strip().lower()
        
        if choice == 'q':
            break
            
        try:
            clip_idx = int(choice)
            if 0 <= clip_idx < len(clips):
                clip_path = clips[clip_idx]
                print(f"\nPlaying: {clip_path.name}")
                player.play_clip(str(clip_path))
            else:
                print("Invalid clip number")
        except ValueError:
            print("Please enter a valid number")
        except Exception as e:
            print(f"Error playing clip: {e}")
        
        print("\nPress Enter to continue...")
        input()

if __name__ == '__main__':
    main() 