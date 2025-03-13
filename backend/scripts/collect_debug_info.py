#!/usr/bin/env python3
import os
from pathlib import Path
import datetime

def write_debug_info():
    # Create debug info directory if it doesn't exist
    debug_dir = Path("debug_info")
    debug_dir.mkdir(exist_ok=True)
    
    # Create a timestamp for the filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = debug_dir / f"debug_info_{timestamp}.txt"
    
    with open(output_file, "w") as f:
        # Write error description
        f.write("=== Database Connection Error Analysis ===\n\n")
        f.write("Error Description:\n")
        f.write("SQLAlchemy async driver error: The application is attempting to use async SQLAlchemy features,\n")
        f.write("but the system is loading psycopg2 instead of the required async driver (asyncpg).\n\n")
        f.write("Error Message:\n")
        f.write("sqlalchemy.exc.InvalidRequestError: The asyncio extension requires an async driver to be used. ")
        f.write("The loaded 'psycopg2' is not async.\n\n")
        
        # List of relevant files to check
        files_to_check = [
            ("backend/api/dependencies/database.py", "Main database configuration file where the error occurs"),
            ("backend/api/database.py", "Core database module with URL processing and engine creation"),
            ("backend/requirements.txt", "Dependencies file showing installed database drivers"),
            ("backend/api/middleware/health.py", "Health check middleware that uses database connection"),
            ("backend/start.sh", "Startup script that handles initial database connection"),
            ("backend/main.py", "Main application file that imports database components"),
            ("backend/api/routes/chat.py", "Route file that imports database dependencies"),
            ("docker/backend/Dockerfile.prod", "Dockerfile that installs dependencies"),
            ("backend/alembic.ini", "Alembic configuration file with database URL"),
            ("backend/config/settings.py", "Settings file with database configuration")
        ]
        
        # Write file contents
        for file_path, description in files_to_check:
            f.write(f"\n{'='*80}\n")
            f.write(f"File: {file_path}\n")
            f.write(f"Description: {description}\n")
            f.write(f"{'='*80}\n\n")
            
            try:
                with open(file_path, 'r') as source_file:
                    f.write(source_file.read())
            except FileNotFoundError:
                f.write(f"[File not found: {file_path}]\n")
            except Exception as e:
                f.write(f"[Error reading file: {str(e)}]\n")
        
        # Write environment information
        f.write("\n\n=== Environment Information ===\n")
        f.write("\nRelevant Environment Variables:\n")
        env_vars = [
            "DATABASE_URL",
            "POSTGRES_CONNECT_TIMEOUT",
            "POSTGRES_POOL_TIMEOUT",
            "POSTGRES_COMMAND_TIMEOUT",
            "PYTHONPATH",
            "PORT",
            "UVICORN_WORKERS"
        ]
        
        for var in env_vars:
            value = os.getenv(var, "[Not set]")
            # Mask sensitive information
            if "password" in var.lower() or "secret" in var.lower():
                value = "[REDACTED]"
            f.write(f"{var}: {value}\n")
    
    print(f"\nDebug information has been written to: {output_file}")
    print("Please include this file when seeking help with debugging.")

if __name__ == "__main__":
    write_debug_info() 