import argparse
from pathlib import Path
import sys
import yaml
import chromadb

def inspect_chroma_db(config_path: str):
    """Inspect the contents of the ChromaDB"""
    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Get project root from config path
    project_root = Path(config_path).resolve().parents[1]
    vector_store_path = project_root / config['paths']['vector_store']
    
    print(f"Looking for ChromaDB at: {vector_store_path}")
    
    # Initialize Chroma client
    client = chromadb.PersistentClient(path=str(vector_store_path))
    
    # List all collections
    collections = client.list_collections()
    print(f"\nFound {len(collections)} collections:")
    for collection in collections:
        print(f"\nCollection name: {collection.name}")
        print(f"Collection metadata: {collection.metadata}")
        
        # Get all entries in this collection
        results = collection.get()
        
        if not results or not results['ids']:
            print("No entries found in this collection.")
            continue
        
        print(f"Total entries: {len(results['ids'])}")
        print("\nSample entries:")
        
        # Print first 5 entries as sample
        for i in range(min(5, len(results['ids']))):
            print(f"\nEntry {i+1}:")
            print(f"ID: {results['ids'][i]}")
            print(f"Text: {results['documents'][i]}")
            print("Metadata:")
            for key, value in results['metadatas'][i].items():
                print(f"  {key}: {value}")
            print("-" * 80)
            
            # Verify clip file exists
            clip_path = Path(results['metadatas'][i]['clip_path'])
            if not clip_path.exists():
                print(f"WARNING: Clip file does not exist: {clip_path}")
        
        # Ask if user wants to see more entries
        if len(results['ids']) > 5:
            response = input("\nShow more entries? (y/n): ")
            if response.lower() == 'y':
                for i in range(5, len(results['ids'])):
                    print(f"\nEntry {i+1}:")
                    print(f"ID: {results['ids'][i]}")
                    print(f"Text: {results['documents'][i]}")
                    print("Metadata:")
                    for key, value in results['metadatas'][i].items():
                        print(f"  {key}: {value}")
                    print("-" * 80)
                    
                    if i % 10 == 9:  # After every 10 entries
                        response = input("\nContinue? (y/n): ")
                        if response.lower() != 'y':
                            break

def main():
    parser = argparse.ArgumentParser(description='Inspect ChromaDB contents')
    parser.add_argument('--config', required=True, help='Path to config file')
    args = parser.parse_args()
    
    inspect_chroma_db(args.config)

if __name__ == "__main__":
    main()
