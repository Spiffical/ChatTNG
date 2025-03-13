#!/usr/bin/env python3
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import json
from dotenv import load_dotenv
import os

# Add project root and backend to Python path
project_root = str(Path(__file__).resolve().parents[2])
backend_path = os.path.join(project_root, 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Load AWS environment variables
aws_env_path = Path(project_root) / 'env' / 'production' / '.env.aws'
load_dotenv(aws_env_path)

from config.settings import get_settings

class CloudFrontSetup:
    def __init__(self):
        self.settings = get_settings()
        self.cloudfront_client = boto3.client(
            'cloudfront',
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.aws_default_region
        )
        self.s3_bucket = self.settings.s3_bucket

    def create_distribution(self):
        """Create CloudFront distribution for S3 bucket"""
        try:
            # Origin configuration for S3
            origin_config = {
                'Origins': {
                    'Quantity': 1,
                    'Items': [{
                        'Id': f'S3-{self.s3_bucket}',
                        'DomainName': f'{self.s3_bucket}.s3.amazonaws.com',
                        'S3OriginConfig': {
                            'OriginAccessIdentity': ''  # Will be updated after OAI creation
                        }
                    }]
                }
            }

            # Create Origin Access Identity
            oai_response = self.cloudfront_client.create_cloud_front_origin_access_identity(
                CloudFrontOriginAccessIdentityConfig={
                    'CallerReference': f'{self.s3_bucket}-oai',
                    'Comment': f'OAI for {self.s3_bucket}'
                }
            )
            oai_id = oai_response['CloudFrontOriginAccessIdentity']['Id']
            origin_config['Origins']['Items'][0]['S3OriginConfig']['OriginAccessIdentity'] = f'origin-access-identity/cloudfront/{oai_id}'

            # Create response headers policy for CORS
            cors_policy_id = self._create_cors_headers_policy()

            # Create distribution
            response = self.cloudfront_client.create_distribution(
                DistributionConfig={
                    'CallerReference': f'{self.s3_bucket}-{hash(self.s3_bucket)}',
                    'Origins': origin_config['Origins'],
                    'DefaultCacheBehavior': {
                        'TargetOriginId': f'S3-{self.s3_bucket}',
                        'ForwardedValues': {
                            'QueryString': False,
                            'Cookies': {'Forward': 'none'},
                            'Headers': {
                                'Quantity': 4,
                                'Items': [
                                    'Origin',
                                    'Access-Control-Request-Headers',
                                    'Access-Control-Request-Method',
                                    'Accept'
                                ]
                            }
                        },
                        'TrustedSigners': {'Enabled': False, 'Quantity': 0},
                        'ViewerProtocolPolicy': 'redirect-to-https',
                        'MinTTL': 0,
                        'DefaultTTL': 86400,  # 24 hours
                        'MaxTTL': 31536000,  # 1 year
                        'Compress': True,
                        'AllowedMethods': {
                            'Quantity': 7,
                            'Items': ['GET', 'HEAD', 'OPTIONS', 'PUT', 'POST', 'PATCH', 'DELETE'],
                            'CachedMethods': {'Quantity': 2, 'Items': ['GET', 'HEAD']}
                        },
                        'ResponseHeadersPolicyId': cors_policy_id
                    },
                    'Comment': f'Distribution for {self.s3_bucket}',
                    'Enabled': True,
                    'DefaultRootObject': '',
                    'PriceClass': 'PriceClass_All',
                    'ViewerCertificate': {
                        'CloudFrontDefaultCertificate': True
                    },
                    'HttpVersion': 'http2',
                    'IsIPV6Enabled': True
                }
            )

            # Update S3 bucket policy
            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                region_name=self.settings.aws_default_region
            )

            # Get the canonical user ID for the CloudFront OAI
            oai_canonical_user_id = oai_response['CloudFrontOriginAccessIdentity']['S3CanonicalUserId']

            bucket_policy = {
                'Version': '2012-10-17',
                'Statement': [{
                    'Sid': 'CloudFrontAccess',
                    'Effect': 'Allow',
                    'Principal': {
                        'CanonicalUser': oai_canonical_user_id
                    },
                    'Action': 's3:GetObject',
                    'Resource': f'arn:aws:s3:::{self.s3_bucket}/*'
                }]
            }

            s3_client.put_bucket_policy(
                Bucket=self.s3_bucket,
                Policy=json.dumps(bucket_policy)
            )

            # Configure CORS for S3 bucket
            cors_configuration = {
                'CORSRules': [
                    {
                        'AllowedHeaders': ['*'],
                        'AllowedMethods': ['GET', 'HEAD'],
                        'AllowedOrigins': ['https://chattng-web.vercel.app', 'http://localhost:3000'],
                        'ExposeHeaders': ['ETag'],
                        'MaxAgeSeconds': 3000
                    }
                ]
            }
            s3_client.put_bucket_cors(
                Bucket=self.s3_bucket,
                CORSConfiguration=cors_configuration
            )

            # Save CloudFront domain to .env files
            domain_name = response['Distribution']['DomainName']
            self._update_env_files(domain_name)

            print(f"\nCloudFront distribution created successfully!")
            print(f"Domain Name: {domain_name}")
            print(f"Distribution ID: {response['Distribution']['Id']}")
            print("\nNOTE: It may take up to 15 minutes for the distribution to deploy")

        except ClientError as e:
            print(f"Error creating CloudFront distribution: {str(e)}")
            sys.exit(1)

    def _update_env_files(self, domain_name):
        """Update .env files with CloudFront domain"""
        env_files = [
            Path(project_root) / 'env' / 'production' / '.env.frontend',
            Path(project_root) / 'env' / 'development' / '.env.frontend'
        ]

        for env_path in env_files:
            if not env_path.exists():
                print(f"Warning: {env_path} not found")
                continue

            with open(env_path, 'r') as f:
                lines = f.readlines()

            # Update or add VITE_CLOUDFRONT_DOMAIN
            domain_found = False
            for i, line in enumerate(lines):
                if line.startswith('VITE_CLOUDFRONT_DOMAIN='):
                    lines[i] = f'VITE_CLOUDFRONT_DOMAIN={domain_name}\n'
                    domain_found = True
                    break

            if not domain_found:
                lines.append(f'\nVITE_CLOUDFRONT_DOMAIN={domain_name}\n')

            with open(env_path, 'w') as f:
                f.writelines(lines)
            print(f"Updated {env_path} with CloudFront domain")

    def _create_cors_headers_policy(self):
        """Get the AWS-managed CORS-with-preflight response headers policy"""
        try:
            # Use the AWS-managed CORS-with-preflight policy
            # This is a managed policy that enables CORS with preflight requests
            print("Using AWS-managed CORS-with-preflight policy")
            return "60669652-455b-4ae9-85a4-c4c02393f86c"  # AWS-managed CORS-with-preflight policy ID
        except ClientError as e:
            print(f"Error with response headers policy: {str(e)}")
            sys.exit(1)

def main():
    setup = CloudFrontSetup()
    setup.create_distribution()

if __name__ == '__main__':
    main() 