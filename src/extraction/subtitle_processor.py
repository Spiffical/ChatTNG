from dataclasses import dataclass
from typing import List
import pysrt
from pathlib import Path

@dataclass
class SubtitleSegment:
    text: str
    start_time: float
    end_time: float

class SubtitleExtractor:
    @staticmethod
    def extract_subtitle_segments(subtitle_group: List[pysrt.SubRipItem], clip_start_time: float) -> List[SubtitleSegment]:
        """Extract subtitle segments and adjust their timing relative to clip start"""
        segments = []
        clip_start_seconds = clip_start_time
        
        for sub in subtitle_group:
            # Convert subtitle times to seconds relative to clip start
            start_seconds = sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds + sub.start.milliseconds / 1000
            end_seconds = sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds + sub.end.milliseconds / 1000
            
            # Adjust timing relative to clip start
            adjusted_start = start_seconds - clip_start_seconds
            adjusted_end = end_seconds - clip_start_seconds
            
            segments.append(SubtitleSegment(
                text=sub.text,
                start_time=adjusted_start,
                end_time=adjusted_end
            ))
        
        return segments

    @staticmethod
    def save_subtitles(segments: List[SubtitleSegment], output_path: Path):
        """Save subtitle segments as SRT file"""
        subs = pysrt.SubRipFile()
        
        for i, segment in enumerate(segments, 1):
            # Convert seconds back to SubRipTime format
            start_hours = int(segment.start_time // 3600)
            start_minutes = int((segment.start_time % 3600) // 60)
            start_seconds = int(segment.start_time % 60)
            start_milliseconds = int((segment.start_time * 1000) % 1000)
            
            end_hours = int(segment.end_time // 3600)
            end_minutes = int((segment.end_time % 3600) // 60)
            end_seconds = int(segment.end_time % 60)
            end_milliseconds = int((segment.end_time * 1000) % 1000)
            
            sub = pysrt.SubRipItem(
                index=i,
                start=pysrt.SubRipTime(
                    hours=start_hours,
                    minutes=start_minutes,
                    seconds=start_seconds,
                    milliseconds=start_milliseconds
                ),
                end=pysrt.SubRipTime(
                    hours=end_hours,
                    minutes=end_minutes,
                    seconds=end_seconds,
                    milliseconds=end_milliseconds
                ),
                text=segment.text
            )
            subs.append(sub)
        
        subs.save(str(output_path), encoding='utf-8')
