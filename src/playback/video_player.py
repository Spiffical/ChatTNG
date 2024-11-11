import mpv
from pathlib import Path

class VideoPlayer:
    def __init__(self):
        self.player = None

    def create_player(self):
        """Create a new MPV player instance with video and audio effects"""
        return mpv.MPV(
            input_default_bindings=True,
            osc=True,
            sub_auto='exact',
            sub_visibility='yes',
            # Video fade filters
            vf="fade=in:0:25,fade=out:975:25",  # 25 frames = ~1 second at 24fps
            # Audio filters: fade in + dreamy effect
            af="afade=t=in:st=0:d=0.3,aecho=0.8:0.88:60:0.4,lowpass=f=3000"
        )

    def play_clip(self, clip_path: str):
        """Play a video clip file with subtitles"""
        try:
            # Create a fresh player instance for each clip
            self.player = self.create_player()
            
            # Convert path to absolute
            clip_path = str(Path(clip_path).resolve())
            
            # Play the video (MPV will auto-load the matching .srt file)
            self.player.play(clip_path)
            
            # Wait until playback is complete
            self.player.wait_for_playback()
            
        except Exception as e:
            print(f"Error playing clip: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Release resources"""
        if self.player:
            self.player.terminate()
            self.player = None
