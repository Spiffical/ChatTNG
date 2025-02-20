# ChatTNG

This system extracts dialog clips from Star Trek: The Next Generation episodes by matching script text with subtitle timings, and creates an interactive dialog system powered by Google's Gemini models, allowing you to chat directly with the characters of Star Trek: The Next Generation.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Data Preparation](#data-preparation)
- [Processing Pipeline](#processing-pipeline)
- [Running the System](#running-the-system)
- [How Character Chat Works](#how-character-chat-works)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Notes](#notes)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.8+
- [FFmpeg](https://ffmpeg.org/)
- [MPV player](https://mpv.io/)
- [Google Cloud API key](https://cloud.google.com/docs/authentication/api-keys)
- [Alass](https://github.com/kaegi/alass) subtitle synchronization tool
- Video files, subtitles, and episode scripts for Star Trek: TNG

## Installation

1. Clone the repository and create a virtual environment:

```bash
git clone git@github.com:Spiffical/ChatTNG.git
cd ChatTNG
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install required packages:

```bash
pip install -r requirements.txt
```

3. Edit the configuration file:

Edit `config/app_config_placeholder.yaml` to set the paths to your video files, subtitles, scripts, and other resources, and include your Google Cloud API key. Rename the file to `config/app_config.yaml`.

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

## How Character Chat Works

The ChatTNG system uses a sophisticated combination of technologies to create natural conversations with Star Trek: TNG characters:

### Dialog Processing
1. **Dialog Extraction**: The system extracts dialog from episodes by matching script text with subtitle timings (see `src/extraction/dialog_matcher.py`).
2. **Vector Database**: Dialogs are stored in ChromaDB with Gemini embeddings, enabling semantic search capabilities.
3. **Character Detection**: The system automatically detects which character should respond based on context and conversation flow.

### Conversation Flow
1. When you input text, the system:
   - Detects if a specific character should respond
   - Generates a contextually appropriate response using Gemini
   - Searches the vector database for similar actual show dialog
   - Selects the best matching dialog and plays the corresponding video clip

### Technical Components
- **Semantic Search**: Uses Google's Gemini embedding model for creating and matching dialog embeddings
- **Context Management**: Maintains conversation history for more coherent exchanges
- **Character Consistency**: Filters responses based on character-specific dialog patterns
- **Dialog Deduplication**: Prevents repetition by tracking used dialogs

### Modes
- **Interactive Mode**: Direct conversations with characters
- **Auto-Dialog**: Watch the system have conversations with itself using actual show dialog

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
chattng/
├── backend/                # Backend application code
├── frontend/              # Frontend application code
├── docker/                # Docker configurations
│   ├── backend/          # Backend Docker files
│   │   ├── Dockerfile.dev
│   │   ├── Dockerfile.prod
│   │   └── scripts/
│   ├── frontend/         # Frontend Docker files
│   │   ├── Dockerfile.dev
│   │   ├── Dockerfile.prod
│   │   └── scripts/
│   └── compose/          # Docker Compose files
├── deploy/               # Deployment configurations
│   ├── aws/             # AWS deployment
│   │   ├── apprunner/   # App Runner configs
│   │   ├── amplify/     # Amplify configs
│   │   └── scripts/     # AWS deployment scripts
│   └── local/           # Local deployment
│       └── scripts/     # Local environment scripts
├── env/                 # Environment configurations
│   ├── development/    # Development environment
│   └── production/     # Production environment
└── infrastructure/     # Infrastructure as Code
    └── terraform/     # Terraform configurations
```

## Notes

- Make sure video files, subtitles, and scripts follow the naming convention `S01E01`
- The system requires significant disk space for storing video clips
- Processing all episodes can take several hours depending on your hardware
- Keep your Google Cloud API key secure and monitor usage

## Troubleshooting

- If clips are misaligned, use the alignment checker and reprocess problematic episodes
- For subtitle sync issues, try using Alass with different parameters (sometimes Alass fails to sync subtitles and it's best to use the raw srt subtitles)
- Monitor the ChromaDB storage size and clean up if needed

For more detailed information about specific components, refer to the source code documentation.