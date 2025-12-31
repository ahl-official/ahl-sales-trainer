from backend.database import Database
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

db = Database('backend/data/sales_trainer.db')
users = db.list_users()
print(f"Users found: {len(users)}")
for u in users:
    print(f"ID: {u['id']}, Username: {u['username']}, Role: {u['role']}")
