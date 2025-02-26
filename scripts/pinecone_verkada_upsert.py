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
index_name = "verkada-docs"
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

# Load all cleaned documents
def load_cleaned_documents(cleaned_dir):
    """Load all cleaned documents from the cleaned directory."""
    documents = []
    cleaned_path = Path(cleaned_dir)
    
    for json_file in cleaned_path.glob('cleaned_*.json'):
        print(f"Loading {json_file.name}...")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                docs = json.load(f)
                if isinstance(docs, list):
                    documents.extend(docs)
                else:
                    documents.append(docs)
        except Exception as e:
            print(f"Error loading {json_file.name}: {str(e)}")
            continue
    
    return documents

# upsert documents to pinecone in batches
BATCH_SIZE = 5  # Reduced batch size to minimize impact of failures
namespace = "verkada-docs"

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
            # Upsert a single record
            index.upsert_records(
                namespace=namespace,
                records=[record]
            )
            success_count += 1
        except Exception as e:
            print(f"Failed to upsert record {record.get('_id')}: {str(e)}")
            # Log problematic record for debugging
            print(f"Problematic record: URL={record.get('url')}, Language={record.get('language')}")
            print(f"Text length: {len(record.get('text', ''))}")
            continue
    
    return success_count

if __name__ == "__main__":
    # Load documents from the cleaned directory
    source_dir = os.path.expanduser("~/Downloads/verkada_scrape/cleaned")
    print(f"Loading cleaned documents from {source_dir}...")
    documents = load_cleaned_documents(source_dir)
    print(f"Loaded {len(documents)} documents")

    # Process batches with individual record handling
    total_success = 0
    total_attempts = 0
    
    for batch in chunks(documents, BATCH_SIZE):
        total_attempts += len(batch)
        try:
            success_count = upsert_records_individually(index, namespace, batch)
            total_success += success_count
            print(f"Successfully upserted {success_count}/{len(batch)} records in this batch")
            print(f"Running total: {total_success}/{total_attempts} records upserted successfully")
        except Exception as e:
            print(f"Unexpected error processing batch: {str(e)}")
            continue
    
    print(f"Completed upserting {total_success}/{total_attempts} records to namespace '{namespace}'") 