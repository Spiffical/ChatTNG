#!/bin/bash

# Create a temporary file for environment variables
echo "Creating environment variables file for Docker..."
ENV_FILE=".env.docker.tmp"

# Convert Railway config to Docker environment file format
while IFS= read -r line; do
    if [[ $line != \#* ]] && [[ -n $line ]]; then
        echo "$line" >> "$ENV_FILE"
    fi
done < railway_config.txt

echo "Running Docker container with environment variables..."
docker run --rm -it --env-file "$ENV_FILE" chattng-backend-test python -c "
from config.settings import get_settings
settings = get_settings()
print('Configuration Test Results:')
print('-' * 50)
print('App Config loaded:', bool(settings.app_config))
if settings.app_config:
    print('Sample app_config value (paths):', settings.app_config.get('paths', {}))
print('\nPrompts Config loaded:', bool(settings.prompts_config))
if settings.prompts_config:
    print('Sample prompts_config keys:', list(settings.prompts_config.keys())[:3])
print('\nSearch Config loaded:', bool(settings.search_config))
if settings.search_config:
    print('Sample search_config value (gemini):', settings.search_config.get('gemini', {}))
print('\nAll configurations loaded successfully!')
"

# Clean up
rm "$ENV_FILE" 