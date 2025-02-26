import json
import os
from pathlib import Path
import statistics

def analyze_documents(cleaned_dir):
    """
    Analyze the character and word length of documents in the cleaned directory.
    
    Args:
        cleaned_dir (str): Path to directory containing cleaned JSON files
        
    Returns:
        dict: Statistics about the documents
    """
    cleaned_path = Path(cleaned_dir)
    
    # Statistics to collect
    char_lengths = []
    word_lengths = []
    doc_count = 0
    languages = {}
    
    # Process each JSON file in the directory
    for json_file in cleaned_path.glob('cleaned_*.json'):
        print(f"Analyzing {json_file.name}...")
        
        try:
            # Read the JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                docs = json.load(f)
                
            # Handle both single document and array of documents
            if not isinstance(docs, list):
                docs = [docs]
            
            # Analyze each document
            for doc in docs:
                doc_count += 1
                
                # Get text content
                text = doc.get('text', '')
                
                # Calculate character length
                char_length = len(text)
                char_lengths.append(char_length)
                
                # Calculate word length
                words = text.split()
                word_length = len(words)
                word_lengths.append(word_length)
                
                # Track languages
                lang = doc.get('language', 'unknown')
                languages[lang] = languages.get(lang, 0) + 1
                
        except Exception as e:
            print(f"Error analyzing {json_file.name}: {str(e)}")
            continue
    
    # Calculate statistics
    stats = {
        "document_count": doc_count,
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
        "languages": languages
    }
    
    return stats

def print_stats(stats):
    """
    Print statistics in a readable format.
    
    Args:
        stats (dict): Statistics from analyze_documents
    """
    print("\n===== DOCUMENT STATISTICS =====")
    print(f"Total documents: {stats['document_count']}")
    
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
        print(f"{lang}: {count} documents ({count/stats['document_count']*100:.2f}%)")
    
    # Print additional insights
    print("\n----- Insights -----")
    if stats['character_length']['max'] > 50000:
        print(f"WARNING: Some documents are very large (max: {stats['character_length']['max']} chars)")
        print("This might cause issues with embedding or processing.")
    
    if stats['character_length']['mean'] > 10000:
        print(f"NOTE: Average document length is quite large ({stats['character_length']['mean']:.2f} chars)")
        print("Consider chunking documents for better embedding performance.")

if __name__ == "__main__":
    # Get the source directory from environment or default to ~/Downloads/verkada_scrape/cleaned
    source_dir = os.path.expanduser("~/Downloads/verkada_scrape/cleaned")
    
    print(f"Analyzing documents in {source_dir}...")
    stats = analyze_documents(source_dir)
    
    # Print statistics
    print_stats(stats)
    
    # Save statistics to JSON
    try:
        stats_dir = Path(os.path.expanduser("~/Downloads/verkada_scrape/stats"))
        stats_dir.mkdir(exist_ok=True)
        output_file = stats_dir / "document_stats.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        print(f"\nStatistics saved to {output_file}")
    except Exception as e:
        print(f"\nError saving statistics: {str(e)}") 