import yaml
import json
from typing import List, Dict, Any, Tuple
import os
import logging
from pathlib import Path
from openai import OpenAI
import chromadb

from ..storage.dialog_storage import DialogStorage
from ..utils.text_utils import clean_dialog_text, split_into_sentences

# Configure logging
logger = logging.getLogger(__name__)

class DialogSearchSystem:
    def __init__(self, config_path: str):
        """Initialize dialog search system"""
        self.config = self._load_config(config_path)
        logger.info(f"Loaded config from {config_path}")
        
        # Create storage config with all necessary settings
        storage_config = {
            **self.config["storage"],
            "openai_api_key": self.config["openai"]["api_key"],
            "embeddings": self.config["embeddings"]  # Pass complete embedding config
        }
        
        self.storage = DialogStorage(storage_config)
        
        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(path=storage_config["chroma_path"])
        
        # Get or create collection using configured embeddings
        self.collection = self.client.get_or_create_collection(
            name=storage_config["collection_name"],
            embedding_function=self.storage._get_embedding_function(),
            metadata={"hnsw:space": self.config["embeddings"]["similarity_metric"]}
        )
        logger.info(f"Initialized with collection '{storage_config['collection_name']}' containing {self.collection.count()} documents")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        with open(config_path) as f:
            return yaml.safe_load(f)

    def add_dialog_clip(self, text: str, clip_path: str, start_time: str, end_time: str, 
                       season: int, episode: int) -> None:
        """Add a dialog clip with its metadata"""
        clip_id = f"dialog_S{season:02d}E{episode:02d}_{Path(clip_path).stem}"
        metadata = {
            "clip_path": clip_path,
            "start_time": start_time,
            "end_time": end_time,
            "season": season,
            "episode": episode
        }
        
        if self.storage.add_dialog(text, metadata, clip_id):
            # Verify storage
            if self.storage.get_dialog(clip_id):
                logger.debug(f"Successfully stored dialog {clip_id}")
            else:
                logger.warning(f"Failed to store dialog {clip_id}")

    def find_similar_dialog(
        self,
        query: str,
        character: str = None,
        n_results: int = 3
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Find similar dialog using vector similarity search"""
        # Clean and prepare query
        cleaned_query = clean_dialog_text(query)
        
        # Get embedding for query
        openai_client = OpenAI(api_key=self.config["openai"]["api_key"])
        response = openai_client.embeddings.create(
            model=self.config["embeddings"]["model"],
            input=cleaned_query,
            encoding_format="float"
        )
        query_embedding = response.data[0].embedding
        
        # Query Pinecone through storage layer
        matches = self.storage.find_similar(
            query_embedding=query_embedding,
            n_results=n_results,
            character=character
        )
        
        # Log only summary
        logger.info(f"Found {len(matches)} matches for query: '{query}'")
        if character:
            logger.info(f"Filtered by character: {character}")
            
        return matches
