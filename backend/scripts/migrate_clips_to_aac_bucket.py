#!/usr/bin/env python3
import sys
from pathlib import Path
import json
import asyncio
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError
from tqdm import tqdm
import hashlib
import os
from dotenv import load_dotenv
import argparse

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables from .env file
env_path = Path(project_root) / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

from config.settings import get_settings

class AACClipMigrator:
    def __init__(self, target_bucket: str):
        self.settings = get_settings()
        # Debug print
        print("Loaded settings:")
        print(f"AWS Access Key ID: {self.settings.aws_access_key_id}")
        print(f"AWS Secret Key: {'*' * 8 if self.settings.aws_secret_access_key else None}")
        print(f"AWS Region: {self.settings.aws_default_region}")
        print(f"Original S3 Bucket: {self.settings.s3_bucket}")
        print(f"Target S3 Bucket: {target_bucket}")
        print(f"Project root: {project_root}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Initialize S3 client with explicit region
        region = self.settings.aws_default_region or 'us-east-1'
        print(f"Initializing S3 client with region: {region}")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=region
        )
        self.target_bucket = target_bucket
        self.progress_file = Path("aac_migration_progress.json")
        self.clips_dir = Path(project_root).parent / "data" / "processed" / "clips"
        self.uploaded_files: Dict[str, str] = self._load_progress()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="aac_encoding_"))
        print(f"Using temporary directory: {self.temp_dir}")

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

    def analyze_audio_encoding(self, file_path: Path) -> Optional[Dict]:
        """Analyze the audio encoding of a video file using FFprobe."""
        try:
            # FFprobe command to get stream information in JSON format
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                '-select_streams', 'a',  # Only select audio streams
                str(file_path)
            ]
            
            # Run FFprobe and capture output
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"FFprobe error for {file_path}: {result.stderr}")
                return None
                
            # Parse JSON output
            probe_data = json.loads(result.stdout)
            
            if not probe_data.get('streams'):
                print(f"No audio streams found in {file_path}")
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
                'duration': audio_stream.get('duration')
            }
            
            return audio_info
            
        except Exception as e:
            print(f"Error analyzing audio for {file_path}: {str(e)}")
            return None

    def transcode_to_aac(self, input_file: Path) -> Tuple[Path, bool]:
        """Transcode video audio to AAC if it's not already AAC.
        Returns: (output_file_path, was_transcoded)
        """
        # First, analyze the audio
        audio_info = self.analyze_audio_encoding(input_file)
        
        # If analysis failed, return original file
        if not audio_info:
            print(f"⚠️ Could not analyze audio for {input_file}, will attempt transcoding anyway")
        # If audio is already AAC, return original file
        elif audio_info.get('codec', '').lower() == 'aac':
            print(f"✓ Audio already AAC for {input_file}, no transcoding needed")
            return input_file, False
        else:
            print(f"⚠️ Audio codec is {audio_info.get('codec')}, will transcode to AAC")
        
        # Create output file path
        output_file = self.temp_dir / f"aac_{input_file.name}"
        
        # FFmpeg command to transcode audio to AAC while copying video stream
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-i', str(input_file),
            '-c:v', 'copy',           # Copy video stream (no re-encoding)
            '-c:a', 'aac',            # Transcode audio to AAC
            '-b:a', '128k',           # Audio bitrate
            '-ac', '2',               # Force 2 audio channels (stereo)
            '-ar', '44100',           # Set audio sample rate to 44.1kHz (iOS compatible)
            '-movflags', 'faststart',  # Optimize for web playback
            str(output_file)
        ]
        
        print(f"Transcoding command: {' '.join(cmd)}")
        
        try:
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error transcoding {input_file}: {result.stderr}")
                return input_file, False
                
            # Verify the output was created and has AAC audio
            if not output_file.exists():
                print(f"Output file not created for {input_file}")
                return input_file, False
                
            # Verify the audio is now AAC
            new_audio_info = self.analyze_audio_encoding(output_file)
            if new_audio_info and new_audio_info.get('codec', '').lower() == 'aac':
                print(f"✓ Successfully transcoded {input_file} to AAC")
                return output_file, True
            else:
                print(f"Failed to verify AAC for {output_file}")
                return input_file, False
                
        except Exception as e:
            print(f"Exception during transcoding of {input_file}: {str(e)}")
            return input_file, False

    async def verify_upload(self, file_path: Path, s3_key: str) -> bool:
        """Verify uploaded file matches local file"""
        try:
            # Get S3 object metadata
            response = self.s3_client.head_object(
                Bucket=self.target_bucket,
                Key=s3_key
            )
            
            # Compare ETag (MD5 hash) with local file
            s3_md5 = response['ETag'].strip('"')
            local_md5 = self._calculate_md5(file_path)
            
            return s3_md5 == local_md5
        except ClientError:
            return False

    async def upload_file(self, file_path: Path) -> bool:
        """Upload a single file to S3, ensuring it has AAC audio"""
        try:
            # First, transcode the file if needed
            transcoded_file, was_transcoded = self.transcode_to_aac(file_path)
            
            # Get S3 key (same as original file path)
            s3_key = self._get_s3_key(file_path)
            
            # Upload file with metadata
            self.s3_client.upload_file(
                str(transcoded_file),
                self.target_bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': 'video/mp4',
                    'CacheControl': 'max-age=31536000',  # 1 year cache
                    'ContentDisposition': 'inline',  # Force inline display
                    'Metadata': {
                        'download-disabled': 'true',  # Custom metadata to indicate download is disabled
                        'aac-audio': 'true',  # Mark as having AAC audio
                        'transcoded': str(was_transcoded).lower()  # Mark if it was transcoded
                    }
                }
            )
            
            # Verify upload
            if await self.verify_upload(transcoded_file, s3_key):
                self.uploaded_files[str(file_path)] = s3_key
                self._save_progress()
                
                # Clean up temporary file if we created one
                if was_transcoded and transcoded_file.exists():
                    os.unlink(transcoded_file)
                
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

    async def ensure_bucket_exists(self):
        """Create the target S3 bucket if it doesn't exist"""
        try:
            # Print the AWS region being used
            print(f"Using AWS region: {self.s3_client.meta.region_name}")
            
            # Check if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=self.target_bucket)
                print(f"Bucket {self.target_bucket} already exists in region {self.s3_client.meta.region_name}")
                
                # List all buckets for verification
                response = self.s3_client.list_buckets()
                print("Available buckets in this account:")
                for bucket in response['Buckets']:
                    print(f"  - {bucket['Name']}")
                    
                return
            except ClientError as e:
                error_code = int(e.response['Error']['Code'])
                if error_code == 404:
                    # Bucket doesn't exist, create it
                    print(f"Creating bucket {self.target_bucket} in region {self.s3_client.meta.region_name}")
                    
                    try:
                        # For regions other than us-east-1, specify LocationConstraint
                        if self.s3_client.meta.region_name != "us-east-1":
                            print(f"Using LocationConstraint: {self.s3_client.meta.region_name}")
                            response = self.s3_client.create_bucket(
                                Bucket=self.target_bucket,
                                CreateBucketConfiguration={
                                    'LocationConstraint': self.s3_client.meta.region_name
                                }
                            )
                        else:
                            # For us-east-1, don't specify LocationConstraint
                            print("Creating bucket in us-east-1 (no LocationConstraint needed)")
                            response = self.s3_client.create_bucket(Bucket=self.target_bucket)
                        
                        print(f"Bucket creation response: {response}")
                        print(f"Bucket {self.target_bucket} created successfully")
                        
                        # List all buckets after creation to verify
                        response = self.s3_client.list_buckets()
                        print("Updated bucket list:")
                        for bucket in response['Buckets']:
                            print(f"  - {bucket['Name']}")
                            
                    except Exception as create_error:
                        print(f"Error creating bucket: {str(create_error)}")
                        raise
                else:
                    # Some other error
                    print(f"Error checking bucket: {e}")
                    raise
        except Exception as e:
            print(f"Unexpected error in ensure_bucket_exists: {str(e)}")
            raise

    async def migrate_clips(self):
        """Migrate all clips to S3 with AAC audio encoding"""
        # Check AWS credentials
        if not all([
            self.settings.aws_access_key_id,
            self.settings.aws_secret_access_key
        ]):
            print("Error: AWS credentials not configured")
            print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
            return

        # Ensure target bucket exists
        await self.ensure_bucket_exists()

        # Get clips to upload
        clips = self.get_clip_files()
        if not clips:
            print("No new clips to upload")
            return

        print(f"Found {len(clips)} clips to upload")
        
        # Create progress bar
        pbar = tqdm(total=len(clips), desc="Uploading clips with AAC audio")
        
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
        
        # Clean up the temporary directory
        try:
            os.rmdir(self.temp_dir)
            print(f"Removed temporary directory: {self.temp_dir}")
        except:
            print(f"Could not remove temporary directory: {self.temp_dir}")

async def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Migrate clips to a new S3 bucket with AAC audio')
    parser.add_argument('--bucket', type=str, help='Target S3 bucket name')
    parser.add_argument('--region', type=str, help='AWS region to create the bucket in')
    
    args = parser.parse_args()
    
    # Get settings
    settings = get_settings()
    
    # Get target bucket name from command line or default
    target_bucket = args.bucket or f"{settings.s3_bucket}-aac"
    
    # Get region from command line or default
    region = args.region or settings.aws_default_region or 'us-east-1'
    
    print(f"Migrating clips to bucket: {target_bucket} in region: {region}")
    
    # Update settings if region was provided
    if args.region:
        os.environ['AWS_DEFAULT_REGION'] = region
    
    # Create migrator
    migrator = AACClipMigrator(target_bucket)
    await migrator.migrate_clips()

if __name__ == "__main__":
    asyncio.run(main()) 