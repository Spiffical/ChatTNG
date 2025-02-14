import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException
import os
from typing import Optional
import time
import hashlib
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ClipService:
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        s3_bucket: str = "chattng-clips",
        cloudfront_domain: Optional[str] = None,
        cloudfront_key_pair_id: Optional[str] = None,
        cloudfront_private_key_path: Optional[str] = None
    ):
        """Initialize clip service with AWS credentials and configuration"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        self.s3_bucket = s3_bucket
        self.cloudfront_domain = cloudfront_domain or os.getenv("CLOUDFRONT_DOMAIN", "d2qqs9uhgc4wdq.cloudfront.net")
        self.cloudfront_key_pair_id = cloudfront_key_pair_id
        self.cloudfront_private_key_path = cloudfront_private_key_path
        self.clip_base_path = "clips"

    async def get_clip_url(self, clip_path: str) -> str:
        """Generate CloudFront URL for clip"""
        try:
            # Ensure clip path is relative
            relative_path = clip_path.replace("data/processed/clips/", "")
            
            # Validate the clip exists in S3 before returning URL
            try:
                self.s3_client.head_object(
                    Bucket=self.s3_bucket,
                    Key=f"{self.clip_base_path}/{relative_path}"
                )
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    raise ValueError(f"Clip not found in S3: {relative_path}")
                else:
                    raise
            
            # Generate CloudFront URL
            url = f"https://{self.cloudfront_domain}/{self.clip_base_path}/{relative_path}"
            
            return url
            
        except Exception as e:
            logger.error(f"Error generating clip URL: {str(e)}")
            raise HTTPException(
                status_code=404,
                detail=f"Error accessing clip: {str(e)}"
            )

    async def upload_clip(self, local_path: str, clip_id: str) -> str:
        """Upload a clip to S3"""
        try:
            # Generate S3 key
            s3_key = f"clips/{clip_id}/{os.path.basename(local_path)}"
            
            # Upload file
            with open(local_path, 'rb') as file:
                self.s3_client.upload_fileobj(
                    file,
                    self.s3_bucket,
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'video/mp4',
                        'CacheControl': 'max-age=31536000',  # 1 year cache
                        'AcceptRanges': 'bytes',  # Explicitly support range requests
                        'ContentDisposition': 'inline',  # Better streaming behavior
                    }
                )
            
            return s3_key
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error uploading clip: {str(e)}"
            )

    async def _get_s3_presigned_url(self, clip_path: str) -> str:
        """Generate a presigned S3 URL"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.s3_bucket,
                    'Key': clip_path
                },
                ExpiresIn=3600  # 1 hour
            )
            return url
        
        except ClientError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating S3 presigned URL: {str(e)}"
            )

    async def _get_cloudfront_url(self, clip_path: str) -> str:
        """Generate a signed CloudFront URL"""
        if not all([
            self.cloudfront_domain,
            self.cloudfront_key_pair_id,
            self.cloudfront_private_key_path
        ]):
            raise ValueError("CloudFront configuration incomplete")

        try:
            # Create CloudFront URL
            resource = f"https://{self.cloudfront_domain}/{clip_path}"
            
            # Set expiration time (1 hour from now)
            expire_time = int(time.time()) + 3600
            
            # Create policy
            policy = {
                'Statement': [{
                    'Resource': resource,
                    'Condition': {
                        'DateLessThan': {
                            'AWS:EpochTime': expire_time
                        }
                    }
                }]
            }

            # Sign URL using CloudFront private key
            # Note: In production, you'd want to use boto3's CloudFront signer
            # This is a simplified version
            return f"{resource}?Expires={expire_time}&Signature={self._sign_url(policy)}&Key-Pair-Id={self.cloudfront_key_pair_id}"
        
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating CloudFront signed URL: {str(e)}"
            )

    def _sign_url(self, policy: dict) -> str:
        """Sign a CloudFront URL (simplified version)"""
        # In production, use proper RSA signing
        # This is just a placeholder
        policy_str = str(policy)
        return hashlib.sha256(policy_str.encode()).hexdigest()

    def _hash_path(self, path: str) -> str:
        """Generate hash for cache key"""
        return hashlib.md5(path.encode()).hexdigest() 