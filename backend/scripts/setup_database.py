#!/usr/bin/env python3
import sys
from pathlib import Path
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import ProgrammingError
import os
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables from .env
env_path = Path(project_root) / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

from config.settings import get_settings
from api.models.conversation import Base

class DatabaseSetup:
    def __init__(self):
        self.settings = get_settings()
        # Parse database URL to get components
        db_url = self.settings.database_url
        self.db_name = db_url.split('/')[-1]
        # Convert async URL to sync URL for initial setup
        self.db_url_base = '/'.join(db_url.split('/')[:-1]).replace('+asyncpg', '')
        self.db_url_default = f"{self.db_url_base}/postgres"  # For initial connection
        
        print("\nDatabase configuration:")
        print(f"Database name: {self.db_name}")
        print(f"Base URL: {self.db_url_base}")

    def create_database(self):
        """Create the database if it doesn't exist"""
        print("\nChecking database...")
        
        # Connect to default database first
        engine = create_engine(self.db_url_default)
        
        try:
            # Check if database exists
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{self.db_name}'"))
                exists = result.scalar() is not None
            
            if not exists:
                print(f"Creating database {self.db_name}...")
                with engine.connect() as conn:
                    # Close existing connections
                    conn.execute(text(f"""
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = '{self.db_name}'
                        AND pid <> pg_backend_pid()
                    """))
                    # Create database
                    conn.execute(text(f"CREATE DATABASE {self.db_name}"))
                print("Database created successfully")
            else:
                print("Database already exists")
                
        except Exception as e:
            print(f"Error creating database: {str(e)}")
            sys.exit(1)
        finally:
            engine.dispose()

    async def setup_schema(self):
        """Set up database schema"""
        print("\nSetting up schema...")
        try:
            # Create async engine with application database
            engine = create_async_engine(self.settings.database_url)
            
            async with engine.begin() as conn:
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
            
            print("Schema created successfully")
            
            # Create indexes
            print("\nCreating indexes...")
            async with engine.begin() as conn:
                # Index on conversations.session_id for faster lookups
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_session_id 
                    ON conversations (session_id)
                """))
                
                # Index on messages.conversation_id for faster message retrieval
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
                    ON messages (conversation_id)
                """))
                
                # Index on messages.timestamp for time-based queries
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                    ON messages (timestamp)
                """))
                
                # Index on conversation_shares.expires_at for cleanup
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_conversation_shares_expires_at 
                    ON conversation_shares (expires_at)
                """))
            
            print("Indexes created successfully")
            
        except Exception as e:
            print(f"Error setting up schema: {str(e)}")
            sys.exit(1)
        finally:
            await engine.dispose()

async def main():
    setup = DatabaseSetup()
    # Create database (sync operation)
    setup.create_database()
    # Set up schema (async operation)
    await setup.setup_schema()
    print("\nDatabase setup completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 