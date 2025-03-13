#!/usr/bin/env python3
import requests
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
project_root = str(Path(__file__).resolve().parents[2])
aws_env_path = Path(project_root) / 'env' / 'production' / '.env.aws'
load_dotenv(aws_env_path)

# CloudFront domain from successful setup
CLOUDFRONT_DOMAIN = "d3h9bmq6ehlxbf.cloudfront.net"

def test_cors_headers(url):
    """Test CORS headers for a URL"""
    print(f"\nTesting CORS headers for: {url}")
    
    # Test preflight request (OPTIONS)
    headers = {
        'Origin': 'https://chattng-web.vercel.app',
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Content-Type'
    }
    
    try:
        options_response = requests.options(url, headers=headers)
        print("\nOPTIONS request headers:")
        print(f"Status code: {options_response.status_code}")
        for header, value in options_response.headers.items():
            if header.lower().startswith('access-control'):
                print(f"{header}: {value}")
    except Exception as e:
        print(f"Error during OPTIONS request: {e}")

    # Test actual GET request
    headers = {
        'Origin': 'https://chattng-web.vercel.app'
    }
    
    try:
        get_response = requests.get(url, headers=headers)
        print("\nGET request headers:")
        print(f"Status code: {get_response.status_code}")
        for header, value in get_response.headers.items():
            if header.lower().startswith('access-control'):
                print(f"{header}: {value}")
        
        # Check content type
        print(f"Content-Type: {get_response.headers.get('Content-Type', 'Not specified')}")
        print(f"Content Length: {len(get_response.content)} bytes")
    except Exception as e:
        print(f"Error during GET request: {e}")

def main():
    # Test paths
    test_paths = [
        f"https://{CLOUDFRONT_DOMAIN}/clips/S04E18/S04E18_clip_0103.mp4",
        f"https://{CLOUDFRONT_DOMAIN}/clips/S04E18/S04E18_clip_0103.srt"
    ]
    
    for path in test_paths:
        test_cors_headers(path)
        print("\n" + "="*80)

if __name__ == "__main__":
    main() 