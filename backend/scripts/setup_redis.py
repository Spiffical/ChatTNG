#!/usr/bin/env python3
import sys
from pathlib import Path
import redis
from redis.exceptions import ConnectionError
import os
from dotenv import load_dotenv
import json

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables from .env
env_path = Path(project_root) / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

from config.settings import get_settings

class RedisSetup:
    def __init__(self):
        self.settings = get_settings()
        self.redis_url = self.settings.redis_url
        print("\nRedis configuration:")
        print(f"URL: {self.redis_url}")
        print(f"Rate limit: {self.settings.rate_limit_per_minute} requests/minute")
        print(f"Session expiry: {self.settings.session_expire} seconds")

    def check_connection(self):
        """Test Redis connection and basic operations"""
        print("\nTesting Redis connection...")
        try:
            # Create Redis client
            client = redis.from_url(self.redis_url)
            
            # Test connection with ping
            response = client.ping()
            if not response:
                raise ConnectionError("Ping failed")
            
            print("Connection successful!")
            return client
            
        except Exception as e:
            print(f"Error connecting to Redis: {str(e)}")
            print("\nPlease ensure Redis is installed and running:")
            print("1. Install Redis: sudo apt-get install redis-server")
            print("2. Start Redis: sudo service redis-server start")
            print("3. Run this script again")
            sys.exit(1)

    def configure_rate_limiting(self, client):
        """Set up rate limiting configuration"""
        print("\nConfiguring rate limiting...")
        try:
            # Store rate limit configuration
            config = {
                "requests_per_minute": self.settings.rate_limit_per_minute,
                "window_size": 60  # 1 minute window
            }
            client.set("rate_limit_config", json.dumps(config))
            print("Rate limiting configured successfully")
            
        except Exception as e:
            print(f"Error configuring rate limiting: {str(e)}")
            sys.exit(1)

    def configure_session_management(self, client):
        """Set up session management configuration"""
        print("\nConfiguring session management...")
        try:
            # Store session configuration
            config = {
                "cookie_name": self.settings.session_cookie,
                "expiry": self.settings.session_expire,
                "cookie_secure": True,
                "cookie_httponly": True,
                "cookie_samesite": "lax"
            }
            client.set("session_config", json.dumps(config))
            print("Session management configured successfully")
            
        except Exception as e:
            print(f"Error configuring session management: {str(e)}")
            sys.exit(1)

    def setup_key_prefixes(self, client):
        """Set up key prefixes for different types of data"""
        print("\nSetting up key prefixes...")
        try:
            prefixes = {
                "rate_limit": "rl:",  # Rate limiting keys
                "session": "sess:",    # Session data
                "share": "share:"      # Share links
            }
            client.set("key_prefixes", json.dumps(prefixes))
            print("Key prefixes configured successfully")
            
        except Exception as e:
            print(f"Error setting up key prefixes: {str(e)}")
            sys.exit(1)

def main():
    setup = RedisSetup()
    
    # Check Redis connection
    client = setup.check_connection()
    
    # Configure components
    setup.configure_rate_limiting(client)
    setup.configure_session_management(client)
    setup.setup_key_prefixes(client)
    
    print("\nRedis setup completed successfully!")
    print("\nNext steps:")
    print("1. Implement rate limiting middleware")
    print("2. Implement session management")
    print("3. Add Redis health checks to the application")

if __name__ == "__main__":
    main() 