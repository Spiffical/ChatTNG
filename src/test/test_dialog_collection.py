import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

from src.extraction.script_parser import ScriptParser

def test_character_dialog_collection():
    # Define path
    script_file = Path(project_root) / "data" / "raw" / "scripts" / "S02E05.txt"
    
    # Parse script
    parser = ScriptParser()
    script_segments = parser.parse_script(script_file)
    
    # Store dialog per character
    character_dialog = {}
    
    # Collect all dialog
    for segment in script_segments:
        if segment.text and segment.speaker:
            speaker = segment.speaker.strip().upper()  # Simple normalization
            if speaker not in character_dialog:
                character_dialog[speaker] = []
            character_dialog[speaker].append(segment.text)
    
    # Print summary
    print("\n=== Character Dialog Summary ===")
    print(f"Total unique characters found: {len(character_dialog)}\n")
    
    # Sort by number of lines (most to least)
    sorted_chars = sorted(character_dialog.items(), key=lambda x: len(x[1]), reverse=True)
    
    for character, lines in sorted_chars:
        print(f"{character:20} Lines: {len(lines):3d}")
        print("First line:", lines[0][:50] + "..." if len(lines[0]) > 50 else lines[0])
        print()

if __name__ == "__main__":
    test_character_dialog_collection() 