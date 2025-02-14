#!/usr/bin/env python3
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import json

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

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

            # Create distribution
            response = self.cloudfront_client.create_distribution(
                DistributionConfig={
                    'CallerReference': f'{self.s3_bucket}-{hash(self.s3_bucket)}',
                    'Origins': origin_config['Origins'],
                    'DefaultCacheBehavior': {
                        'TargetOriginId': f'S3-{self.s3_bucket}',
                        'ForwardedValues': {
                            'QueryString': False,
                            'Cookies': {'Forward': 'none'}
                        },
                        'TrustedSigners': {'Enabled': False, 'Quantity': 0},
                        'ViewerProtocolPolicy': 'redirect-to-https',
                        'MinTTL': 0,
                        'DefaultTTL': 86400,  # 24 hours
                        'MaxTTL': 31536000,  # 1 year
                        'Compress': True,
                        'AllowedMethods': {
                            'Quantity': 2,
                            'Items': ['GET', 'HEAD'],
                            'CachedMethods': {'Quantity': 2, 'Items': ['GET', 'HEAD']}
                        }
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

            # Save CloudFront domain to .env
            domain_name = response['Distribution']['DomainName']
            self._update_env_file(domain_name)

            print(f"\nCloudFront distribution created successfully!")
            print(f"Domain Name: {domain_name}")
            print(f"Distribution ID: {response['Distribution']['Id']}")
            print("\nNOTE: It may take up to 15 minutes for the distribution to deploy")

        except ClientError as e:
            print(f"Error creating CloudFront distribution: {str(e)}")
            sys.exit(1)

    def _update_env_file(self, domain_name):
        """Update .env file with CloudFront domain"""
        env_path = Path(project_root) / '.env'
        if not env_path.exists():
            print("Error: .env file not found")
            return

        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Update or add CLOUDFRONT_DOMAIN
        domain_found = False
        for i, line in enumerate(lines):
            if line.startswith('CLOUDFRONT_DOMAIN='):
                lines[i] = f'CLOUDFRONT_DOMAIN={domain_name}\n'
                domain_found = True
                break

        if not domain_found:
            lines.append(f'\nCLOUDFRONT_DOMAIN={domain_name}\n')

        with open(env_path, 'w') as f:
            f.writelines(lines)

def main():
    setup = CloudFrontSetup()
    setup.create_distribution()

if __name__ == '__main__':
    main() 