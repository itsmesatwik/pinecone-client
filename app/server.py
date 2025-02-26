from flask import request, jsonify
from pinecone import Pinecone
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cache for Pinecone indexes to avoid recreating them for each request
index_cache = {}

# Define available indexes and their namespaces
# This could be dynamically populated from Pinecone, but for simplicity we'll hardcode it
AVAILABLE_INDEXES = {
    "verkada-docs": ["verkada-docs"],
    "webpage-english-chunks": ["webpage-chunks"]
}

def setup_pinecone(api_key):
    """Initialize Pinecone client with API key"""
    return Pinecone(api_key=api_key)

def get_index(pc, index_name):
    """Get or create a Pinecone index from the cache"""
    if index_name not in index_cache:
        index_cache[index_name] = pc.Index(index_name)
    return index_cache[index_name]

def clean_result(hit):
    """Clean the result fields to ensure they're JSON serializable"""
    # Handle description that might be a list
    description = hit['fields'].get('description', '')
    if isinstance(description, list):
        description = description[0] if description else ''
    
    return {
        '_id': hit['_id'],
        '_score': hit['_score'],
        'fields': {
            'description': description.strip() if description else '',
            'text': hit['fields']['text'].strip() if hit['fields'].get('text') else '',
            'url': hit['fields']['url'].strip() if hit['fields'].get('url') else ''
        }
    }

def get_usage_info(result):
    """Extract usage information from the search result"""
    usage_info = {}
    try:
        if hasattr(result, 'usage'):
            usage_attr = result.usage
            
            # Check if usage is callable (a method)
            if callable(usage_attr):
                try:
                    usage_data = usage_attr()
                    if isinstance(usage_data, dict):
                        usage_info = usage_data
                except:
                    logger.warning("Failed to call usage method")
            # Check if usage is a dictionary
            elif isinstance(usage_attr, dict):
                for key, value in usage_attr.items():
                    if isinstance(value, (int, float, str, bool)) or value is None:
                        usage_info[key] = value
                    else:
                        usage_info[key] = str(value)
            # Check if usage is an object with attributes
            elif hasattr(usage_attr, '__dict__'):
                usage_dict = vars(usage_attr)
                for key, value in usage_dict.items():
                    if isinstance(value, (int, float, str, bool)) or value is None:
                        usage_info[key] = value
                    else:
                        usage_info[key] = str(value)
            else:
                # Last resort: convert to string
                usage_info = {"usage_info": str(usage_attr)}
            
            logger.info(f"Usage information: {usage_info}")
    except Exception as e:
        logger.warning(f"Error processing usage information: {str(e)}")
        # Continue without usage info if there's an error
    
    return usage_info

def process_search_results(result):
    """Process search results to ensure they're JSON serializable"""
    cleaned_hits = []
    if hasattr(result, 'result') and hasattr(result.result, 'hits'):
        # Process each hit to ensure it's JSON serializable
        for hit in result.result.hits:
            try:
                cleaned_hit = {
                    '_id': hit.get('_id', ''),
                    '_score': float(hit.get('_score', 0)),
                    'fields': {}
                }
                
                # Process fields
                if 'fields' in hit:
                    for field_key, field_value in hit['fields'].items():
                        # Handle different field types
                        if isinstance(field_value, (str, int, float, bool)) or field_value is None:
                            cleaned_hit['fields'][field_key] = field_value
                        elif isinstance(field_value, list):
                            # For list values, convert to string if not primitive types
                            if all(isinstance(item, (str, int, float, bool)) for item in field_value):
                                cleaned_hit['fields'][field_key] = field_value
                            else:
                                cleaned_hit['fields'][field_key] = str(field_value)
                        else:
                            cleaned_hit['fields'][field_key] = str(field_value)
                
                cleaned_hits.append(cleaned_hit)
            except Exception as e:
                logger.error(f"Error processing hit: {e}")
                # Skip this hit if there's an error
    
    return cleaned_hits

def setup_routes(app, pc):
    """Set up the API routes for the application"""
    
    @app.route('/api/indexes', methods=['GET'])
    def get_indexes():
        """Get available indexes and their namespaces"""
        try:
            # In a production environment, you might want to dynamically fetch this from Pinecone
            return jsonify({
                'indexes': AVAILABLE_INDEXES
            })
        except Exception as e:
            logger.error(f"Error getting indexes: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/search', methods=['POST'])
    def search():
        try:
            data = request.json
            query = data.get('query')
            rerank_model = data.get('rerank_model', '')
            top_k = data.get('top_k', 10)
            index_name = data.get('index_name', 'verkada-docs')
            namespace_name = data.get('namespace', 'webpage-chunks')
            
            if not query:
                return jsonify({'error': 'Query is required'}), 400

            # Get the index
            try:
                index = get_index(pc, index_name)
                logger.info(f"Using index: {index_name}")
            except Exception as e:
                logger.error(f"Error getting index {index_name}: {str(e)}")
                return jsonify({'error': f"Invalid index: {index_name}"}), 400

            # Prepare search query
            search_query = {
                "inputs": {"text": query},
                "top_k": top_k
            }
            
            # Prepare search parameters
            search_params = {
                "namespace": namespace_name,
                "query": search_query,
                "fields": ["text", "url", "description"]
            }
            
            # Add reranking if a model is selected
            if rerank_model:
                logger.info(f"Using reranking with model: {rerank_model}")
                search_params["rerank"] = {
                    "model": rerank_model,
                    "top_n": top_k,
                    "rank_fields": ["text"]  # Field to use for reranking
                }
            
            # Log the search parameters
            logger.info(f"Search parameters: {search_params}")

            # Execute search
            result = index.search_records(**search_params)
            
            # Log the number of results
            if hasattr(result, 'result') and hasattr(result.result, 'hits'):
                logger.info(f"Search returned {len(result.result.hits)} results")
            else:
                logger.warning("Search returned no results or unexpected result structure")
            
            # Get usage information
            usage_info = get_usage_info(result)
            
            # Process search results
            cleaned_hits = process_search_results(result)

            return jsonify({
                'result': {
                    'hits': cleaned_hits
                },
                'usage': usage_info
            })

        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500 