import pinecone
from pinecone import Pinecone
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any, Callable
import yaml
from openai import OpenAI
import google.generativeai as genai
from core.utils.text_utils import clean_dialog_text
import os
import logging
# Configure logging
logger = logging.getLogger(__name__)

# Import settings relative to backend directory
from config.settings import get_settings

settings = get_settings()

class DialogStorage:
    def __init__(self, config: Dict[str, Any]):
        """Initialize dialog storage with configuration"""
        self.config = config
        
        # Get Pinecone settings
        pinecone_api_key = settings.pinecone_api_key
        pinecone_env = settings.pinecone_environment
        pinecone_index = settings.pinecone_index
        
        logger.debug(f"Initializing Pinecone with environment: {pinecone_env}")
        logger.debug(f"Using index: {pinecone_index}")
        logger.debug(f"API key present: {bool(pinecone_api_key)}")
        
        if not pinecone_api_key:
            raise ValueError("Pinecone API key is not set. Please set PINECONE_API_KEY environment variable.")
        
        try:
            # Initialize Pinecone with new API
            pc = Pinecone(api_key=pinecone_api_key)
            self.index = pc.Index(pinecone_index)
            logger.info(f"Successfully connected to Pinecone index: {pinecone_index}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            raise ValueError(f"Pinecone initialization failed: {str(e)}")
        
        # Get embedding config
        self.embedding_config = config.get("embeddings", {})
        if not self.embedding_config:
            raise ValueError("Embedding configuration is required")
        
        # Initialize provider client (currently supporting OpenAI)
        if self.embedding_config["provider"] == "openai":
            if "openai_api_key" not in config:
                raise ValueError("OpenAI API key is required for OpenAI embeddings")
            
            # Initialize OpenAI client with base configuration
            self.embedding_client = OpenAI(
                api_key=config["openai_api_key"],
                base_url="https://api.openai.com/v1",  # Explicitly set the base URL
                timeout=60.0,  # Set a reasonable timeout
                max_retries=3  # Set max retries for robustness
            )
            logger.debug("Successfully initialized OpenAI client")
        else:
            raise ValueError(f"Unsupported embedding provider: {self.embedding_config['provider']}")

    def _get_embedding_function(self) -> Callable[[List[str]], List[List[float]]]:
        """Get embedding function for ChromaDB that matches our Pinecone setup"""
        class OpenAIEmbeddingFunction:
            def __init__(self, client: OpenAI, model: str):
                self.client = client
                self.model = model
            
            def __call__(self, input: List[str]) -> List[List[float]]:
                try:
                    # Clean texts
                    cleaned_texts = [clean_dialog_text(text) for text in input]
                    
                    # Get embeddings using OpenAI
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=cleaned_texts,
                        encoding_format="float"
                    )
                    
                    # Extract embeddings from response
                    return [item.embedding for item in response.data]
                except Exception as e:
                    logger.error(f"Error generating embeddings: {e}")
                    raise
        
        return OpenAIEmbeddingFunction(
            client=self.embedding_client,
            model=self.embedding_config["model"]
        )

    def add_dialog(self, text: str, metadata: Dict, clip_id: str) -> bool:
        """Store dialog text and metadata"""
        try:
            cleaned_text = clean_dialog_text(text)
            # Get embedding
            response = self.embedding_client.embeddings.create(
                model=self.embedding_config["model"],
                input=cleaned_text,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            
            # Ensure text is stored in metadata
            metadata_with_text = {
                **metadata,
                "text": cleaned_text,  # Store the actual dialog text
                "speaker": metadata.get("speaker", ""),  # Ensure speaker is present for filtering
            }
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[{
                    "id": clip_id,
                    "values": embedding,
                    "metadata": metadata_with_text
                }]
            )
            
            # Verify storage
            result = self.index.fetch([clip_id])
            if result and clip_id in result.vectors:
                stored_text = result.vectors[clip_id].metadata.get('text')
                if stored_text:
                    logger.debug(f"Successfully stored dialog in Pinecone: {clip_id}")
                    logger.debug(f"Text: {stored_text[:100]}...")
                    return True
                else:
                    logger.error(f"Text not found in stored metadata for {clip_id}")
                    return False
            else:
                logger.error(f"Failed to verify storage of {clip_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing dialog: {str(e)}")
            return False

    def get_dialog(self, clip_id: str) -> Optional[Dict]:
        """Retrieve dialog by ID"""
        try:
            result = self.index.fetch([clip_id])
            if result and clip_id in result['vectors']:
                vector = result['vectors'][clip_id]
                return {
                    'text': vector.metadata['text'],
                    'metadata': {k: v for k, v in vector.metadata.items() if k != 'text'}
                }
        except Exception as e:
            logger.error(f"Error retrieving dialog: {e}")
        return None

    def find_similar(
        self,
        query_embedding: List[float],
        n_results: int = 3,
        character: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Find similar dialogs using vector similarity search"""
        try:
            # Build filter if character specified
            filter_dict = {"speaker": {"$eq": character}} if character else None
            
            # Query Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=n_results,
                filter=filter_dict,
                include_metadata=True
            )
            
            # Format results
            matches = []
            for match in results.matches:
                # Safely extract text and metadata
                metadata = match.metadata if hasattr(match, 'metadata') else {}
                text = metadata.get('text', '')
                
                # Remove text from metadata to match expected format
                metadata_without_text = {k: v for k, v in metadata.items() if k != 'text'}
                
                # Add match score
                metadata_without_text['match_ratio'] = match.score if hasattr(match, 'score') else 0.0
                
                if text:  # Only add if we have text content
                    matches.append((text, metadata_without_text))
                else:
                    logger.warning(f"Skipping match due to missing text")
            
            logger.info(f"Found {len(matches)} valid matches from vector search")
            return matches
        except Exception as e:
            logger.error(f"Error searching dialogs: {str(e)}")
            return []
