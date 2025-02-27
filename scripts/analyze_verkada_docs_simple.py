import json
import os
from pathlib import Path
import statistics

def analyze_documents(chunked_dir):
    """
    Analyze the character and word length of document chunks in the chunked directory.
    
    Args:
        chunked_dir (str): Path to directory containing chunked JSON files
        
    Returns:
        dict: Statistics about the document chunks
    """
    chunked_path = Path(chunked_dir)
    
    # Statistics to collect
    char_lengths = []
    word_lengths = []
    chunk_count = 0
    languages = {}
    header_levels = {}
    english_chunks = 0
    
    # Process each JSON file in the directory
    for json_file in chunked_path.glob('chunked_*.json'):
        print(f"Analyzing {json_file.name}...")
        
        try:
            # Read the JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
                
            # Handle both single document and array of documents
            if not isinstance(chunks, list):
                chunks = [chunks]
            
            # Analyze each chunk
            for chunk in chunks:
                chunk_count += 1
                
                # Get text content
                text = chunk.get('text', '')
                
                # Calculate character length
                char_length = len(text)
                char_lengths.append(char_length)
                
                # Calculate word length
                words = text.split()
                word_length = len(words)
                word_lengths.append(word_length)
                
                # Get metadata
                metadata = chunk.get('metadata', {})
                
                # Track languages
                lang = metadata.get('language', 'unknown')
                languages[lang] = languages.get(lang, 0) + 1
                
                # Count English chunks specifically
                if lang.lower() == 'en':
                    english_chunks += 1
                
                # Track header levels
                header_level = metadata.get('header_level', -1)
                header_levels[header_level] = header_levels.get(header_level, 0) + 1
                
        except Exception as e:
            print(f"Error analyzing {json_file.name}: {str(e)}")
            continue
    
    # Calculate statistics
    stats = {
        "chunk_count": chunk_count,
        "english_chunks": english_chunks,
        "english_percentage": (english_chunks / chunk_count * 100) if chunk_count > 0 else 0,
        "character_length": {
            "min": min(char_lengths) if char_lengths else 0,
            "max": max(char_lengths) if char_lengths else 0,
            "mean": statistics.mean(char_lengths) if char_lengths else 0,
            "median": statistics.median(char_lengths) if char_lengths else 0,
            "stdev": statistics.stdev(char_lengths) if len(char_lengths) > 1 else 0
        },
        "word_length": {
            "min": min(word_lengths) if word_lengths else 0,
            "max": max(word_lengths) if word_lengths else 0,
            "mean": statistics.mean(word_lengths) if word_lengths else 0,
            "median": statistics.median(word_lengths) if word_lengths else 0,
            "stdev": statistics.stdev(word_lengths) if len(word_lengths) > 1 else 0
        },
        "languages": languages,
        "header_levels": header_levels
    }
    
    return stats

def print_stats(stats):
    """
    Print statistics in a readable format.
    
    Args:
        stats (dict): Statistics from analyze_documents
    """
    print("\n===== CHUNK STATISTICS =====")
    print(f"Total chunks: {stats['chunk_count']}")
    print(f"English chunks: {stats['english_chunks']} ({stats['english_percentage']:.2f}%)")
    
    print("\n----- Character Length -----")
    print(f"Min: {stats['character_length']['min']}")
    print(f"Max: {stats['character_length']['max']}")
    print(f"Mean: {stats['character_length']['mean']:.2f}")
    print(f"Median: {stats['character_length']['median']:.2f}")
    print(f"Standard Deviation: {stats['character_length']['stdev']:.2f}")
    
    print("\n----- Word Length -----")
    print(f"Min: {stats['word_length']['min']}")
    print(f"Max: {stats['word_length']['max']}")
    print(f"Mean: {stats['word_length']['mean']:.2f}")
    print(f"Median: {stats['word_length']['median']:.2f}")
    print(f"Standard Deviation: {stats['word_length']['stdev']:.2f}")
    
    print("\n----- Language Distribution -----")
    for lang, count in sorted(stats['languages'].items(), key=lambda x: x[1], reverse=True):
        print(f"{lang}: {count} chunks ({count/stats['chunk_count']*100:.2f}%)")
    
    print("\n----- Header Level Distribution -----")
    for level, count in sorted(stats['header_levels'].items()):
        level_name = "No header" if level == 0 else f"H{level}" if level > 0 else "Unknown"
        print(f"{level_name}: {count} chunks ({count/stats['chunk_count']*100:.2f}%)")
    
    # Print additional insights
    print("\n----- Insights -----")
    if stats['english_percentage'] < 50:
        print(f"NOTE: Only {stats['english_percentage']:.2f}% of chunks are in English.")
        print("Consider filtering non-English content if your application is primarily for English users.")
    
    if stats['character_length']['max'] > 10000:
        print(f"WARNING: Some chunks are still quite large (max: {stats['character_length']['max']} chars)")
        print("Consider further chunking or limiting chunk size for better embedding performance.")

if __name__ == "__main__":
    # Get the source directory from environment or default to ~/Downloads/verkada_scrape/chunked
    source_dir = os.path.expanduser("~/Downloads/verkada_scrape/chunked")
    
    print(f"Analyzing document chunks in {source_dir}...")
    stats = analyze_documents(source_dir)
    
    # Print statistics
    print_stats(stats)
    
    # Save statistics to JSON
    try:
        stats_dir = Path(os.path.expanduser("~/Downloads/verkada_scrape/stats"))
        stats_dir.mkdir(exist_ok=True)
        output_file = stats_dir / "chunk_stats.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        print(f"\nStatistics saved to {output_file}")
    except Exception as e:
        print(f"\nError saving statistics: {str(e)}") 