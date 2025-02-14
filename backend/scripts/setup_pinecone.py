#!/usr/bin/env python3
import sys
from pathlib import Path
import json
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm
import os
from typing import Dict, List, Set
import numpy as np
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings

# Add project root to Python path
project_root = str(Path(__file__).resolve().parents[1])
workspace_root = str(Path(project_root).parent)  # Parent of backend directory
if project_root not in sys.path:
    sys.path.append(project_root)

# Load environment variables from .env
env_path = Path(project_root) / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

from config.settings import get_settings

class PineconeSetup:
    def __init__(self):
        self.settings = get_settings()
        self.verification_file = Path("migration_verification.json")
        self.vector_store = Path(workspace_root) / "data" / "processed" / "vector_store"
        self.verified_clips: Set[str] = set()
        self.index_name = os.getenv("PINECONE_INDEX", "chattng-dialogs")
        self.dimension = 1536  # Using OpenAI's text-embedding-3-small model
        
        # Load verified clips
        if not self.verification_file.exists():
            print("Error: No verification results found. Please run verify_migration.py first.")
            sys.exit(1)
            
        with open(self.verification_file, "r") as f:
            verification_results = json.load(f)
            # Normalize verified clip paths to be relative to workspace root
            self.verified_clips = {
                str(Path(clip_path).relative_to(workspace_root))
                for clip_path in verification_results["verified_clips"]
            }

        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.vector_store),
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # List available collections
        print("\nAvailable ChromaDB collections:")
        collections = self.chroma_client.list_collections()
        for collection in collections:
            print(f"- {collection.name}")
        
        if not collections:
            print("Error: No collections found in ChromaDB")
            sys.exit(1)
            
        # Use the first collection found
        self.collection = collections[0]
        print(f"\nUsing collection: {self.collection.name}")

    def initialize_pinecone(self):
        """Initialize Pinecone and create index"""
        try:
            # Initialize Pinecone
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            
            # Delete existing index if it exists
            if self.index_name in pc.list_indexes().names():
                print(f"\nDeleting existing Pinecone index: {self.index_name}")
                pc.delete_index(self.index_name)
                print("Waiting for index deletion to complete...")
                import time
                time.sleep(10)  # Wait for deletion to complete
            
            # Create new index
            print(f"\nCreating fresh Pinecone index: {self.index_name}")
            pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
                )
            )
            
            print("Waiting for index to be ready...")
            time.sleep(10)  # Wait for index to be ready
            
            # Connect to index
            self.index = pc.Index(self.index_name)
            print(f"\nConnected to fresh Pinecone index: {self.index_name}")
            
        except Exception as e:
            print(f"Error initializing Pinecone: {str(e)}")
            sys.exit(1)

    def process_dialogs(self):
        """Process dialog embeddings from ChromaDB for verified clips"""
        try:
            # Get all embeddings and documents from ChromaDB
            print("\nRetrieving data from ChromaDB...")
            results = self.collection.get(
                include=['embeddings', 'metadatas', 'documents']  # Explicitly include documents
            )
            
            embeddings = results['embeddings']
            metadatas = results['metadatas']
            documents = results['documents']  # Get the actual text content
            ids = results['ids']
            
            print(f"\nFound {len(embeddings)} total entries")
            
            # Process vectors in batches
            batch_size = 100
            total_vectors = 0
            batch_vectors = []
            
            print("\nPreparing vectors for Pinecone...")
            for i, (embedding, metadata, document, id) in enumerate(zip(embeddings, metadatas, documents, ids)):
                # Ensure text is included in metadata
                metadata_with_text = {
                    **metadata,
                    "text": document  # Add the actual dialog text to metadata
                }
                
                # Create vector entry
                vector = {
                    "id": id,
                    "values": embedding,
                    "metadata": metadata_with_text
                }
                
                batch_vectors.append(vector)
                
                # Debug first few entries
                if i < 5:
                    print(f"\nProcessing entry {i+1}:")
                    print(f"ID: {id}")
                    print(f"Text: {document[:100]}...")
                    print(f"Metadata keys: {list(metadata_with_text.keys())}")
            
            print(f"\nPrepared {len(batch_vectors)} vectors for upload")
            
            if batch_vectors:
                print("\nUploading to Pinecone...")
                try:
                    # Upload first batch and verify
                    first_batch = batch_vectors[:batch_size]
                    print(f"\nUploading first batch ({len(first_batch)} vectors)...")
                    self.index.upsert(vectors=first_batch)
                    total_vectors += len(first_batch)
                    
                    # Wait a moment for consistency
                    import time
                    time.sleep(2)
                    
                    # Verify first vector
                    first_id = first_batch[0]["id"]
                    print(f"\nVerifying first vector (ID: {first_id})...")
                    try:
                        result = self.index.fetch(ids=[first_id])
                        print(f"Fetch result: {result}")
                        
                        if result and hasattr(result, 'vectors') and first_id in result.vectors:
                            vector = result.vectors[first_id]
                            if hasattr(vector, 'metadata') and 'text' in vector.metadata:
                                stored_text = vector.metadata['text']
                                print(f"Successfully verified text storage: {stored_text[:100]}...")
                            else:
                                print("Warning: Vector found but no text in metadata!")
                                print(f"Available metadata: {vector.metadata if hasattr(vector, 'metadata') else 'None'}")
                        else:
                            print("Warning: Could not find vector in fetch result!")
                            print(f"Full result: {result}")
                    except Exception as e:
                        print(f"Error during verification: {str(e)}")
                        print("Continuing with upload anyway...")
                    
                    # Upload remaining batches
                    remaining_vectors = batch_vectors[batch_size:]
                    if remaining_vectors:
                        print("\nUploading remaining vectors...")
                        for i in tqdm(range(0, len(remaining_vectors), batch_size), desc="Processing batches"):
                            batch = remaining_vectors[i:i + batch_size]
                            self.index.upsert(vectors=batch)
                            total_vectors += len(batch)
                    
                except Exception as e:
                    print(f"Error during batch upload: {str(e)}")
                    raise
            
            print(f"\nSuccessfully processed {total_vectors} dialog vectors")
            
        except Exception as e:
            print(f"Error processing vectors: {str(e)}")
            sys.exit(1)

def main():
    setup = PineconeSetup()
    setup.initialize_pinecone()
    setup.process_dialogs()

if __name__ == "__main__":
    main() 