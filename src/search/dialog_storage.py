import chromadb
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import yaml
from chromadb.utils import embedding_functions
from src.utils.text_utils import clean_dialog_text

class DialogStorage:
    def __init__(self, config_path: str):
        # Load config
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        # Get project root from config path
        project_root = Path(config_path).resolve().parents[1]
        
        # Ensure vector store directory exists with absolute path
        vector_store_path = project_root / self.config['paths']['vector_store']
        vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(vector_store_path)
        )
        
        # Create OpenAI embedding function
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.config['openai']['api_key'],
            model_name=self.config['openai']['models']['embedding']
        )
        
        # Initialize with OpenAI embedding function
        self.collection = self.client.get_or_create_collection(
            name=self.config['vector_store']['collection_name'],
            embedding_function=embedding_function,
            metadata={"hnsw:space": self.config['vector_store']['similarity_metric']}
        )

    def add_dialog(self, text: str, metadata: Dict, clip_id: str) -> bool:
        """Store dialog text and metadata"""
        try:
            cleaned_text = clean_dialog_text(text)
            self.collection.add(
                documents=[cleaned_text],
                metadatas=[metadata],
                ids=[clip_id]
            )
            print(f"Added to store: {clip_id}")
            print(f"Text: {cleaned_text[:100]}...")
            return True
        except Exception as e:
            print(f"Error storing dialog: {e}")
            return False

    def get_dialog(self, clip_id: str) -> Optional[Dict]:
        """Retrieve dialog by ID"""
        try:
            result = self.collection.get(ids=[clip_id])
            if result and result['ids']:
                return {
                    'text': result['documents'][0],
                    'metadata': result['metadatas'][0]
                }
        except Exception as e:
            print(f"Error retrieving dialog: {e}")
        return None

    def get_all_dialogs(self) -> Optional[Dict]:
        """Retrieve all stored dialogs"""
        try:
            return self.collection.get()
        except Exception as e:
            print(f"Error retrieving all dialogs: {e}")
            return None
