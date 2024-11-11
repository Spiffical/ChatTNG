from pathlib import Path
import sys
import argparse

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

from src.search.dialog_storage import DialogStorage

def remove_episode(config_path: str, season: int, episode: int):
    # Initialize storage
    storage = DialogStorage(config_path)
    
    # Create where clause for the specific episode
    where_clause = {
        "$and": [
            {"season": {"$eq": season}},
            {"episode": {"$eq": episode}}
        ]
    }
    
    # Get all dialogs for this episode
    episode_dialogs = storage.collection.get(where=where_clause)
    
    if not episode_dialogs or not episode_dialogs['ids']:
        print(f"No dialogs found for S{season:02d}E{episode:02d}")
        return
    
    # Delete all dialogs for this episode
    storage.collection.delete(ids=episode_dialogs['ids'])
    print(f"Removed {len(episode_dialogs['ids'])} dialogs from S{season:02d}E{episode:02d}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Remove specific episode from ChromaDB')
    parser.add_argument('season', type=int, help='Season number')
    parser.add_argument('episode', type=int, help='Episode number')
    parser.add_argument('--config', default='config/app_config.yaml', help='Path to config file')
    
    args = parser.parse_args()
    remove_episode(args.config, args.season, args.episode)
