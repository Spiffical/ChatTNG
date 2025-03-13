#!/usr/bin/env python3
import yaml
import base64
import json
from pathlib import Path

def yaml_to_base64(yaml_path):
    """Convert a YAML file to a base64 encoded string."""
    with open(yaml_path, 'r') as f:
        yaml_content = f.read()
    return base64.b64encode(yaml_content.encode('utf-8')).decode('utf-8')

def main():
    config_dir = Path(__file__).parent.parent / 'backend' / 'config'
    
    # List of config files to process
    config_files = [
        ('app_config.yaml', 'APP_CONFIG'),
        ('prompts.yaml', 'PROMPTS_CONFIG'),
        ('search_config.yaml', 'SEARCH_CONFIG'),
    ]
    
    print("# Railway Environment Variables")
    print("# Add these to your Railway project's Variables section")
    print()
    
    for filename, env_var_name in config_files:
        file_path = config_dir / filename
        if file_path.exists():
            base64_content = yaml_to_base64(file_path)
            print(f"{env_var_name}={base64_content}")
            print(f"{env_var_name}_ENCODING=base64")
            print()

if __name__ == '__main__':
    main() 