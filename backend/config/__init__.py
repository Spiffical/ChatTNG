"""
Configuration package for ChatTNG backend.
"""

import os
import sys
from pathlib import Path

# Get the absolute path of the current directory
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent

# Add backend directory to Python path
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    # Print debug information
    print(f"Current directory: {current_dir}")
    print(f"Backend directory: {backend_dir}")
    print(f"Directory contents: {os.listdir(current_dir)}")
    print(f"Python path: {sys.path}")
    
    # Try to import settings
    from .settings import get_settings
except ImportError as e:
    print(f"Error importing settings: {e}")
    print(f"Current directory contents: {os.listdir(current_dir)}")
    print(f"Parent directory contents: {os.listdir(backend_dir)}")
    raise

__all__ = ['get_settings'] 