import csv
import sys
import os
import argparse
from typing import List, Dict, Tuple

# Ensure we can import database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import Database

def import_users_from_csv(csv_path: str, db_path: str = 'data/sales_trainer.db') -> Dict[str, List[str]]:
    """
    Import users from a CSV file.
    
    Expected CSV columns: username, password, name, role (optional)
    """
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
    db = Database(db_path)
    
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Validate headers
        required = {'username', 'password', 'name'}
        if not required.issubset(reader.fieldnames):
            raise ValueError(f"CSV missing required columns. Found: {reader.fieldnames}. Required: {required}")
            
        for row in reader:
            username = row.get('username', '').strip()
            password = row.get('password', '').strip()
            name = row.get('name', '').strip()
            role = row.get('role', 'candidate').strip()
            
            if not all([username, password, name]):
                results['failed'].append(f"Missing data for row: {row}")
                continue
                
            try:
                # Check if user exists
                existing = db.get_user_by_username(username)
                if existing:
                    results['skipped'].append(username)
                    continue
                    
                # Create user
                db.create_user(username, password, name, role)
                results['success'].append(username)
                
            except Exception as e:
                results['failed'].append(f"{username}: {str(e)}")
                
    return results

def main():
    parser = argparse.ArgumentParser(description='Bulk import users from CSV')
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--db', default='data/sales_trainer.db', help='Path to database file')
    
    args = parser.parse_args()
    
    try:
        print(f"Importing users from {args.csv_file}...")
        results = import_users_from_csv(args.csv_file, args.db)
        
        print("\n=== Import Summary ===")
        print(f"✅ Successfully imported: {len(results['success'])}")
        print(f"⏭️  Skipped (already exist): {len(results['skipped'])}")
        print(f"❌ Failed: {len(results['failed'])}")
        
        if results['failed']:
            print("\nFailures:")
            for fail in results['failed']:
                print(f"  - {fail}")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
