import argparse
from pathlib import Path
import sys
import random
import yaml
from collections import defaultdict

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

from src.playback.video_player import VideoPlayer
from src.storage.dialog_storage import DialogStorage

def check_episode_alignment(config_path: str):
    # Initialize dialog storage
    storage = DialogStorage(config_path)
    
    # Get all entries from the collection
    results = storage.collection.get()
    
    if not results or not results['ids']:
        print("No entries found in the collection.")
        return
    
    # Group clips by episode
    episode_clips = defaultdict(list)
    for i, metadata in enumerate(results['metadatas']):
        episode_key = f"S{metadata['season']:02d}E{metadata['episode']:02d}"
        episode_clips[episode_key].append({
            'clip_path': metadata['clip_path'],
            'start_time': metadata['start_time'],
            'end_time': metadata['end_time'],
            'text': results['documents'][i]
        })
    
    # Initialize video player
    player = VideoPlayer()
    
    print(f"\nFound {len(episode_clips)} episodes with clips")
    print("Press Enter to play next clip, 'q' to quit, 'm' to mark episode as misaligned")
    misaligned_episodes = set()
    
    # Process each episode
    for episode in sorted(episode_clips.keys()):
        # Select a random clip from this episode
        clip_info = random.choice(episode_clips[episode])
        print(f"\nPlaying clip from {episode}")
        print(f"Dialog: {clip_info['text']}")
        print(f"Clip path: {clip_info['clip_path']}")
        
        # Play the clip
        player.play_clip(clip_info['clip_path'])
        
        # Get user input
        response = input("Press Enter for next clip, 'q' to quit, 'm' to mark as misaligned: ").lower()
        if response == 'q':
            break
        elif response == 'm':
            misaligned_episodes.add(episode)
    
    # Print summary of misaligned episodes
    if misaligned_episodes:
        print("\nMisaligned episodes:")
        for episode in sorted(misaligned_episodes):
            print(f"- {episode}")
        
        # Save to file
        output_file = Path(project_root) / "data" / "misaligned_episodes.txt"
        with open(output_file, 'w') as f:
            for episode in sorted(misaligned_episodes):
                f.write(f"{episode}\n")
        print(f"\nSaved misaligned episodes to: {output_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check episode dialog alignment')
    parser.add_argument('--config', default='config/app_config.yaml', help='Path to config file')
    args = parser.parse_args()
    
    check_episode_alignment(args.config)