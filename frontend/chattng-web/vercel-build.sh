#!/bin/bash

# Install dependencies
npm install

# Build project
npm run build

# The build should output to the dist directory
echo "Build completed. Output in dist directory." 