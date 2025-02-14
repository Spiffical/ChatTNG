from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Dict, Any, Optional
import os
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(env_path)

from api.schemas.chat import ChatResponse, ClipMetadata
from core.search.llm_interface import LLMInterface
from core.search.web_dialog_search import WebDialogSearch

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db: AsyncSession, redis: Redis):
        """Initialize chat service"""
        logger.debug("Initializing ChatService")
        self.db = db
        self.redis = redis
        
        # Get project root from environment variable
        project_root = os.getenv('PROJECT_ROOT', '/app')  # Default to /app in Docker
        logger.debug(f"Using project root: {project_root}")
        
        config_path = os.path.join(project_root, "config", "search_config.yaml")
        logger.debug(f"Using config path: {config_path}")
        self.llm = LLMInterface(config_path)
        self.dialog_search = WebDialogSearch(config_path, redis)
        
        # Cache settings
        self.cache_prefix = "chat_response:"
        self.cache_ttl = 3600  # 1 hour

    def _convert_timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert HH:MM:SS,mmm format to seconds"""
        try:
            # Replace comma with period for milliseconds
            timestamp = timestamp.replace(',', '.')
            # Split into hours, minutes, seconds
            h, m, s = timestamp.split(':')
            return float(h) * 3600 + float(m) * 60 + float(s)
        except Exception as e:
            logger.error(f"Error converting timestamp {timestamp}: {e}")
            return 0.0

    async def get_response(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """Get response for user message"""
        try:
            logger.info(f"Processing message from session {session_id}")
            
            # Initialize conversation history from context if provided
            if context and 'conversation_history' in context:
                # Get all messages except the current one
                history_messages = [
                    msg for msg in context['conversation_history'] 
                    if msg['content'] != message
                ]
                
                # Reset conversation history before adding from context
                self.llm.conversation_history = []
                
                # Add all previous messages to history
                for i in range(0, len(history_messages) - 1, 2):
                    user_msg = history_messages[i]
                    assistant_msg = history_messages[i + 1] if i + 1 < len(history_messages) else None
                    
                    if user_msg['role'] == 'user' and assistant_msg and assistant_msg['role'] == 'assistant':
                        self.llm.add_to_history(
                            user_msg['content'],
                            assistant_msg['content'],
                            assistant_msg.get('clip_metadata')
                        )
            else:
                # If no context provided, ensure history is empty
                self.llm.conversation_history = []

            # Generate responses and get matches
            response_text, matches = self.llm.generate_and_match(message)
            
            if not matches:
                logger.warning("No matching dialog found")
                raise ValueError("No matching dialog found")

            # Get best match using LLM from all available matches
            best_match_idx = self.llm.select_best_match(message, matches)
            if best_match_idx < 0:
                logger.warning("No suitable match found")
                raise ValueError("No suitable match found")

            text, metadata = matches[best_match_idx]

            # Update the user's message in history with the selected response
            self.llm.add_to_history(message, text, metadata)

            # Add the selected dialog to used dialogs to avoid repetition
            self.llm.add_used_dialog(text, metadata)

            # Create response with properly formatted metadata
            clip_url = self._get_clip_url(metadata["clip_path"])
            subtitle_url = self._get_subtitle_url(metadata["clip_path"])
            logger.info(f"Generated response with clip from S{metadata.get('season')}E{metadata.get('episode')}")

            response = ChatResponse(
                text=text,
                clip_url=clip_url,
                subtitle_url=subtitle_url,
                clip_metadata=ClipMetadata(
                    clip_path=metadata["clip_path"],
                    start_time=self._convert_timestamp_to_seconds(metadata["start_time"]),
                    end_time=self._convert_timestamp_to_seconds(metadata["end_time"]),
                    character=metadata.get("speaker", ""),
                    episode=str(metadata.get("episode", "")),
                    season=str(metadata.get("season", "")),
                    confidence=metadata.get("match_ratio", 0.0)
                ),
                conversation_id=str(uuid.uuid4())
            )

            return response

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            raise ValueError(f"Error generating response: {str(e)}")

    async def _get_cached_response(self, cache_key: str) -> Optional[ChatResponse]:
        """Get cached response if available"""
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug("Found cached response")
                return ChatResponse(**json.loads(cached))
            logger.debug("No cached response found")
            return None
        except Exception as e:
            logger.error(f"Error getting cached response: {str(e)}", exc_info=True)
            return None

    async def _cache_response(self, cache_key: str, response: ChatResponse) -> None:
        """Cache response for future use"""
        try:
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                response.json()
            )
            logger.debug("Response cached successfully")
        except Exception as e:
            logger.error(f"Error caching response: {str(e)}", exc_info=True)
            pass  # Fail silently on cache errors

    def _hash_message(self, message: str) -> str:
        """Create a deterministic hash of the message for caching"""
        import hashlib
        return hashlib.md5(message.encode()).hexdigest()

    async def get_character_suggestions(
        self,
        message: str,
        limit: int = 3
    ) -> list[str]:
        """Get character suggestions based on message content"""
        try:
            return self.llm.get_character_suggestions(message, limit)
        except Exception as e:
            raise ValueError(f"Error getting character suggestions: {str(e)}")

    async def get_episode_context(
        self,
        clip_metadata: ClipMetadata
    ) -> Optional[str]:
        """Get additional episode context for a clip"""
        try:
            return self.llm.get_episode_context(
                clip_metadata.episode,
                clip_metadata.start_time,
                clip_metadata.end_time
            )
        except Exception:
            return None

    async def validate_rate_limit(self, session_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        key = f"rate_limit:{session_id}"
        count = await self.redis.incr(key)
        
        if count == 1:
            await self.redis.expire(key, 60) # 1 minute window
            
        return count <= 10 # 10 messages per minute 

    def _get_clip_url(self, clip_path: str) -> str:
        """Convert local clip path to CloudFront URL"""
        # Remove 'data/processed/clips/' prefix if present
        clip_path = clip_path.replace('data/processed/clips/', '')
        # Format CloudFront URL
        cloudfront_domain = os.getenv('CLOUDFRONT_DOMAIN', 'd2qqs9uhgc4wdq.cloudfront.net')
        return f"https://{cloudfront_domain}/clips/{clip_path}"

    def _get_subtitle_url(self, clip_path: str) -> str:
        """Convert local clip path to CloudFront subtitle URL"""
        # Remove 'data/processed/clips/' prefix if present
        clip_path = clip_path.replace('data/processed/clips/', '')
        # Replace video extension with .srt while keeping the same path
        subtitle_path = os.path.splitext(clip_path)[0] + '.srt'
        # Format CloudFront URL
        cloudfront_domain = os.getenv('CLOUDFRONT_DOMAIN', 'd2qqs9uhgc4wdq.cloudfront.net')
        subtitle_url = f"https://{cloudfront_domain}/clips/{subtitle_path}"
        logger.debug(f"Generated subtitle URL: {subtitle_url} from clip path: {clip_path}")
        return subtitle_url 