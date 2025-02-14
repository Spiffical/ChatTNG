from redis.asyncio import Redis
import yaml
import json
from typing import List, Dict, Any, Tuple, Optional
import os
import logging
from fastapi import HTTPException

from .dialog_search import DialogSearchSystem
from ..utils.text_utils import clean_dialog_text, split_into_sentences

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class WebDialogSearch:
    def __init__(self, config_path: str, redis: Redis):
        """Initialize web-optimized dialog search"""
        logger.debug("Initializing WebDialogSearch")
        self.redis = redis
        self.search_system = DialogSearchSystem(config_path)
        
        # Cache settings
        self.cache_prefix = "dialog_search:"
        self.cache_ttl = 3600  # 1 hour
        self.batch_size = 50
        logger.debug(f"Cache settings - TTL: {self.cache_ttl}s, Batch size: {self.batch_size}")

    async def find_similar_dialog(
        self,
        query: str,
        character_name: Optional[str] = None,
        n_results: int = 5,
        used_dialogs: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Find similar dialog with caching and rate limiting"""
        try:
            logger.debug("\n=== Web Dialog Search ===")
            logger.debug(f"Query: {query}")
            logger.debug(f"Character: {character_name}")
            logger.debug(f"Session ID: {session_id}")
            logger.debug(f"Used dialogs: {len(used_dialogs) if used_dialogs else 0}")
            
            # Check rate limit if session provided
            if session_id:
                rate_limited = await self._check_rate_limit(session_id)
                if not rate_limited:
                    logger.warning(f"Rate limit exceeded for session {session_id}")
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded"
                    )
                logger.debug("Rate limit check passed")
            
            # Try cache first
            cache_key = self._get_cache_key(query, character_name, n_results)
            cached = await self._get_cached_results(cache_key)
            if cached:
                logger.debug("Found cached results")
                return cached
            logger.debug("No cached results found")
            
            # Get matches from search system
            matches = self.search_system.find_similar_dialog(
                query=query,
                character=character_name,
                n_results=n_results,
                used_dialogs=used_dialogs
            )
            
            # Cache results
            await self._cache_results(cache_key, matches)
            logger.debug(f"Cached {len(matches)} results")
            
            return matches
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error searching dialogs: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error searching dialogs: {str(e)}"
            )

    def _get_cache_key(self, query: str, character_name: Optional[str], n_results: int) -> str:
        """Generate cache key for query"""
        key_parts = [
            clean_dialog_text(query),
            str(character_name),
            str(n_results)
        ]
        key = f"dialog_search:{':'.join(key_parts)}"
        logger.debug(f"Generated cache key: {key}")
        return key

    async def _get_cached_results(
        self,
        cache_key: str
    ) -> Optional[List[Tuple[str, Dict[str, Any]]]]:
        """Get cached search results"""
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                results = json.loads(cached)
                logger.debug(f"Retrieved {len(results)} cached results")
                return results
            return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None

    async def _cache_results(
        self,
        cache_key: str,
        results: List[Tuple[str, Dict[str, Any]]]
    ) -> None:
        """Cache search results"""
        try:
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(results)
            )
            logger.debug(f"Cached {len(results)} results for {self.cache_ttl}s")
        except Exception as e:
            logger.error(f"Error caching results: {str(e)}")
            pass  # Fail silently on cache errors

    async def _check_rate_limit(self, session_id: str) -> bool:
        """Check if session has exceeded rate limit"""
        key = f"dialog_search_rate:{session_id}"
        count = await self.redis.incr(key)
        
        if count == 1:
            await self.redis.expire(key, 60)  # 1 minute window
            
        under_limit = count <= 20  # 20 searches per minute
        logger.debug(f"Rate limit check - Session: {session_id}, Count: {count}, Under limit: {under_limit}")
        return under_limit 