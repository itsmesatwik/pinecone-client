from pinecone import Pinecone
import os
from dotenv import load_dotenv
import json
from pathlib import Path
import time
from functools import wraps
import random
from itertools import islice

# Load environment variables from .env
load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Delete existing index if it exists
index_name = "verkada-docs-english"
if pc.has_index(index_name):
    print(f"Deleting existing index '{index_name}'...")
    pc.delete_index(index_name)

print(f"Creating new index '{index_name}' with integrated embedding...")
# Create new index with integrated embedding
index = pc.create_index_for_model(
    name=index_name,
    cloud="aws",
    region="us-east-1",
    embed={
        "model": "llama-text-embed-v2",  # Using one of the supported models
        "field_map": {
            "text": "text"  # Map the 'text' field in our records to be embedded
        }
    }
)

# Wait for index to be ready
while not pc.describe_index(index_name).status['ready']:
    print("Waiting for index to be ready...")
    time.sleep(1)

print("Index is ready!")

# Get the index instance
index = pc.Index(index_name)

def chunks(iterable, batch_size=100):
    """A helper function to break an iterable into chunks of size batch_size."""
    iterator = iter(iterable)
    chunk = list(islice(iterator, batch_size))
    while chunk:
        yield chunk
        chunk = list(islice(iterator, batch_size))

def retry_with_exponential_backoff(
    max_retries=3,
    initial_delay=1,
    max_delay=60,
    exponential_base=2,
    jitter=True
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_retries (int): Maximum number of retries
        initial_delay (float): Initial delay in seconds
        max_delay (float): Maximum delay in seconds
        exponential_base (float): Base for exponential calculation
        jitter (bool): Whether to add random jitter to delay
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        print(f"Max retries ({max_retries}) exceeded.")
                        raise e
                    
                    delay = min(
                        max_delay,
                        initial_delay * (exponential_base ** (retries - 1))
                    )
                    
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    print(f"Retry {retries}/{max_retries} after {delay:.2f}s delay. Error: {str(e)}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

# Load all chunked documents
def load_chunked_documents(chunked_dir):
    """Load all chunked documents from the chunked directory."""
    documents = []
    chunked_path = Path(chunked_dir)
    
    for json_file in chunked_path.glob('chunked_*.json'):
        print(f"Loading {json_file.name}...")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
                if isinstance(chunks, list):
                    documents.extend(chunks)
                else:
                    documents.append(chunks)
        except Exception as e:
            print(f"Error loading {json_file.name}: {str(e)}")
            continue
    
    return documents

# Filter for English documents if needed
def filter_english_documents(documents):
    """Filter documents to only include English language chunks."""
    english_docs = []
    for doc in documents:
        metadata = doc.get('metadata', {})
        lang = metadata.get('language', '').lower()
        if lang == 'en':
            english_docs.append(doc)
    
    print(f"Filtered {len(english_docs)} English documents from {len(documents)} total documents")
    return english_docs

# upsert documents to pinecone in batches
BATCH_SIZE = 50  # Moderate batch size for better throughput

# Note: We're including metadata as direct properties of the record
# rather than as a nested metadata object to comply with Pinecone's requirements.
namespace = "verkada-docs-english"

def upsert_records_individually(index, namespace, batch):
    """
    Upsert records one by one to handle individual failures gracefully.
    
    Args:
        index: Pinecone index
        namespace: Namespace to upsert to
        batch: List of records to upsert
        
    Returns:
        int: Number of successfully upserted records
    """
    success_count = 0
    
    for record in batch:
        try:
            # Get metadata from the record
            metadata = record.get('metadata', {})
            
            # Create a record with text, ID, and flattened metadata fields
            # Include metadata fields directly in the record instead of as a nested object
            upsert_record = {
                '_id': record['_id'],
                'text': record['text'],
                # Add metadata fields directly to the record
                'url': str(metadata.get('url', '')),
                'language': str(metadata.get('language', '')),
                'description': str(metadata.get('description', '')),
                'header': str(metadata.get('header', '')),
                'header_level': str(metadata.get('header_level', '0')),
                'chunk_index': str(metadata.get('chunk_index', '0')),
                'total_chunks': str(metadata.get('total_chunks', '0')),
                'parent_doc_id': str(metadata.get('parent_doc_id', ''))
            }
            
            # Upsert a single record with flattened metadata
            index.upsert_records(
                namespace=namespace,
                records=[upsert_record]
            )
            success_count += 1
            
        except Exception as e:
            print(f"Failed to upsert record {record.get('_id')}: {str(e)}")
            # Log problematic record for debugging
            if metadata:
                print(f"Problematic record: URL={metadata.get('url')}, Language={metadata.get('language')}")
            print(f"Text length: {len(record.get('text', ''))}")
            
            # Print the exact error for debugging
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            continue
    
    return success_count

if __name__ == "__main__":
    # Load documents from the chunked directory
    source_dir = os.path.expanduser("/Users/satwik/Downloads/verkada_scrape/english_chunks")
    print(f"Loading chunked documents from {source_dir}...")
    documents = load_chunked_documents(source_dir)
    print(f"Loaded {len(documents)} document chunks")

    # Optionally filter for English documents only
    # All documents are already English, no need for filtering
    # documents = filter_english_documents(documents)  # Already English

    # Process batches with individual record handling
    total_success = 0
    total_attempts = 0
    
    for batch in chunks(documents, BATCH_SIZE):
        total_attempts += len(batch)
        try:
            success_count = upsert_records_individually(index, namespace, batch)
            total_success += success_count
            print(f"Successfully upserted {success_count}/{len(batch)} chunks in this batch")
            print(f"Running total: {total_success}/{total_attempts} chunks upserted successfully")
            # Add a small delay between batches to avoid rate limiting
            time.sleep(0.5)
        except Exception as e:
            print(f"Unexpected error processing batch: {str(e)}")
            continue
    
    print(f"Completed upserting {total_success}/{total_attempts} chunks to namespace '{namespace}'")
    print(f"Index '{index_name}' is now ready for querying!") 