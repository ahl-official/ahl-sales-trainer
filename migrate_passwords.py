#!/usr/bin/env python3
import sqlite3
import bcrypt

def migrate_passwords(db_path='data/sales_trainer.db'):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, password_hash FROM users')
    users = cursor.fetchall()
    migrated = 0
    skipped = 0
    for user in users:
        user_id = user['id']
        username = user['username']
        old_hash = user['password_hash']
        if isinstance(old_hash, str) and old_hash.startswith('$2b$'):
            skipped += 1
            continue
        known = {'admin': 'admin123'}
        if username in known:
            password = known[username]
            new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user_id))
            migrated += 1
        else:
            temp_password = f'TempPass{user_id}!'
            new_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user_id))
            migrated += 1
    conn.commit()
    conn.close()
    print(f'Migration complete. Migrated: {migrated}, Skipped: {skipped}, Total: {len(users)}')

if __name__ == '__main__':
    migrate_passwords()
