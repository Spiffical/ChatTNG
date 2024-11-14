import chromadb
from chromadb.utils import embedding_functions
from typing import List, Tuple, Optional
import os
from pathlib import Path
import yaml
from src.storage.dialog_storage import DialogStorage
from src.utils.text_utils import clean_dialog_text, split_into_sentences

class DialogSearchSystem:
    def __init__(self, config_path: str):
        """Initialize the search system with OpenAI embeddings"""
        self.storage = DialogStorage(config_path)
        
        # Load config for OpenAI
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Create OpenAI embedding function using text-embedding-3-small model
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=config['openai']['api_key'],
            model_name=config['openai']['models']['embedding']
        )
        
        # Get existing collection and update its embedding function
        self.collection = self.storage.client.get_collection(
            name="star_trek_dialog"
        )
        
        # Set the embedding function for queries
        self.collection._embedding_function = embedding_function

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
                print(f"Successfully verified storage of {clip_id}")
            else:
                print(f"Warning: Failed to verify storage of {clip_id}")

    def find_similar_dialog(self, query: str, character_name: str = None, n_results: int = 5, used_dialogs: List[str] = None) -> List[Tuple[str, dict]]:
        """Find similar dialog using embeddings, with optional character filtering"""
        print("\n=== Dialog Search Debug ===")
        print(f"Query: {query}")
        print(f"Character filter: {character_name}")
        
        cleaned_query = clean_dialog_text(query)
        print(f"Cleaned query: {cleaned_query}")
        
        # Pre-process used dialogs more efficiently
        if used_dialogs:
            used_data = {
                'texts': set(text.lower().strip() for text, _ in (d.split('::') for d in used_dialogs)),
                'clips': set(clip for _, clip in (d.split('::') for d in used_dialogs)),
                'ids': set(used_dialogs),
                'sentences': set(
                    sent.lower().strip() 
                    for text, _ in (d.split('::') for d in used_dialogs)
                    for sent in split_into_sentences(text.lower().strip())
                )
            }
        else:
            used_data = {'texts': set(), 'clips': set(), 'ids': set(), 'sentences': set()}

        # Query ChromaDB with increased initial results for better filtering
        results = self.collection.query(
            query_texts=[cleaned_query],
            where={"speaker": character_name} if character_name else None,
            n_results=min(200, n_results * 20)  # Increased pool for better matches
        )
        
        if not results['documents'][0]:
            return []

        # Process results in batches
        unique_results = []
        seen_texts = set()
        
        # Create generator for result processing
        def process_results():
            for text, metadata in zip(results['documents'][0], results['metadatas'][0]):
                if len(unique_results) >= n_results:
                    return
                    
                current_dialog_id = f"{text}::{metadata['clip_path']}"
                cleaned_text = clean_dialog_text(text).lower()
                
                # Combine all filtering conditions
                if (current_dialog_id not in used_data['ids'] and
                    metadata['clip_path'] not in used_data['clips'] and
                    cleaned_text not in used_data['texts'] and
                    cleaned_text not in seen_texts and
                    not any(s.lower().strip() in used_data['sentences'] for s in split_into_sentences(cleaned_text))):
                    
                    seen_texts.add(cleaned_text)
                    unique_results.append((text, metadata))

        # Process results
        process_results()
        return unique_results
