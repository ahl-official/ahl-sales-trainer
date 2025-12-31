#!/usr/bin/env python3
"""
Add database indexes for better query performance
Run once after deploying
"""
import sqlite3

def add_indexes(db_path='data/sales_trainer.db'):
    """Add all necessary indexes"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    indexes = [
        # Session queries
        ('idx_sessions_user_id', 'sessions', 'user_id'),
        ('idx_sessions_status', 'sessions', 'status'),
        ('idx_sessions_category', 'sessions', 'category'),
        ('idx_sessions_started_at', 'sessions', 'started_at'),
        
        # Message queries
        ('idx_messages_session_id', 'messages', 'session_id'),
        ('idx_messages_timestamp', 'messages', 'timestamp'),
        
        # Upload queries
        ('idx_uploads_category', 'uploads', 'category'),
        ('idx_uploads_uploaded_at', 'uploads', 'uploaded_at'),
        
        # Report queries
        ('idx_reports_session_id', 'reports', 'session_id'),
        
        # User queries
        ('idx_users_role', 'users', 'role'),
        ('idx_users_username', 'users', 'username'),  # Already has UNIQUE but add index
    ]
    
    for index_name, table, column in indexes:
        try:
            cursor.execute(f'''
                CREATE INDEX IF NOT EXISTS {index_name} 
                ON {table}({column})
            ''')
            print(f"✓ Created index: {index_name}")
        except Exception as e:
            print(f"✗ Failed to create {index_name}: {e}")
    
    # Composite indexes for common query patterns
    composite_indexes = [
        # Dashboard queries: sessions by user and status
        (
            'idx_sessions_user_status',
            'sessions',
            'user_id, status'
        ),
        # Performance tracking: sessions by user and category
        (
            'idx_sessions_user_category',
            'sessions',
            'user_id, category'
        ),
    ]
    
    for index_name, table, columns in composite_indexes:
        try:
            cursor.execute(f'''
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {table}({columns})
            ''')
            print(f"✓ Created composite index: {index_name}")
        except Exception as e:
            print(f"✗ Failed to create {index_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ All indexes created successfully!")

if __name__ == '__main__':
    add_indexes()
