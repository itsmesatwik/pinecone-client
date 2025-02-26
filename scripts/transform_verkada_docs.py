import json
import os
import uuid
from pathlib import Path
import re

def clean_text(text):
    """
    Clean text to remove problematic characters and limit length.
    
    Args:
        text (str): Raw text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Replace escape sequences
    text = text.replace('\\n', '\n').replace('\\"', '"')
    
    # Remove control characters except for newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Limit text length to 100,000 characters (adjust as needed)
    if len(text) > 100000:
        text = text[:100000]
        
    return text

def transform_document(doc):
    """
    Transform a scraped document record into the desired format for integrated embedding.
    
    Args:
        doc (dict): Raw document data containing html, markdown, metadata etc.
        
    Returns:
        dict: Transformed document record for upsert_records or None if invalid
    """
    try:
        metadata = doc.get('metadata', {})
        
        # Skip if no markdown content
        if not doc.get('markdown'):
            print("Skipping document with no markdown content")
            return None
            
        # Clean the text
        cleaned_text = clean_text(doc.get('markdown', ''))
        
        # Skip if cleaned text is too short
        if len(cleaned_text) < 10:
            print("Skipping document with insufficient content after cleaning")
            return None
            
        return {
            '_id': str(uuid.uuid4()),  # Using _id for integrated embedding
            'text': cleaned_text,  # text field for embedding
            'url': metadata.get('url', ''),
            'language': metadata.get('language', ''),
            'description': clean_text(metadata.get('description', ''))
        }
    except Exception as e:
        print(f"Error transforming document: {str(e)}")
        return None

def process_directory(input_dir):
    """
    Process all JSON files in a directory and transform them into the desired format.
    
    Args:
        input_dir (str): Path to directory containing JSON files
        
    Returns:
        list: List of transformed documents
    """
    input_path = Path(input_dir)
    transformed_docs = []
    
    # Create cleaned subdirectory if it doesn't exist
    cleaned_dir = input_path / 'cleaned'
    cleaned_dir.mkdir(exist_ok=True)
    
    # Process each JSON file in the directory
    for json_file in input_path.glob('*.json'):
        if json_file.name.startswith('.'):  # Skip hidden files
            continue
            
        print(f"Processing {json_file.name}...")
        
        try:
            # Read the JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                docs = json.load(f)
                
            # Handle both single document and array of documents
            if not isinstance(docs, list):
                docs = [docs]
            
            # Transform each document, filtering out None results
            transformed = []
            for doc in docs:
                result = transform_document(doc)
                if result:
                    transformed.append(result)
            
            if transformed:
                transformed_docs.extend(transformed)
                
                # Save transformed documents to cleaned directory
                output_file = cleaned_dir / f"cleaned_{json_file.name}"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(transformed, f, ensure_ascii=False, indent=2)
                    
                print(f"Saved {len(transformed)} cleaned documents to {output_file}")
            else:
                print(f"No valid documents found in {json_file.name}")
            
        except Exception as e:
            print(f"Error processing {json_file.name}: {str(e)}")
            continue
    
    return transformed_docs

if __name__ == "__main__":
    # Get the source directory from environment or default to ~/Downloads/verkada_scrape
    source_dir = os.path.expanduser("~/Downloads/verkada_scrape")
    
    print(f"Processing files in {source_dir}...")
    transformed_docs = process_directory(source_dir)
    print(f"Transformed {len(transformed_docs)} documents successfully") 