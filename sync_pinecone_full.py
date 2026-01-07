
import os
import sys
import sqlite3
from dotenv import load_dotenv
from pinecone import Pinecone
from database import Database

CATEGORIES = [
    'Pre Consultation',
    'Consultation Series',
    'Sales Objections',
    'After Fixing Objection',
    'Full Wig Consultation',
    'Hairline Consultation',
    'Types of Patches',
    'Upselling / Cross Selling',
    'Retail Sales',
    'SMP Sales',
    'Sales Follow up',
    'General Sales'
]

# Load environment variables
load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_INDEX_HOST = os.environ.get('PINECONE_INDEX_HOST')

if not PINECONE_API_KEY or not PINECONE_INDEX_HOST:
    print("Error: Missing Pinecone configuration")
    sys.exit(1)

def sync_pinecone_full():
    print("Starting Full Pinecone Synchronization (Add & Remove)...")
    
    # Initialize DB
    db = Database('data/sales_trainer.db')
    
    # Initialize Pinecone
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(host=PINECONE_INDEX_HOST)
        stats = index.describe_index_stats()
    except Exception as e:
        print(f"Error connecting to Pinecone: {e}")
        return {'error': str(e)}

    pinecone_namespaces = stats.get('namespaces', {})
    print(f"Found {len(pinecone_namespaces)} namespaces in Pinecone.")

    conn = db._get_connection()
    cursor = conn.cursor()

    # Pre-process categories for matching
    # Map snake_case -> Display Name
    cat_map = {c.lower().replace(' ', '_'): c for c in CATEGORIES}
    
    # Sort by length descending to match longest prefix first
    sorted_cat_keys = sorted(cat_map.keys(), key=len, reverse=True)

    # 1. ADD: Sync Pinecone -> SQLite
    synced_count = 0
    active_db_keys = set() # (category, video_name)

    for ns_name, ns_data in pinecone_namespaces.items():
        vector_count = ns_data.get('vector_count', 0)
        
        # Parse namespace: {category}_{video_name}
        matched_category = None
        video_slug = None
        
        for cat_key in sorted_cat_keys:
            if ns_name.startswith(cat_key + '_'):
                matched_category = cat_map[cat_key]
                video_slug = ns_name[len(cat_key)+1:]
                break
        
        if not matched_category:
            print(f"Skipping namespace '{ns_name}': Could not match to any known category.")
            continue
            
        video_name = video_slug.replace('_', ' ').title()
        active_db_keys.add((matched_category, video_name))
        
        # Check if exists in DB
        cursor.execute('''
            SELECT id FROM uploads 
            WHERE category = ? AND video_name = ?
        ''', (matched_category, video_name))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update chunk count just in case
            cursor.execute('''
                UPDATE uploads SET chunks_created = ? WHERE id = ?
            ''', (vector_count, existing['id']))
        else:
            print(f"  + Adding local record: Category='{matched_category}', Video='{video_name}'")
            cursor.execute('''
                INSERT INTO uploads (category, video_name, filename, chunks_created, uploaded_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (matched_category, video_name, 'Synced from Pinecone', vector_count, 1))
            synced_count += 1

    # 2. REMOVE: Sync SQLite -> Pinecone (Delete local if not in Pinecone)
    print("\nChecking for stale local records...")
    cursor.execute('SELECT id, category, video_name FROM uploads')
    all_uploads = cursor.fetchall()
    
    deleted_count = 0
    for upload in all_uploads:
        key = (upload['category'], upload['video_name'])
        
        # If this local record is NOT in the set of active Pinecone namespaces we just processed
        # And assuming all valid uploads MUST be in Pinecone
        if key not in active_db_keys:
            print(f"  - Deleting stale record: ID={upload['id']}, {upload['category']} - {upload['video_name']}")
            cursor.execute('DELETE FROM uploads WHERE id = ?', (upload['id'],))
            deleted_count += 1

    conn.commit()
    conn.close()
    
    print(f"\nSync complete.")
    print(f"  - Added: {synced_count}")
    print(f"  - Deleted: {deleted_count}")

if __name__ == "__main__":
    sync_pinecone_full()
