
import sys
import os

# Add root to path so imports work
sys.path.append(os.getcwd())

from database import Database

def create_admin():
    # Use the correct relative path to the database
    db_path = 'data/sales_trainer.db'
    print(f"Connecting to database at: {db_path}")
    db = Database(db_path)
    
    # Check if admin exists
    admin = db.get_user_by_username('admin')
    if admin:
        print("Admin user already exists. Updating password...")
        # Update password directly
        new_hash = db._hash_password('admin123')
        conn = db._get_connection()
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, admin['id']))
        conn.commit()
        conn.close()
        print("Admin password updated to 'admin123'.")
    else:
        print("Creating new admin user...")
        try:
            user_id = db.create_user('admin', 'admin123', 'System Admin', 'admin')
            print(f"Admin user created with ID: {user_id}")
        except Exception as e:
            print(f"Error creating admin: {e}")

if __name__ == "__main__":
    create_admin()
