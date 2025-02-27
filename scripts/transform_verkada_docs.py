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

def chunk_markdown_by_headers(markdown_text):
    """
    Split markdown text into chunks based on headers.
    
    Args:
        markdown_text (str): Cleaned markdown text
        
    Returns:
        list: List of dictionaries containing chunk text and header info
    """
    if not markdown_text:
        return []
    
    # Regex to match markdown headers (# Header, ## Header, etc.)
    header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    # Find all headers with their positions
    headers = [(m.group(1), m.group(2), m.start()) for m in header_pattern.finditer(markdown_text)]
    
    # If no headers found, return the whole text as one chunk
    if not headers:
        return [{"text": markdown_text, "header": "", "level": 0}]
    
    chunks = []
    
    # Handle text before the first header if it exists
    if headers[0][2] > 0:
        intro_text = markdown_text[:headers[0][2]].strip()
        if intro_text:
            chunks.append({
                "text": intro_text,
                "header": "Introduction",
                "level": 0
            })
    
    # Process each header and the content that follows it
    for i in range(len(headers)):
        header_marks, header_text, start_pos = headers[i]
        level = len(header_marks)  # Number of # symbols indicates header level
        
        # Determine end position (start of next header or end of text)
        end_pos = headers[i+1][2] if i < len(headers) - 1 else len(markdown_text)
        
        # Extract chunk text (including the header)
        chunk_text = markdown_text[start_pos:end_pos].strip()
        
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "header": header_text,
                "level": level
            })
    
    return chunks

def transform_document(doc):
    """
    Transform a scraped document record into the desired format for integrated embedding.
    Split the document into chunks based on headers.
    
    Args:
        doc (dict): Raw document data containing html, markdown, metadata etc.
        
    Returns:
        list: List of transformed document chunks for upsert_records or empty list if invalid
    """
    try:
        metadata = doc.get('metadata', {})
        
        # Skip if no markdown content
        if not doc.get('markdown'):
            print("Skipping document with no markdown content")
            return []
            
        # Clean the text
        cleaned_text = clean_text(doc.get('markdown', ''))
        
        # Skip if cleaned text is too short
        if len(cleaned_text) < 10:
            print("Skipping document with insufficient content after cleaning")
            return []
        
        # Get document URL for reference
        doc_url = metadata.get('url', '')
        
        # Split the document into chunks based on headers
        chunks = chunk_markdown_by_headers(cleaned_text)
        
        # Transform each chunk into a document record
        transformed_chunks = []
        for i, chunk in enumerate(chunks):
            # Skip chunks that are too small
            if len(chunk["text"]) < 10:
                continue
                
            # Create a unique ID for each chunk
            chunk_id = f"{str(uuid.uuid4())}"
            
            # Create chunk-specific metadata
            chunk_metadata = {
                "url": doc_url,
                "language": metadata.get('language', ''),
                "description": clean_text(metadata.get('description', '')),
                "header": chunk["header"],
                "header_level": chunk["level"],
                "chunk_index": i,
                "total_chunks": len(chunks),
                "parent_doc_id": metadata.get('id', '')
            }
            
            transformed_chunks.append({
                '_id': chunk_id,
                'text': chunk["text"],
                'metadata': chunk_metadata
            })
            
        return transformed_chunks
    except Exception as e:
        print(f"Error transforming document: {str(e)}")
        return []

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
    
    # Create chunked subdirectory if it doesn't exist
    chunked_dir = input_path / 'chunked'
    chunked_dir.mkdir(exist_ok=True)
    
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
            
            # Transform each document, getting chunks for each
            transformed = []
            for doc in docs:
                chunks = transform_document(doc)
                if chunks:
                    transformed.extend(chunks)
            
            if transformed:
                transformed_docs.extend(transformed)
                
                # Save transformed documents to chunked directory
                output_file = chunked_dir / f"chunked_{json_file.name}"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(transformed, f, ensure_ascii=False, indent=2)
                    
                print(f"Saved {len(transformed)} chunks from {json_file.name} to chunked directory")
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
    print(f"Transformed {len(transformed_docs)} document chunks successfully") 