import argparse
from pathlib import Path
import sys
from tqdm import tqdm
import time
import yaml
from chromadb.utils import embedding_functions
from src.storage.dialog_storage import DialogStorage
from src.utils.text_utils import clean_dialog_text

def generate_embeddings(config_path: str):
    """Generate embeddings for all stored dialogs using OpenAI"""
    # Initialize storage
    storage = DialogStorage(config_path)
    
    # First, get all dialogs from the existing collection
    all_dialogs = storage.get_all_dialogs()
    if not all_dialogs or not all_dialogs['ids']:
        print("No dialogs found in source storage.")
        return
    
    # Store the dialogs temporarily
    temp_dialogs = {
        'ids': all_dialogs['ids'],
        'documents': all_dialogs['documents'],
        'metadatas': all_dialogs['metadatas']
    }
    
    # Delete existing collection
    try:
        storage.client.delete_collection("star_trek_dialog")
        print("Deleted existing collection")
    except:
        print("No existing collection to delete")
    
    # Create OpenAI embedding function
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        api_key=config['openai']['api_key'],
        model_name=config['openai']['models']['embedding']
    )
    
    # Create new collection with OpenAI embeddings
    collection = storage.client.create_collection(
        name=config['vector_store']['collection_name'],
        embedding_function=embedding_function,
        metadata={"hnsw:space": config['vector_store']['similarity_metric']}
    )
    print("Created new collection with OpenAI embeddings")
    
    print(f"Found {len(temp_dialogs['ids'])} dialogs. Generating OpenAI embeddings...")
    
    # Process in batches
    batch_size = 100
    max_retries = 5
    retry_delay = 3  # seconds
    
    for i in tqdm(range(0, len(temp_dialogs['ids']), batch_size)):
        batch_ids = temp_dialogs['ids'][i:i + batch_size]
        batch_texts = temp_dialogs['documents'][i:i + batch_size]
        batch_metadatas = temp_dialogs['metadatas'][i:i + batch_size]
        
        # Add to collection with retries
        for attempt in range(max_retries):
            try:
                collection.add(
                    documents=[clean_dialog_text(text) for text in batch_texts],
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"\nError processing batch {i//batch_size + 1}, retrying in {retry_delay} seconds: {e}")
                    time.sleep(retry_delay)
                else:
                    print(f"\nFailed to process batch {i//batch_size + 1} after {max_retries} attempts: {e}")
                    user_input = input("Continue with next batch? (y/n): ").lower()
                    if user_input != 'y':
                        print("Embedding generation stopped by user.")
                        return

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate embeddings for stored dialogs.')
    parser.add_argument('--config', required=True, help='Path to config file')
    args = parser.parse_args()

    generate_embeddings(args.config)
