#!/usr/bin/env python3
import asyncio
import os
import sys
from typing import Optional

import asyncpg
import httpx

# Default values for Docker Compose environment
DEFAULT_DB_URL = "postgresql://postgres:postgres123@localhost:5432/chattng"
DEFAULT_API_URL = "http://localhost:8080"

async def check_database(db_url: str) -> bool:
    """Check if database is accessible."""
    try:
        conn = await asyncpg.connect(db_url)
        await conn.execute("SELECT 1")
        await conn.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

async def check_api_health(base_url: str) -> bool:
    """Check if API health endpoint is responding."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("✅ API health check successful")
                    return True
                else:
                    print(f"❌ API health check failed: Unexpected response - {data}")
                    return False
            else:
                print(f"❌ API health check failed: Status code {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ API health check failed: {str(e)}")
        return False

async def main() -> None:
    """Run all health checks."""
    # Get configuration from environment or use defaults
    db_url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    api_url = os.getenv("API_URL", DEFAULT_API_URL)
    
    print("\nRunning health checks...")
    print("-" * 50)
    
    db_success = await check_database(db_url)
    api_success = await check_api_health(api_url)
    
    print("-" * 50)
    if db_success and api_success:
        print("✅ All checks passed!")
        sys.exit(0)
    else:
        print("❌ Some checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 