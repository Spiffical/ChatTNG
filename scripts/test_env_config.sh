#!/bin/bash

# Export the environment variables from railway_config.txt
while IFS= read -r line; do
    if [[ $line != \#* ]] && [[ -n $line ]]; then
        export "$line"
    fi
done < railway_config.txt

# Run the test script
python scripts/test_config.py 