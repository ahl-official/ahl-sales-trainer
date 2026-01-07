import os
import json
import hashlib
import requests
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pinecone import Pinecone
from extensions import db
from utils.text_utils import chunk_text
from config_logging import get_logger

logger = get_logger('pinecone_service')

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', '')
PINECONE_INDEX_HOST = os.environ.get('PINECONE_INDEX_HOST', '')

def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Create embeddings for batch of texts using OpenAI"""
    if not texts:
        return []
        
    try:
        response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'text-embedding-3-small',
                'input': texts
            },
            timeout=60
        )
        
        response.raise_for_status()
        data = response.json()
        
        return [item['embedding'] for item in data['data']]
    except Exception as e:
        logger.error(f"Failed to create embeddings: {e}")
        raise

def get_namespaces_for_category(category: str) -> List[str]:
    """Get all Pinecone namespaces for a category"""
    uploads = db.get_uploads_by_category(category)
    
    namespaces = []
    for upload in uploads:
        video_name = upload['video_name']
        ns = f"{category.lower().replace(' ', '_')}_{video_name.lower().replace(' ', '_')}"
        namespaces.append(ns)
    
    return namespaces

def process_and_upload(content: str, category: str, video_name: str) -> Dict:
    """Process content and upload to Pinecone"""
    # Create namespace (e.g., "consultation_series_video1")
    namespace = f"{category.lower().replace(' ', '_')}_{video_name.lower().replace(' ', '_')}"
    
    # Chunk the content
    chunks = chunk_text(content)
    
    # Create embeddings
    embeddings = create_embeddings_batch(chunks)
    
    # Upload to Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(host=PINECONE_INDEX_HOST)
    
    vectors = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vector_id = f"{namespace}_chunk_{i}"
        vectors.append({
            'id': vector_id,
            'values': embedding,
            'metadata': {
                'text': chunk[:3000],  # Store preview
                'category': category,
                'video_name': video_name,
                'chunk_index': i,
                'namespace': namespace
            }
        })
    
    # Batch upsert
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch, namespace=namespace)
    
    return {
        'chunks': len(chunks),
        'namespace': namespace
    }

def query_pinecone(embedding: List[float], category: str, top_k: int = 50, namespaces: List[str] = None) -> List[Dict]:
    """Query Pinecone for relevant content across namespaces"""
    if namespaces is None:
        namespaces = get_namespaces_for_category(category)
    
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(host=PINECONE_INDEX_HOST)
    
    def run_query(ns):
        try:
            return index.query(
                vector=embedding,
                top_k=top_k,
                namespace=ns,
                include_metadata=True
            )
        except Exception:
            return None
    
    max_workers = min(4, len(namespaces)) if namespaces else 0
    results = []
    
    if max_workers > 0:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_query, ns): ns for ns in namespaces}
            for fut in as_completed(futures):
                res = fut.result()
                if res and 'matches' in res:
                    results.extend(res['matches'])
    
    return results

def get_rag_stats() -> Dict:
    """Get statistics about the Pinecone index and namespaces"""
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(host=PINECONE_INDEX_HOST)
        stats = index.describe_index_stats()
        
        # Format for dashboard
        namespaces = stats.get('namespaces', {})
        formatted_namespaces = []
        total_vectors = stats.get('total_vector_count', 0)
        
        for ns_name, ns_data in namespaces.items():
            formatted_namespaces.append({
                'name': ns_name,
                'vector_count': ns_data.get('vector_count', 0)
            })
            
        return {
            'total_vectors': total_vectors,
            'namespaces': sorted(formatted_namespaces, key=lambda x: x['name']),
            'dimension': stats.get('dimension'),
            'fullness': stats.get('index_fullness')
        }
    except Exception as e:
        logger.error(f"Failed to get RAG stats: {e}")
        return {'error': str(e)}
