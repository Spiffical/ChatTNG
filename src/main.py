import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

# Now imports will work
from src.search.llm_interface import LLMInterface
from src.playback.video_player import VideoPlayer
from src.modes.auto_dialog import AutoDialogMode
from src.modes.interactive_mode import InteractiveMode
import argparse

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='Star Trek TNG Dialog Interactive System')
    parser.add_argument('--config', required=True, help='Path to config file')
    parser.add_argument('--mode', required=True, help='Mode to run: auto_dialog or interactive')
    args = parser.parse_args()

    # Initialize components
    interface = LLMInterface(args.config)
    player = VideoPlayer()
    
    # Check if auto-dialog mode is enabled in config
    auto_dialog_enabled = interface.config.get('modes', {}).get('auto_dialog', {}).get('enabled', False)
    
    if auto_dialog_enabled and args.mode == 'auto_dialog':
        # Run auto-dialog mode
        auto_mode = AutoDialogMode(interface, player, interface.config)
        auto_mode.run()
    else:
        # Run interactive mode
        interactive_mode = InteractiveMode(interface, player, interface.config)
        interactive_mode.run()

if __name__ == '__main__':
    main()
