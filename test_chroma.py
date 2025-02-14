import chromadb
import yaml
from openai import OpenAI
import os

# Load config
with open('config/search_config.yaml') as f:
    config = yaml.safe_load(f)

# Set up OpenAI client
os.environ["OPENAI_API_KEY"] = config["openai"]["api_key"]
openai_client = OpenAI()

# Get embedding for query
response = openai_client.embeddings.create(
    model=config["embeddings"]["model"],
    input="hello",
    encoding_format="float"
)
query_embedding = response.data[0].embedding

print("\n=== ChromaDB Test ===")

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=config['storage']['chroma_path'])
print(f"\nConnected to ChromaDB at: {config['storage']['chroma_path']}")

# List all collections
collections = client.list_collections()
print(f"\nAll collections: {[c.name for c in collections]}")

# Get collection
collection = client.get_collection(name=config['storage']['collection_name'])
print(f"\nCollection '{config['storage']['collection_name']}' stats:")
print(f"- Number of documents: {collection.count()}")

# Get a sample of documents
print("\nSample of documents:")
results = collection.get(limit=5)
if results and results['documents']:
    for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
        print(f"\nDocument {i+1}:")
        print(f"Text: {doc[:100]}...")
        print(f"Metadata: {metadata}")
else:
    print("No documents found in collection")

# Try a query using the embedding directly
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=1
)

print("\nSample query results:")
print(results) 