import json
import os
from pathlib import Path
import shutil

def extract_english_chunks(chunked_dir, output_dir):
    """
    Extract chunks with English language and save them to a separate directory.
    
    Args:
        chunked_dir (str): Path to directory containing chunked JSON files
        output_dir (str): Path to directory where English chunks will be saved
        
    Returns:
        tuple: (total_chunks, english_chunks) counts
    """
    chunked_path = Path(chunked_dir)
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(exist_ok=True, parents=True)
    
    total_chunks = 0
    english_chunks = 0
    english_files = 0
    
    # Process each JSON file in the chunked directory
    for json_file in chunked_path.glob('chunked_*.json'):
        print(f"Processing {json_file.name}...")
        
        try:
            # Read the JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
                
            # Handle both single document and array of documents
            if not isinstance(chunks, list):
                chunks = [chunks]
            
            # Filter for English chunks
            english_only = []
            for chunk in chunks:
                total_chunks += 1
                
                # Get metadata
                metadata = chunk.get('metadata', {})
                
                # Check if language is English
                # This includes 'en', 'en-US', 'en-CA', etc.
                lang = metadata.get('language', '').lower()
                if lang == 'en':
                    english_chunks += 1
                    english_only.append(chunk)
            
            # Save English chunks to output directory if any found
            if english_only:
                english_files += 1
                output_file = output_path / f"en_{json_file.name}"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(english_only, f, ensure_ascii=False, indent=2)
                print(f"Saved {len(english_only)} English chunks to {output_file}")
            else:
                print(f"No English chunks found in {json_file.name}")
                
        except Exception as e:
            print(f"Error processing {json_file.name}: {str(e)}")
            continue
    
    return total_chunks, english_chunks, english_files

def main():
    # Get the source and output directories
    source_dir = os.path.expanduser("~/Downloads/verkada_scrape/chunked")
    output_dir = os.path.expanduser("~/Downloads/verkada_scrape/english_chunks")
    
    print(f"Extracting English chunks from {source_dir} to {output_dir}...")
    
    # Extract English chunks
    total, english, files = extract_english_chunks(source_dir, output_dir)
    
    # Print summary
    print("\n===== EXTRACTION SUMMARY =====")
    print(f"Total chunks processed: {total}")
    print(f"English chunks extracted: {english} ({english/total*100:.2f}% of total)")
    print(f"Files created: {files}")
    print(f"English chunks saved to: {output_dir}")
    
    # Create a modified version of the upsert script for English chunks
    create_english_upsert_script(output_dir)

def create_english_upsert_script(english_chunks_dir):
    """Create a modified version of the upsert script specifically for English chunks."""
    
    # Path to the original upsert script
    original_script = Path("scripts/pinecone_verkada_upsert.py")
    
    # Path to the new English-only upsert script
    english_script = Path("scripts/pinecone_verkada_upsert_english.py")
    
    if not original_script.exists():
        print(f"Warning: Could not find original upsert script at {original_script}")
        return
    
    try:
        # Read the original script
        with open(original_script, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Modify the content for English chunks
        content = content.replace(
            'index_name = "verkada-docs-chunked"',
            'index_name = "verkada-docs-english"'
        )
        content = content.replace(
            'namespace = "verkada-docs-chunked"',
            'namespace = "verkada-docs-english"'
        )
        content = content.replace(
            'source_dir = os.path.expanduser("~/Downloads/verkada_scrape/chunked")',
            f'source_dir = os.path.expanduser("{english_chunks_dir}")'
        )
        
        # Remove the English filtering since all chunks are already English
        content = content.replace(
            '# Uncomment the next line to filter for English documents',
            '# All documents are already English, no need for filtering'
        )
        content = content.replace(
            'documents = filter_english_documents(documents)',
            '# documents = filter_english_documents(documents)  # Already English'
        )
        
        # Write the modified script
        with open(english_script, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\nCreated English-specific upsert script: {english_script}")
        print("You can use this script to upsert only the English chunks to Pinecone.")
        
    except Exception as e:
        print(f"Error creating English upsert script: {str(e)}")

if __name__ == "__main__":
    main() 