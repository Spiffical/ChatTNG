from dataclasses import dataclass
from typing import List
import re

@dataclass
class DialogSegment:
    speaker: str
    text: str
    scene_info: str = ""
    position: int = 0

class ScriptParser:
    def __init__(self):
        self.dialog_segments: List[DialogSegment] = []
        
    def parse_script(self, script_path: str) -> List[DialogSegment]:
        with open(script_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"\nProcessing {len(lines)} lines...")
        
        current_speaker = None
        current_text = []
        
        for line in lines:
            # Clean the line and remove any text within brackets, including parentheses
            line = re.sub(r'[\[\(].*?[\]\)]', '', line).strip()
            if not line:
                continue
                
            # Check for Captain's Log entries
            if line.lower().startswith("captain's log"):
                if current_speaker and current_text:
                    self._add_dialog(current_speaker, current_text)
                current_speaker = "PICARD"
                current_text = [line]
                continue
            
            # Check for new speaker (all caps followed by colon)
            speaker_match = re.match(r'^([A-Z][A-Z\s]+?)(?:\s*[\[\(].*?[\]\)])*\s*:\s*(.*)$', line)
            if speaker_match:
                # Save previous dialog if exists
                if current_speaker and current_text:
                    self._add_dialog(current_speaker, current_text)
                    
                # Start new dialog
                current_speaker = speaker_match.group(1).strip()
                dialog_text = speaker_match.group(2)
                # Clean any remaining bracketed text from dialog
                dialog_text = re.sub(r'[\[\(].*?[\]\)]', '', dialog_text).strip()
                # Only add non-empty dialog text
                current_text = [dialog_text] if dialog_text else []
            
            # If no speaker match, add to current dialog
            elif current_speaker:
                # Clean any remaining bracketed text
                cleaned_line = re.sub(r'[\[\(].*?[\]\)]', '', line).strip()
                if cleaned_line:
                    current_text.append(cleaned_line)
        
        # Add final dialog if exists
        if current_speaker and current_text:
            self._add_dialog(current_speaker, current_text)
            
        print(f"\nFound {len(self.dialog_segments)} dialog segments")
        return self.dialog_segments
    
    def _add_dialog(self, speaker: str, text_lines: List[str]):
        """Helper method to add a dialog segment after cleaning"""
        # Join text lines
        text = ' '.join(text_lines).strip()
        
        # Split on any new speaker patterns
        speaker_pattern = r'([A-Z\-]+\s*:)'
        segments = re.split(speaker_pattern, text)
        
        # Clean first segment for current speaker
        first_segment = segments[0]
        first_segment = re.sub(r'[\[\(].*?[\]\)]', '', first_segment).strip()
        
        if first_segment:
            self.dialog_segments.append(DialogSegment(
                speaker=speaker.strip(),
                text=first_segment,
                position=len(self.dialog_segments)  # Add position
            ))
        
        # Handle any additional speakers found in the text
        for i in range(1, len(segments)-1, 2):
            next_speaker = segments[i].strip(':').strip()
            next_text = re.sub(r'[\[\(].*?[\]\)]', '', segments[i+1]).strip()
            
            if next_text:
                self.dialog_segments.append(DialogSegment(
                    speaker=next_speaker,
                    text=next_text,
                    position=len(self.dialog_segments)  # Add position
                ))
