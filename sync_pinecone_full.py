
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
    if 'localhost' in (PINECONE_INDEX_HOST or '').lower():
        return {'error': 'Invalid PINECONE_INDEX_HOST. Set to your Pinecone index URL (https://...pinecone.io).'}
    
    # Initialize DB (respect env path)
    db = Database(os.environ.get('DATABASE_PATH', 'data/sales_trainer.db'))
    
    # Initialize Pinecone
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(host=PINECONE_INDEX_HOST)
        stats = index.describe_index_stats()
    except Exception as e:
        print(f"Error connecting to Pinecone: {e}")
        return {'error': f"{e}. Ensure PINECONE_INDEX_HOST is the full index URL from the Pinecone dashboard (https://...pinecone.io)."}

    pinecone_namespaces = stats.get('namespaces', {})
    print(f"Found {len(pinecone_namespaces)} namespaces in Pinecone.")

    conn = db._get_connection()
    cursor = conn.cursor()

    # Build dynamic prefix map from DB categories and courses
    cursor.execute('''
        SELECT c.id AS course_id, c.slug AS course_slug, cc.name AS category_name
        FROM course_categories cc
        JOIN courses c ON cc.course_id = c.id
    ''')
    rows = cursor.fetchall()
    prefix_map = {}  # prefix -> (course_id, category_name)
    for row in rows:
        course_id = row['course_id']
        course_slug = (row['course_slug'] or '').lower().replace(' ', '_')
        cat_slug = (row['category_name'] or '').lower().replace(' ', '_')
        if course_id == 1:
            prefix = f"{cat_slug}"
        else:
            prefix = f"{course_slug}_{cat_slug}"
        prefix_map[prefix] = (course_id, row['category_name'])
    # Sort prefixes by length to match longest first
    sorted_prefixes = sorted(prefix_map.keys(), key=len, reverse=True)

    # 1. ADD: Sync Pinecone -> SQLite
    synced_count = 0
    active_db_keys = set() # (category, video_name)

    for ns_name, ns_data in pinecone_namespaces.items():
        vector_count = ns_data.get('vector_count', 0)
        matched_prefix = None
        for prefix in sorted_prefixes:
            if ns_name.startswith(prefix + '_'):
                matched_prefix = prefix
                break
        if not matched_prefix:
            print(f"Skipping namespace '{ns_name}': Could not match to any known category.")
            continue
        course_id, category_name = prefix_map[matched_prefix]
        video_slug = ns_name[len(matched_prefix) + 1:]
        video_name = video_slug.replace('_', ' ').title()
        active_db_keys.add((course_id, category_name, video_name))
        # Check if exists in DB for this course
        cursor.execute('''
            SELECT id FROM uploads 
            WHERE category = ? AND video_name = ? AND course_id = ?
        ''', (category_name, video_name, course_id))
        existing = cursor.fetchone()
        if existing:
            cursor.execute('UPDATE uploads SET chunks_created = ? WHERE id = ?', (vector_count, existing['id']))
        else:
            print(f"  + Adding local record: CourseID={course_id}, Category='{category_name}', Video='{video_name}'")
            cursor.execute('''
                INSERT INTO uploads (category, video_name, filename, chunks_created, uploaded_by, course_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (category_name, video_name, 'Synced from Pinecone', vector_count, 1, course_id))
            synced_count += 1

    # 2. REMOVE: Sync SQLite -> Pinecone (Delete local if not in Pinecone)
    print("\nChecking for stale local records...")
    cursor.execute('SELECT id, category, video_name, course_id FROM uploads')
    all_uploads = cursor.fetchall()
    
    deleted_count = 0
    for upload in all_uploads:
        key = (upload['course_id'], upload['category'], upload['video_name'])
        if key not in active_db_keys:
            print(f"  - Deleting stale record: ID={upload['id']}, {upload['category']} - {upload['video_name']}")
            cursor.execute('DELETE FROM uploads WHERE id = ?', (upload['id'],))
            deleted_count += 1

    conn.commit()
    conn.close()
    
    print(f"\nSync complete.")
    print(f"  - Added: {synced_count}")
    print(f"  - Deleted: {deleted_count}")
    return {'added': synced_count, 'deleted': deleted_count}

if __name__ == "__main__":
    sync_pinecone_full()
