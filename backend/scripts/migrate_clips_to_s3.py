#!/usr/bin/env python3
import sys
from pathlib import Path
import json
import asyncio
from typing import Dict, List
import boto3
from botocore.exceptions import ClientError
from tqdm import tqdm
import hashlib
import os
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables from .env file
env_path = Path(project_root) / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

from config.settings import get_settings

class ClipMigrator:
    def __init__(self):
        self.settings = get_settings()
        # Debug print
        print("Loaded settings:")
        print(f"AWS Access Key ID: {self.settings.aws_access_key_id}")
        print(f"AWS Secret Key: {'*' * 8 if self.settings.aws_secret_access_key else None}")
        print(f"S3 Bucket: {self.settings.s3_bucket}")
        print(f"Project root: {project_root}")
        print(f"Current working directory: {os.getcwd()}")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key
        )
        self.progress_file = Path("migration_progress.json")
        self.clips_dir = Path(project_root).parent / "data" / "processed" / "clips"
        self.uploaded_files: Dict[str, str] = self._load_progress()

    def _load_progress(self) -> Dict[str, str]:
        """Load progress from previous migration attempts"""
        if self.progress_file.exists():
            with open(self.progress_file, "r") as f:
                return json.load(f)
        return {}

    def _save_progress(self):
        """Save migration progress"""
        with open(self.progress_file, "w") as f:
            json.dump(self.uploaded_files, f, indent=2)

    def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 hash of file"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _get_s3_key(self, file_path: Path) -> str:
        """Generate S3 key for file"""
        # Keep the same directory structure as local
        relative_path = file_path.relative_to(self.clips_dir)
        return f"clips/{relative_path}"

    async def verify_upload(self, file_path: Path, s3_key: str) -> bool:
        """Verify uploaded file matches local file"""
        try:
            # Get S3 object metadata
            response = self.s3_client.head_object(
                Bucket=self.settings.s3_bucket,
                Key=s3_key
            )
            
            # Compare ETag (MD5 hash) with local file
            s3_md5 = response['ETag'].strip('"')
            local_md5 = self._calculate_md5(file_path)
            
            return s3_md5 == local_md5
        except ClientError:
            return False

    async def upload_file(self, file_path: Path) -> bool:
        """Upload a single file to S3"""
        s3_key = self._get_s3_key(file_path)
        
        try:
            # Upload file with metadata
            self.s3_client.upload_file(
                str(file_path),
                self.settings.s3_bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': 'video/mp4',
                    'CacheControl': 'max-age=31536000'  # 1 year cache
                }
            )
            
            # Verify upload
            if await self.verify_upload(file_path, s3_key):
                self.uploaded_files[str(file_path)] = s3_key
                self._save_progress()
                return True
            
            return False
            
        except Exception as e:
            print(f"Error uploading {file_path}: {str(e)}")
            return False

    def get_clip_files(self) -> List[Path]:
        """Get all clip files that need to be uploaded"""
        all_clips = list(self.clips_dir.rglob("*.mp4"))
        return [
            clip for clip in all_clips 
            if str(clip) not in self.uploaded_files
        ]

    async def migrate_clips(self):
        """Migrate all clips to S3"""
        # Check AWS credentials
        if not all([
            self.settings.aws_access_key_id,
            self.settings.aws_secret_access_key
        ]):
            print("Error: AWS credentials not configured")
            print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
            return

        # Get clips to upload
        clips = self.get_clip_files()
        if not clips:
            print("No new clips to upload")
            return

        print(f"Found {len(clips)} clips to upload")
        
        # Create progress bar
        pbar = tqdm(total=len(clips), desc="Uploading clips")
        
        # Upload clips
        for clip in clips:
            success = await self.upload_file(clip)
            if success:
                pbar.update(1)
            else:
                print(f"\nFailed to upload {clip}")
        
        pbar.close()
        
        # Print summary
        print("\nMigration complete!")
        print(f"Successfully uploaded: {len(self.uploaded_files)} clips")
        failed = len(clips) - len(self.uploaded_files)
        if failed > 0:
            print(f"Failed to upload: {failed} clips")

async def main():
    migrator = ClipMigrator()
    await migrator.migrate_clips()

if __name__ == "__main__":
    asyncio.run(main()) 