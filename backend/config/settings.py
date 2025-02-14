from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    api_title: str = "ChatTNG API"
    api_description: str = "Star Trek: TNG Dialog Chat API"
    api_version: str = "1.0.0"
    debug: bool = False

    # CORS Settings
    cors_origins: List[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Database Settings
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/chattng"
    redis_url: str = "redis://redis:6379"

    # AWS Settings
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "us-east-1"
    s3_bucket: str = "chattng-clips"
    cloudfront_domain: Optional[str] = None
    cloudfront_key_pair_id: Optional[str] = None
    cloudfront_private_key_path: Optional[str] = None

    # Pinecone Settings
    pinecone_api_key: Optional[str] = None
    pinecone_environment: str = "gcp-starter"
    pinecone_index: str = "chattng-dialogs"

    # OpenAI Settings
    openai_api_key: Optional[str] = None
    openai_model: str = "text-embedding-3-small"

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Session Settings
    session_cookie: str = "chattng_session"
    session_expire: int = 24 * 60 * 60  # 24 hours

    # Share Settings
    share_expire_days: int = 7
    share_base_url: str = "http://localhost:3000"

    # Project Settings
    project_root: str = "/app"  # Docker container path

    def __init__(self, **kwargs):
        # Debug print
        print(f"Looking for .env file in: {os.getcwd()}")
        print(f"Environment variables:")
        for key in [
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET", "AWS_DEFAULT_REGION",
            "PINECONE_API_KEY", "PINECONE_ENVIRONMENT", "OPENAI_API_KEY"
        ]:
            print(f"{key}: {'[SET]' if key in os.environ else '[NOT SET]'}")
        
        # Set AWS credentials from environment variables
        kwargs["aws_access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID")
        kwargs["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY")
        kwargs["s3_bucket"] = os.environ.get("S3_BUCKET", "chattng-clips")
        kwargs["aws_default_region"] = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        
        # Set Pinecone and OpenAI credentials
        kwargs["pinecone_api_key"] = os.environ.get("PINECONE_API_KEY")
        kwargs["pinecone_environment"] = os.environ.get("PINECONE_ENVIRONMENT", "gcp-starter")
        kwargs["openai_api_key"] = os.environ.get("OPENAI_API_KEY")
        
        super().__init__(**kwargs)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings() 