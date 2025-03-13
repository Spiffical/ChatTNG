#!/usr/bin/env python3

import boto3
import subprocess
import json
import os
from typing import Dict, Optional
import logging
from botocore.exceptions import ClientError
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from env/.env file
env_path = Path(__file__).parents[2] / 'env' / 'production' /'.env.backend'
if env_path.exists():
    logger.info(f"Loading environment variables from {env_path}")
    load_dotenv(env_path)
else:
    logger.error(f"Environment file not found at {env_path}")
    exit(1)

def get_s3_client():
    """Create an S3 client with credentials from environment variables."""
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
        
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name='us-east-1'
    )

def download_from_s3(bucket: str, key: str, local_path: str) -> bool:
    """Download a file from S3 to local storage."""
    try:
        s3_client = get_s3_client()
        logger.info(f"Downloading {key} from bucket {bucket}")
        s3_client.download_file(bucket, key, local_path)
        return True
    except ClientError as e:
        logger.error(f"Error downloading from S3: {str(e)}")
        return False

def analyze_audio_encoding(file_path: str) -> Optional[Dict]:
    """
    Analyze the audio encoding of a video file using FFmpeg.
    Returns a dictionary with audio stream information.
    """
    try:
        # FFprobe command to get stream information in JSON format
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-select_streams', 'a',  # Only select audio streams
            file_path
        ]
        
        # Run FFprobe and capture output
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFprobe error: {result.stderr}")
            return None
            
        # Parse JSON output
        probe_data = json.loads(result.stdout)
        
        if not probe_data.get('streams'):
            logger.warning("No audio streams found in the file")
            return None
            
        # Get the first audio stream
        audio_stream = probe_data['streams'][0]
        
        # Extract relevant information
        audio_info = {
            'codec': audio_stream.get('codec_name'),
            'codec_long_name': audio_stream.get('codec_long_name'),
            'sample_rate': audio_stream.get('sample_rate'),
            'channels': audio_stream.get('channels'),
            'bit_rate': audio_stream.get('bit_rate'),
            'duration': audio_stream.get('duration'),
            'tags': audio_stream.get('tags', {})
        }
        
        return audio_info
        
    except Exception as e:
        logger.error(f"Error analyzing audio: {str(e)}")
        return None

def main():
    """Main function to download and analyze a video from S3."""
    # Check required environment variables
    required_vars = ['S3_BUCKET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please ensure your .env file contains S3_BUCKET and VIDEO_KEY")
        return
    
    bucket = os.getenv('S3_BUCKET')
    video_key = "clips/S03E19/S03E19_clip_0103_s01.mp4"
    
    # Create temporary directory if it doesn't exist
    temp_dir = '/tmp/video_analysis'
    os.makedirs(temp_dir, exist_ok=True)
    
    # Local path for downloaded video
    local_path = os.path.join(temp_dir, os.path.basename(video_key))
    
    try:
        # Download video from S3
        if not download_from_s3(bucket, video_key, local_path):
            logger.error("Failed to download video from S3")
            return
            
        # Analyze audio encoding
        audio_info = analyze_audio_encoding(local_path)
        
        if audio_info:
            logger.info("Audio Stream Information:")
            logger.info(json.dumps(audio_info, indent=2))
            
            # Check if audio codec is iOS compatible
            codec = audio_info.get('codec', '').lower()
            if codec == 'aac':
                logger.info("✅ Audio codec is iOS compatible (AAC)")
            else:
                logger.warning(f"⚠️ Audio codec ({codec}) may need transcoding for iOS compatibility")
        else:
            logger.error("Failed to analyze audio encoding")
            
    finally:
        # Cleanup: remove downloaded file
        if os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"Cleaned up temporary file: {local_path}")

if __name__ == "__main__":
    main() 