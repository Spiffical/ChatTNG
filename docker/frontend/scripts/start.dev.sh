#!/bin/bash

# Enable error tracing
set -ex

# Start Vite dev server with host set to allow external connections
exec npm run dev -- --host 0.0.0.0 