#!/usr/bin/env python3
import sys
from pathlib import Path
import json
import boto3
from botocore.exceptions import ClientError
from tqdm import tqdm
import hashlib
import os
from typing import Dict, List, Set
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables from .env
env_path = Path(project_root) / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

from config.settings import get_settings

class MigrationVerifier:
    def __init__(self):
        self.settings = get_settings()
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )
        self.clips_dir = Path(project_root).parent / "data" / "processed" / "clips"
        self.progress_file = Path("migration_progress.json")
        self.verification_file = Path("migration_verification.json")
        self.uploaded_files: Dict[str, str] = self._load_progress()
        self.verified_clips: Set[str] = set()
        self.failed_clips: Set[str] = set()
        self.missing_clips: Set[str] = set()

    def _load_progress(self) -> Dict[str, str]:
        """Load progress from migration attempts"""
        if self.progress_file.exists():
            with open(self.progress_file, "r") as f:
                return json.load(f)
        return {}

    def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 hash of file"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _get_s3_key(self, file_path: Path) -> str:
        """Generate S3 key for file"""
        relative_path = file_path.relative_to(self.clips_dir)
        return f"clips/{relative_path}"

    async def verify_upload(self, file_path: Path) -> bool:
        """Verify uploaded file matches local file"""
        try:
            s3_key = self._get_s3_key(file_path)
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

    async def verify_all_uploads(self):
        """Verify all local clips are in S3"""
        print("\nScanning local clips directory...")
        local_clips = list(self.clips_dir.rglob("*.mp4"))
        print(f"Found {len(local_clips)} local clips")
        
        # Create progress bar
        pbar = tqdm(total=len(local_clips), desc="Verifying clips")
        
        # Verify each local clip
        for clip_path in local_clips:
            if await self.verify_upload(clip_path):
                self.verified_clips.add(str(clip_path))
            else:
                # Check if it was in the progress file
                if str(clip_path) in self.uploaded_files:
                    self.failed_clips.add(str(clip_path))
                else:
                    self.missing_clips.add(str(clip_path))
            pbar.update(1)
        
        pbar.close()

        # Save verification results
        verification_results = {
            "verified_clips": list(self.verified_clips),
            "failed_clips": list(self.failed_clips),
            "missing_clips": list(self.missing_clips),
            "total_local_clips": len(local_clips),
            "verified_count": len(self.verified_clips),
            "failed_count": len(self.failed_clips),
            "missing_count": len(self.missing_clips)
        }

        with open(self.verification_file, "w") as f:
            json.dump(verification_results, f, indent=2)

        # Print summary
        print("\nVerification complete!")
        print(f"Total local clips: {len(local_clips)}")
        print(f"Successfully verified in S3: {len(self.verified_clips)}")
        print(f"Failed verification: {len(self.failed_clips)}")
        print(f"Missing from S3: {len(self.missing_clips)}")
        
        if self.failed_clips:
            print("\nFailed clips (first 10):")
            for clip in list(self.failed_clips)[:10]:
                print(f"- {clip}")
            if len(self.failed_clips) > 10:
                print(f"... and {len(self.failed_clips) - 10} more")

        if self.missing_clips:
            print("\nMissing clips (first 10):")
            for clip in list(self.missing_clips)[:10]:
                print(f"- {clip}")
            if len(self.missing_clips) > 10:
                print(f"... and {len(self.missing_clips) - 10} more")

        print(f"\nVerification results saved to: {self.verification_file}")

async def main():
    verifier = MigrationVerifier()
    await verifier.verify_all_uploads()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 