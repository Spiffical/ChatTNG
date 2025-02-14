from rapidfuzz import fuzz
from typing import List, Dict, Any, Tuple, Optional
import pysrt
import re
from tqdm import tqdm
from .script_parser import DialogSegment
from backend.core.utils.text_utils import clean_dialog_text, split_into_sentences
from multiprocessing import Pool
import functools
import nltk
from difflib import SequenceMatcher

class DialogMatcher:
    def __init__(self, script_segments: List[DialogSegment], subtitles: pysrt.SubRipFile):
        self.script_segments = script_segments
        self.subtitles = subtitles
        self.cleaned_subtitles = []
        self.original_to_cleaned_map = {}
        
        for idx, sub in enumerate(subtitles):
            # Clean HTML tags first
            sub_text = re.sub(r'<[^>]+>', '', sub.text.strip())
            
            # Split on lines starting with dash
            lines = sub_text.split('\n')
            is_multi = len(lines) > 1 and all(line.strip().startswith('-') for line in lines)
            
            if is_multi:
                # Process each line separately but mark as multi-speaker
                for line in lines:
                    cleaned_line = line.strip().lstrip('- ')
                    cleaned = clean_dialog_text(cleaned_line)
                    self.cleaned_subtitles.append((sub, cleaned, True))
                    self.original_to_cleaned_map[idx] = cleaned
            else:
                # Single speaker - process normally
                cleaned = clean_dialog_text(sub_text)
                if cleaned:
                    self.cleaned_subtitles.append((sub, cleaned, False))
                    self.original_to_cleaned_map[idx] = cleaned
    
    def normalize_speaker(self, speaker: str) -> str:
        """Normalize speaker names to handle variations"""
        speaker = speaker.upper()
        
        # Common speaker variations
        if speaker in ['ETHAN', 'ETHAN/JEAN-LUC', 'JEAN-LUC']:
            return 'ETHAN'
        
        return speaker
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text for comparison"""
        text = text.lower()
        
        # Combine all text normalization
        text = text.replace("3", "three")
        text = re.sub(r'\([^)]*\)', '', text)  # Remove stage directions
        text = re.sub(r'<[^>]+>', '', text)    # Remove HTML
        text = re.sub(r'\[.*?\]', '', text)    # Remove brackets
        
        words = text.split()
        if len(words) <= 3:
            text = re.sub(r'[,;]', '', text)
        else:
            text = re.sub(r'[^\w\s\']', '', text)
        
        return ' '.join(text.split())
    
    def find_subtitle_group(self, script_text: str, start_idx: int, script_position: int = 0) -> Tuple[List[pysrt.SubRipItem], float, bool, int]:
        """Find a group of consecutive subtitles that match the script text"""
        best_ratio = 0
        best_group = []
        best_position = start_idx  # Track position of best match
        max_group_size = 8
        has_multi_speaker = False
        
        cleaned_script = self.clean_text(script_text)
        words = cleaned_script.split()
        
        # For very short phrases, we want to consider position more carefully
        is_short_phrase = len(words) <= 2
        
        for i in range(start_idx, min(start_idx + 100, len(self.cleaned_subtitles))):
            current_group = []
            combined_text = ""
            last_end_time = None
            current_has_multi = False
            
            # Get initial subtitle
            sub, cleaned_sub_text, is_multi = self.cleaned_subtitles[i]
            
            # Include multi-speaker lines but track their presence
            current_has_multi = is_multi
            
            # Check timing gap
            if last_end_time and (sub.start.ordinal - last_end_time.ordinal) > 2500:
                continue
            
            current_group.append(sub)
            combined_text = cleaned_sub_text
            last_end_time = sub.end
            
            # Modified ratio comparison for short phrases
            if is_short_phrase:
                ratio = fuzz.ratio(cleaned_script, combined_text) / 100.0
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_group = current_group.copy()
                    best_position = i
                    has_multi_speaker = current_has_multi
                elif ratio == best_ratio and abs(i - script_position) < abs(best_position - script_position):
                    # If equal ratio, prefer the match closer to the script position
                    best_group = current_group.copy()
                    best_position = i
                    has_multi_speaker = current_has_multi
            else:
                # Original ratio comparison for longer phrases
                ratio = fuzz.ratio(cleaned_script, combined_text) / 100.0
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_group = current_group.copy()
                    best_position = i
                    has_multi_speaker = current_has_multi
            
            # Try combining with subsequent subtitles
            for j in range(i + 1, min(i + max_group_size, len(self.cleaned_subtitles))):
                next_sub, next_cleaned_text, next_is_multi = self.cleaned_subtitles[j]
                
                # Check timing gap
                if (next_sub.start.ordinal - last_end_time.ordinal) > 2500:
                    break
                
                current_group.append(next_sub)
                current_has_multi = current_has_multi or next_is_multi
                
                # Handle ellipses when combining text
                if combined_text.endswith('...') and not next_cleaned_text.startswith('...'):
                    combined_text = combined_text.rstrip('.') + ' ' + next_cleaned_text
                else:
                    combined_text += ' ' + next_cleaned_text
                
                last_end_time = next_sub.end
                
                ratio = fuzz.ratio(cleaned_script, combined_text) / 100.0
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_group = current_group.copy()
                    has_multi_speaker = current_has_multi
                    
                    if ratio > 0.95:
                        break
        
        return best_group, best_ratio, has_multi_speaker, best_position
    
    def _match_single_segment(self, segment) -> Dict:
        """Process a single script segment - helper for parallel processing"""
        # Normalize the speaker name before processing
        normalized_speaker = self.normalize_speaker(segment.speaker)
        
        debug_output = []
        debug_output.append(f"\n{'='*80}")
        debug_output.append(f"Processing dialog segment:")
        debug_output.append(f"Speaker: {normalized_speaker}")  # Use normalized speaker
        debug_output.append(f"Complete text: {segment.text}")
        
        # First try to match the complete dialog
        complete_match = self._find_best_match(segment.text, segment.position)
        if complete_match:
            debug_output.append(f"\nComplete match found:")
            debug_output.append(f"Match ratio: {complete_match['match_ratio']:.2%}")
            debug_output.append(f"Subtitle text: {complete_match['subtitle_text']}")
            debug_output.append(f"Position difference: {abs(complete_match['position'] - segment.position)}")
        else:
            debug_output.append("\nNo complete match found")
        
        # Split into sentences and match each one
        sentences = split_into_sentences(segment.text)
        sentence_matches = []
        
        # Only do sentence matching if we have multiple sentences
        if len(sentences) > 1:
            debug_output.append(f"\nSplit into {len(sentences)} sentences:")
            
            for i, sentence in enumerate(sentences):
                debug_output.append(f"\nSentence {i+1}: {sentence}")
                sentence_match = self._find_best_match(sentence, segment.position)
                if sentence_match:
                    # Check if the matched subtitle contains multiple sentences
                    subtitle_sentences = split_into_sentences(sentence_match['subtitle_text'])
                    if len(subtitle_sentences) == 1:
                        debug_output.append(f"Found match with ratio: {sentence_match['match_ratio']:.2%}")
                        debug_output.append(f"Subtitle text: {sentence_match['subtitle_text']}")
                        debug_output.append(f"Position difference: {abs(sentence_match['position'] - segment.position)}")
                        sentence_matches.append(sentence_match)
                    else:
                        debug_output.append("Match found but subtitle contains multiple sentences - skipping")
                else:
                    debug_output.append("No match found")
        else:
            debug_output.append("\nSingle sentence dialog - skipping sentence matching")
        
        # Print all debug output at once
        # print('\n'.join(debug_output))
        
        # Return both complete and sentence-level matches
        return {
            'complete': complete_match,
            'sentences': sentence_matches,
            'speaker': normalized_speaker,  # Use normalized speaker
            'text': segment.text,
            'scene_info': segment.scene_info
        }

    def _find_best_match(self, text: str, script_position: int) -> Optional[Dict]:
        """Find the best matching subtitle group for a piece of text"""
        best_match_ratio = 0
        best_match_group = None
        has_multi_speaker = False
        best_position = 0
        
        # Search through ALL subtitles
        for i in range(len(self.cleaned_subtitles)):
            subtitle_group, match_ratio, is_multi, position = self.find_subtitle_group(text, i, script_position)
            
            # Skip multi-speaker subtitles
            if is_multi:
                continue
                
            if match_ratio > best_match_ratio:
                # Check for " - " in the combined text before accepting
                subtitle_text = ' '.join(sub.text for sub in subtitle_group)
                if ' - ' in subtitle_text:
                    continue
                    
                best_match_ratio = match_ratio
                best_match_group = subtitle_group
                has_multi_speaker = is_multi
                best_position = position
                
                if match_ratio > 0.95:
                    break
            
            # For very short phrases, if we have an equal match ratio, prefer the closer position
            elif match_ratio == best_match_ratio and len(text.split()) <= 2:
                if abs(position - script_position) < abs(best_position - script_position):
                    subtitle_text = ' '.join(sub.text for sub in subtitle_group)
                    if ' - ' not in subtitle_text or match_ratio > 0.85:
                        best_match_group = subtitle_group
                        has_multi_speaker = is_multi
                        best_position = position
        
        if best_match_group and best_match_ratio > 0.61:
            subtitle_text = ' '.join(sub.text for sub in best_match_group)
            return {
                'text': text,
                'subtitle_text': subtitle_text,
                'start_time': best_match_group[0].start,
                'end_time': best_match_group[-1].end,
                'match_ratio': best_match_ratio,
                'subtitle_group': best_match_group,
                'position': best_position
            }
        return None

    def match_dialog(self) -> List[Dict]:
        # Initialize NLTK data in main process
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        # Create a helper function that ensures NLTK data is available in worker process
        def init_worker():
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
        
        # Initialize pool with the worker initialization function
        with Pool(initializer=init_worker) as pool:
            results = list(tqdm(
                pool.imap_unordered(
                    functools.partial(self._match_single_segment),
                    self.script_segments,
                    chunksize=10
                ),
                total=len(self.script_segments),
                desc="Matching dialog"
            ))
        
        # Filter out results with no matches
        return [r for r in results if r['complete'] or r['sentences']]
