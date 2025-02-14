#!/usr/bin/env python3
import boto3
import os
from pathlib import Path
import mimetypes

def upload_subtitles(clips_dir: str, bucket_name: str):
    """Upload SRT files to S3 bucket"""
    s3 = boto3.client('s3')
    
    # Walk through clips directory
    clips_path = Path(clips_dir)
    for srt_file in clips_path.rglob('*.srt'):
        # Get relative path from clips directory
        relative_path = srt_file.relative_to(clips_path)
        s3_key = f"clips/{relative_path}"
        
        print(f"Uploading {srt_file} to s3://{bucket_name}/{s3_key}")
        
        # Upload file with correct content type
        s3.upload_file(
            str(srt_file),
            bucket_name,
            s3_key,
            ExtraArgs={
                'ContentType': 'application/x-subrip',
                'CacheControl': 'max-age=31536000'  # 1 year cache
            }
        )

if __name__ == "__main__":
    clips_dir = "data/processed/clips"
    bucket_name = "chattng-clips"  # Replace with your bucket name
    
    upload_subtitles(clips_dir, bucket_name) 