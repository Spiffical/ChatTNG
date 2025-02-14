import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

import pysrt
from backend.core.extraction.script_parser import ScriptParser
from backend.core.extraction.dialog_matcher import DialogMatcher

def test_extraction():
    # Define paths
    subtitles_file = Path(project_root) / "data" / "raw" / "subtitles" / "srt" / "S02E05.srt"
    script_file = Path(project_root) / "data" / "raw" / "scripts" / "S02E05.txt"
    
    # Load files quietly
    subs = pysrt.open(str(subtitles_file))
    parser = ScriptParser()
    script_segments = parser.parse_script(script_file)
    matcher = DialogMatcher(script_segments, subs)
    matched_segments = matcher.match_dialog()
    
    # Print summary statistics
    print("\n=== Summary Statistics ===")
    
    # Print matches with a ratio between 75% and 85%
    print("\n=== Matches with Ratio Between 75% and 85% ===")
    for segment in matched_segments:
        # Check complete match
        if segment['complete'] and 0.75 <= segment['complete']['match_ratio'] <= 0.85:
            print("\nComplete Match:")
            print(f"Speaker: {segment['speaker']}")
            print(f"Text: {segment['text']}")
            print(f"Match ratio: {segment['complete']['match_ratio']:.2%}")
            print("\nMatched Subtitles:")
            print(f"  {segment['complete']['subtitle_text']}")
            print(f"  Start: {segment['complete']['start_time']} End: {segment['complete']['end_time']}")
            print("-" * 80)
        
        # Check sentence matches
        for i, sentence_match in enumerate(segment['sentences']):
            if 0.75 <= sentence_match['match_ratio'] <= 0.85:
                print("\nSentence Match:")
                print(f"Speaker: {segment['speaker']}")
                print(f"Text: {sentence_match['text']}")
                print(f"Match ratio: {sentence_match['match_ratio']:.2%}")
                print("\nMatched Subtitles:")
                print(f"  {sentence_match['subtitle_text']}")
                print(f"  Start: {sentence_match['start_time']} End: {sentence_match['end_time']}")
                print("-" * 80)
    
    # Count total lines in script vs matched
    total_script_lines = len([s for s in script_segments if s.text and s.speaker])
    total_matched = len([s for s in matched_segments if s['complete'] or s['sentences']])
    print(f"\nScript dialog lines: {total_script_lines}")
    print(f"Matched dialog lines: {total_matched}")
    print(f"Missing dialog lines: {total_script_lines - total_matched}")
    
    # Count lines per character (both script and matched)
    script_char_counts = {}
    matched_char_counts = {}
    
    # Use the same speaker normalization for both script and matched segments
    for segment in script_segments:
        if segment.text and segment.speaker:
            normalized_speaker = matcher.normalize_speaker(segment.speaker)
            script_char_counts[normalized_speaker] = script_char_counts.get(normalized_speaker, 0) + 1
            
    for segment in matched_segments:
        if segment['complete']:
            speaker = segment['speaker']
            matched_char_counts[speaker] = matched_char_counts.get(speaker, 0) + 1
    
    print("\nDialog line comparison by character:")
    all_speakers = sorted(set(list(script_char_counts.keys()) + list(matched_char_counts.keys())))
    for speaker in all_speakers:
        script_count = script_char_counts.get(speaker, 0)
        matched_count = matched_char_counts.get(speaker, 0)
        print(f"{speaker:20} Script: {script_count:3d}  Matched: {matched_count:3d}  Missing: {script_count - matched_count:3d}")
    
    # Calculate match quality statistics
    match_ratios = []
    for segment in matched_segments:
        if segment['complete']:
            match_ratios.append(segment['complete']['match_ratio'])
        for sentence_match in segment['sentences']:
            match_ratios.append(sentence_match['match_ratio'])
    
    avg_match_ratio = sum(match_ratios) / len(match_ratios) if match_ratios else 0
    print(f"\nAverage match quality: {avg_match_ratio:.2%}")
    
    # Distribution of match ratios
    ratio_ranges = [(0.80, 0.85), (0.85, 0.90), (0.90, 0.95), (0.95, 1.0)]
    print("\nMatch ratio distribution:")
    for low, high in ratio_ranges:
        count = len([r for r in match_ratios if low <= r < high])
        print(f"{low:.2%} - {high:.2%}: {count:3d} matches")
        
    # # Print missing dialog lines with closest matches
    # print("\n=== Missing Dialog Lines with Closest Matches ===")
    # matched_text_set = {segment['text'] for segment in matched_segments}
    # for segment in script_segments:
    #     if segment.text and segment.speaker and segment.text not in matched_text_set:
    #         print(f"\nSpeaker: {segment.speaker}")
    #         print(f"Text: {segment.text}")
            
    #         # Find closest match
    #         closest_match = None
    #         highest_ratio = 0
    #         for matched in matched_segments:
    #             ratio = matcher.calculate_match_ratio(segment.text, matched['subtitle_text'])
    #             if ratio > highest_ratio:
    #                 highest_ratio = ratio
    #                 closest_match = matched
            
    #         if closest_match:
    #             print("\nClosest subtitle match:")
    #             print(f"Speaker: {closest_match['speaker']}")
    #             print(f"Text: {closest_match['subtitle_text']}")
    #             print(f"Match ratio: {highest_ratio:.2%}")
    #         print("-" * 40)

if __name__ == "__main__":
    test_extraction()
