from pinecone import Pinecone
import os
from dotenv import load_dotenv
import json
import uuid
from itertools import islice
import time
from functools import wraps
import random

# Load environment variables from .env
load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Delete existing index if it exists
index_name = "webpage-english-chunks"
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

# load webpages_english_combined.json
with open("webpages_english_combined.json", "r") as f:
    webpages = json.load(f)

def transform_webpage_data(webpage):
    """
    Transform a scraped webpage record into the desired format for integrated embedding.
    
    Args:
        webpage (dict): Raw webpage data containing html, markdown, metadata etc.
        
    Returns:
        dict: Transformed webpage record for upsert_records
    """
    metadata = webpage.get('metadata', {})
    
    return {
        '_id': str(uuid.uuid4()),  # Using _id for integrated embedding
        'text': webpage.get('markdown', '').replace('\\n', '\n').replace('\\"', '"'),  # text field for embedding
        'url': metadata.get('url', ''),
        'language': metadata.get('language', ''),
        'description': metadata.get('description', '')
    }

def process_webpages(webpages_data):
    """
    Process a list of webpage records into the desired format.
    
    Args:
        webpages_data (list): List of raw webpage records
        
    Returns:
        list: List of transformed webpage records
    """
    transformed_pages = []
    
    for webpage in webpages_data:
        transformed = transform_webpage_data(webpage)
        transformed_pages.append(transformed)
        
    return transformed_pages

# transformed_webpages = process_webpages(webpages)

# save transformed webpages to a json file
# with open("transformed_webpages.json", "w") as f:
#     json.dump(transformed_webpages, f)

# load transformed webpages from a json file
with open("transformed_webpages.json", "r") as f:
    transformed_webpages = json.load(f)

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

# upsert transformed webpages to pinecone in batches
BATCH_SIZE = 10  # Keep batch size small initially to avoid hitting limits
namespace = "webpage-chunks"

@retry_with_exponential_backoff(
    max_retries=5,
    initial_delay=2,
    max_delay=60,
    jitter=True
)
def upsert_batch(index, namespace, batch):
    """Upsert a batch of records with retry logic."""
    index.upsert_records(
        namespace=namespace,
        records=batch
    )
    return len(batch)

# Process batches with retry logic
for batch in chunks(transformed_webpages, BATCH_SIZE):
    try:
        batch_size = upsert_batch(index, namespace, batch)
        print(f"Successfully upserted batch of {batch_size} records to namespace '{namespace}'")
    except Exception as e:
        print(f"Failed to upsert batch even after retries: {str(e)}")
        print(f"Detailed error: {str(e)}")
        # Optionally, you might want to continue with the next batch instead of breaking
        continue