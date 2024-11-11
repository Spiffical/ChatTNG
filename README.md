# ChatTNG

This system extracts dialog clips from Star Trek: The Next Generation episodes by matching script text with subtitle timings, and creates an interactive dialog system powered by OpenAI's GPT models, allowing you to chat directly with the characters of Star Trek: The Next Generation.

## Prerequisites

- Python 3.8+
- FFmpeg
- MPV player
- OpenAI API key
- [Alass](https://github.com/kaegi/alass) subtitle synchronization tool
- Video files, subtitles, and episode scripts for Star Trek: TNG

## Installation

1. Clone the repository and create a virtual environment:

```bash
git clone <repository-url>
cd star-trek-dialog-system
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install required packages:

```bash
pip install -r requirements.txt
```

3. Edit the configuration file:

Edit `config/app_config_placeholder.yaml` to set the paths to your video files, subtitles, scripts, and other resources, and include your OpenAI API key.
```

## Data Preparation

1. Organize your video files in `path/to/videos` with format `S01E01.mkv`

2. Download episode scripts:
```bash
python src/scripts/download_scripts.py path/to/save/scripts
```

3. Extract subtitles from video files:
```bash
python src/utils/extract_subtitles.py path/to/videos --output_dir path/to/subtitles
```

4. Synchronize subtitles with video (if needed):
```bash
python src/extraction/sync_subtitles.py \
    path/to/videos \
    path/to/subtitles \
    path/to/save/synced/subtitles \
    --alass /path/to/alass
```

## Processing Pipeline

1. Extract video clips by matching scripts with subtitles:
```bash
python src/extraction/extract_video_clips.py \
    path/to/videos \
    path/to/subtitles \
    path/to/scripts \
    path/to/save/clips \
    --padding_before 0.1 \
    --padding_after 0.1
```

The following is not needed but can be used to test the clip extraction:

2. Test clip extraction for a single episode:
```bash
python src/utils/process_single_episode.py 1 1 \
    --video_dir path/to/videos \
    --subtitles_dir path/to/subtitles \
    --scripts_dir path/to/scripts \
    --output_dir path/to/save/clips
```

3. Check dialog alignment:
```bash
python src/utils/check_episode_alignment.py --config config/app_config.yaml
```

## Running the System

1. Run the main application:
```bash
python src/main.py --config config/app_config.yaml --mode interactive
# or
python src/main.py --config config/app_config.yaml --mode auto_dialog
```

The system supports two modes:
- `interactive`: Chat with the system using Star Trek dialog
- `auto_dialog`: Watch the system have conversations with itself

## Testing

Test various components:

1. Test video playback:
```bash
python src/test/test_video_playback.py path/to/clips
```

2. Test dialog collection:
```bash
python src/test/test_dialog_collection.py
```

3. Inspect ChromaDB contents:
```bash
python src/test/test_chroma_db.py --config config/app_config.yaml
```

## Project Structure

```
.
├── config/                 # Configuration files
├── data/
│   ├── raw/               # Original videos, scripts, and subtitles
│   └── processed/         # Extracted clips and metadata
├── src/
│   ├── extraction/        # Video and dialog extraction
│   ├── modes/             # Interactive and auto-dialog modes
│   ├── playback/          # Video playback handling
│   ├── search/            # Dialog search and matching
│   ├── scripts/           # Utility scripts
│   ├── test/             # Test modules
│   └── utils/            # Helper utilities
└── README.md
```

## Notes

- Make sure video files, subtitles, and scripts follow the naming convention `S01E01`
- The system requires significant disk space for storing video clips
- Processing all episodes can take several hours depending on your hardware
- Keep your OpenAI API key secure and monitor usage

## Troubleshooting

- If clips are misaligned, use the alignment checker and reprocess problematic episodes
- For subtitle sync issues, try using Alass with different parameters (sometimes Alass fails to sync subtitles and it's best to use the raw srt subtitles)
- Monitor the ChromaDB storage size and clean up if needed

For more detailed information about specific components, refer to the source code documentation.