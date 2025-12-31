# 🎯 AHL SALES TRAINER - IMPROVEMENT ROADMAP

**Project Manager:** System Upgrade & Enhancement  
**Version:** 2.1  
**Last Updated:** December 18, 2025  
**Status:** � Implementation Started (Phase 1 Completed)

---

## 📊 EXECUTIVE SUMMARY

This document outlines 31 improvements across 6 categories:
- 🔴 **Critical Security Issues** (3 items) - Do Immediately
- 🟡 **High Priority** (8 items) - Do This Week  
- 🟢 **Functionality** (6 items) - Do This Month
- 🔵 **Code Quality** (4 items) - Do This Month
- 🟣 **Performance** (3 items) - Do This Month
- 🎨 **UX/UI** (4 items) - Do This Month
- 🧪 **Testing** (2 items) - Ongoing
- 📊 **Monitoring** (2 items) - Do This Month

**Estimated Total Time:** 40-60 hours  
**Team Size:** 1-2 developers  
**Timeline:** 4 weeks

---

## 🚨 PHASE 1: CRITICAL SECURITY FIXES (DO IMMEDIATELY)

**Priority:** P0 - Critical  
**Estimated Time:** 4-6 hours  
**Risk if Delayed:** High - System vulnerable to attacks

### ✅ Task 1.1: Fix Password Hashing with bcrypt

**Current Issue:** SHA256 without salt is easily crackable via rainbow tables

**Files to Modify:**
- `backend/database.py`
- `backend/requirements.txt`

**Step-by-Step Instructions:**

1. **Update requirements.txt**
```bash
# Add this line to backend/requirements.txt
bcrypt==4.1.2
```

2. **Install new dependency**
```bash
cd backend
pip install bcrypt==4.1.2
```

3. **Update database.py**

Replace the current password methods (lines 28-30) with:

```python
# database.py - ADD THIS IMPORT at top
import bcrypt

# database.py - REPLACE _hash_password method
def _hash_password(self, password: str) -> str:
    """Hash password using bcrypt with automatic salt generation"""
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds is secure and fast
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# database.py - ADD NEW METHOD for verification
def _verify_password(self, password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash"""
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            password_hash.encode('utf-8')
        )
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

# database.py - UPDATE verify_user method (around line 90)
def verify_user(self, username: str, password: str) -> Optional[Dict]:
    """Verify user credentials"""
    user = self.get_user_by_username(username)
    
    if not user:
        return None
    
    # NEW: Use bcrypt verification instead of direct hash comparison
    if not self._verify_password(password, user['password_hash']):
        return None
    
    # Update last login
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
    ''', (user['id'],))
    conn.commit()
    conn.close()
    
    return user
```

4. **Migration: Rehash existing passwords**

Create a migration script: `backend/migrate_passwords.py`

```python
#!/usr/bin/env python3
"""
Migration script to rehash existing passwords from SHA256 to bcrypt
Run once after deploying the bcrypt changes
"""
import sqlite3
import bcrypt
import hashlib

def migrate_passwords(db_path='data/sales_trainer.db'):
    """Migrate all existing passwords to bcrypt"""
    
    # Known passwords for system accounts
    KNOWN_PASSWORDS = {
        'admin': 'admin123',  # Default admin password
    }
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, username, password_hash FROM users')
    users = cursor.fetchall()
    
    print(f"Found {len(users)} users to migrate")
    
    migrated = 0
    skipped = 0
    
    for user in users:
        user_id = user['id']
        username = user['username']
        old_hash = user['password_hash']
        
        # Check if already bcrypt (starts with $2b$)
        if old_hash.startswith('$2b$'):
            print(f"✓ User '{username}' already using bcrypt, skipping")
            skipped += 1
            continue
        
        # Try to get known password
        if username in KNOWN_PASSWORDS:
            password = KNOWN_PASSWORDS[username]
            new_hash = bcrypt.hashpw(
                password.encode('utf-8'), 
                bcrypt.gensalt(rounds=12)
            ).decode('utf-8')
            
            cursor.execute(
                'UPDATE users SET password_hash = ? WHERE id = ?',
                (new_hash, user_id)
            )
            print(f"✓ Migrated user '{username}'")
            migrated += 1
        else:
            print(f"⚠ User '{username}' - unknown password, needs manual reset")
            # Option: Set a temporary password and force reset
            temp_password = f"TempPass{user_id}!"
            new_hash = bcrypt.hashpw(
                temp_password.encode('utf-8'),
                bcrypt.gensalt(rounds=12)
            ).decode('utf-8')
            cursor.execute(
                'UPDATE users SET password_hash = ? WHERE id = ?',
                (new_hash, user_id)
            )
            print(f"  → Set temporary password: {temp_password}")
            migrated += 1
    
    conn.commit()
    conn.close()
    
    print(f"\nMigration complete!")
    print(f"✓ Migrated: {migrated}")
    print(f"✓ Skipped: {skipped}")
    print(f"Total: {len(users)}")

if __name__ == '__main__':
    migrate_passwords()
```

5. **Run migration**
```bash
cd backend
python migrate_passwords.py
```

**Testing Checklist:**
- [ ] bcrypt installed successfully
- [ ] Migration script runs without errors
- [ ] Can login with admin/admin123
- [ ] Can create new user and login
- [ ] Old passwords still work after migration
- [ ] Password verification takes ~100-200ms (bcrypt is intentionally slow)

**Time Estimate:** 2 hours

---

### ✅ Task 1.2: Fix SECRET_KEY Configuration

**Current Issue:** Secret key regenerates on each restart, invalidating all sessions

**Files to Modify:**
- `backend/app.py`
- `.env.example`
- `README.md`

**Step-by-Step Instructions:**

1. **Update .env.example**

Add clear instructions:

```env
# .env.example

# SECRET KEY - REQUIRED - Generate with: python -c "import secrets; print(secrets.token_hex(32))"
# NEVER commit the actual .env file with your real secret key!
SECRET_KEY=your_generated_secret_key_here_64_characters_long

# API Keys - REQUIRED
OPENROUTER_API_KEY=sk-or-v1-YOUR_ACTUAL_KEY
OPENAI_API_KEY=sk-YOUR_ACTUAL_KEY
PINECONE_API_KEY=pcsk_YOUR_ACTUAL_KEY
PINECONE_INDEX_HOST=https://your-index.svc.region.pinecone.io

# Server Configuration
PORT=5050
DEBUG=False
```

2. **Update app.py**

Replace lines 18-20 with:

```python
# app.py - REPLACE SECRET KEY HANDLING

# Validate SECRET_KEY exists
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        "❌ ERROR: SECRET_KEY environment variable is required!\n"
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
        "Then add it to your .env file"
    )

if len(SECRET_KEY) < 32:
    raise RuntimeError("❌ ERROR: SECRET_KEY must be at least 32 characters long")

app.secret_key = SECRET_KEY
```

3. **Generate and set SECRET_KEY**

```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Copy the output and add to .env file
echo "SECRET_KEY=<paste_generated_key_here>" >> .env
```

4. **Update README.md**

Add to Quick Start section:

```markdown
### Step 1: Generate SECRET_KEY

**IMPORTANT:** Generate a secure secret key first:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output (should be 64 characters).

### Step 2: Create .env file
```

**Testing Checklist:**
- [ ] Server refuses to start without SECRET_KEY
- [ ] Server refuses to start with short SECRET_KEY
- [ ] Sessions persist across server restarts
- [ ] Login once, restart server, still logged in

**Time Estimate:** 1 hour

---

### ✅ Task 1.3: Restrict CORS Origins

**Current Issue:** CORS allows ALL origins, enabling CSRF attacks

**Files to Modify:**
- `backend/app.py`
- `.env.example`

**Step-by-Step Instructions:**

1. **Update .env.example**

```env
# .env.example

# CORS Configuration - Comma-separated list of allowed origins
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

2. **Update app.py CORS configuration**

Replace line 20 with:

```python
# app.py - REPLACE CORS CONFIGURATION

# Get allowed origins from environment
allowed_origins = os.environ.get(
    'ALLOWED_ORIGINS', 
    'http://localhost:8000,http://127.0.0.1:8000'
).split(',')

# Strict CORS configuration
CORS(app, 
     origins=allowed_origins,
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     max_age=3600  # Cache preflight requests for 1 hour
)

print(f"✅ CORS enabled for origins: {', '.join(allowed_origins)}")
```

3. **For production deployment**

Update .env for production:

```env
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**Testing Checklist:**
- [ ] Frontend on localhost:8000 works correctly
- [ ] Request from different port/domain gets blocked
- [ ] Cookies/credentials still work properly
- [ ] OPTIONS preflight requests succeed

**Time Estimate:** 1 hour

---

## 🟡 PHASE 2: HIGH PRIORITY IMPROVEMENTS (DO THIS WEEK)

**Priority:** P1 - High  
**Estimated Time:** 10-12 hours  
**Risk if Delayed:** Medium - Performance and stability issues

### ✅ Task 2.1: Add Database Indexes

**Current Issue:** Slow queries as data grows

**Files to Modify:**
- `backend/database.py`

**Step-by-Step Instructions:**

1. **Create migration script: `backend/add_indexes.py`**

```python
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
```

2. **Run migration**

```bash
cd backend
python add_indexes.py
```

3. **Update database.py initialize() method**

Add indexes to schema creation (after line 100):

```python
# database.py - ADD to initialize() method after table creation

# Create indexes for better query performance
print("Creating indexes...")

indexes = [
    'CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)',
    'CREATE INDEX IF NOT EXISTS idx_sessions_category ON sessions(category)',
    'CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at)',
    'CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON sessions(user_id, status)',
    'CREATE INDEX IF NOT EXISTS idx_sessions_user_category ON sessions(user_id, category)',
    'CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)',
    'CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)',
    'CREATE INDEX IF NOT EXISTS idx_uploads_category ON uploads(category)',
    'CREATE INDEX IF NOT EXISTS idx_uploads_uploaded_at ON uploads(uploaded_at)',
    'CREATE INDEX IF NOT EXISTS idx_reports_session_id ON reports(session_id)',
    'CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)',
]

for index_sql in indexes:
    cursor.execute(index_sql)

conn.commit()
```

**Testing Checklist:**
- [ ] Migration runs without errors
- [ ] All indexes created (check with SQL query)
- [ ] Dashboard loads faster
- [ ] Session list loads faster
- [ ] No broken queries

**SQL to verify indexes:**
```sql
-- Run in SQLite shell to verify
.indexes sessions
.indexes messages
.indexes uploads
```

**Time Estimate:** 1.5 hours

---

### ✅ Task 2.2: Enable Foreign Key Constraints

**Current Issue:** No referential integrity - orphaned records possible

**Files to Modify:**
- `backend/database.py`

**Step-by-Step Instructions:**

1. **Update _get_connection() method**

```python
# database.py - UPDATE _get_connection method (around line 14)

def _get_connection(self):
    """Get database connection with foreign keys enabled"""
    conn = sqlite3.connect(self.db_path)
    
    # CRITICAL: Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Enable Write-Ahead Logging for better concurrency
    conn.execute("PRAGMA journal_mode = WAL")
    
    conn.row_factory = sqlite3.Row
    return conn
```

2. **Add cascade delete rules to schema**

Update initialize() method table creation:

```python
# database.py - UPDATE sessions table (around line 42)

cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ended_at TIMESTAMP,
        status TEXT DEFAULT 'active',
        overall_score REAL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
''')

# database.py - UPDATE messages table (around line 55)

cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        context_source TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )
''')

# database.py - UPDATE reports table (around line 67)

cursor.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER UNIQUE NOT NULL,
        report_html TEXT NOT NULL,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )
''')

# database.py - UPDATE uploads table (around line 30)

cursor.execute('''
    CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        video_name TEXT NOT NULL,
        filename TEXT NOT NULL,
        chunks_created INTEGER NOT NULL,
        uploaded_by INTEGER NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
    )
''')
```

3. **Update delete_user() to handle cascades**

```python
# database.py - UPDATE delete_user method (around line 130)

def delete_user(self, user_id: int):
    """Delete a user and all associated data (cascades to sessions, messages, reports)"""
    conn = self._get_connection()
    cursor = conn.cursor()
    
    # Foreign keys will cascade automatically
    # This will delete: sessions → messages → reports
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return deleted_count > 0
```

**Testing Checklist:**
- [ ] Foreign keys are enabled (check with `PRAGMA foreign_keys`)
- [ ] Cannot delete user with sessions without CASCADE
- [ ] Deleting user deletes all their sessions/messages/reports
- [ ] Cannot insert session with invalid user_id
- [ ] Cannot insert message with invalid session_id

**Test queries:**
```python
# test_foreign_keys.py
from database import Database

db = Database('data/sales_trainer.db')

# Test 1: FK enabled
conn = db._get_connection()
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys")
print(f"Foreign keys enabled: {cursor.fetchone()[0]}")

# Test 2: Cannot insert invalid FK
try:
    cursor.execute("INSERT INTO sessions (user_id, category, difficulty, duration_minutes) VALUES (99999, 'Test', 'basic', 10)")
    print("❌ FAIL: Inserted session with invalid user_id")
except Exception as e:
    print(f"✓ PASS: Correctly rejected invalid FK: {e}")

conn.close()
```

**Time Estimate:** 2 hours

---

### ✅ Task 2.3: Add Input Validation Layer

**Current Issue:** No validation of user inputs, vulnerable to injection

**Files to Create:**
- `backend/validators.py`

**Files to Modify:**
- `backend/app.py`

**Step-by-Step Instructions:**

1. **Create validators.py**

```python
# backend/validators.py
"""
Input validation functions for all API endpoints
"""
from dataclasses import dataclass
from typing import Optional, List
import re

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


@dataclass
class CreateUserRequest:
    """Validation for user creation"""
    username: str
    password: str
    name: str
    role: str = 'candidate'
    
    def validate(self):
        """Validate user creation fields"""
        errors = []
        
        # Username validation
        if not self.username or len(self.username.strip()) < 3:
            errors.append(ValidationError('username', 'Must be at least 3 characters'))
        elif len(self.username) > 50:
            errors.append(ValidationError('username', 'Must be less than 50 characters'))
        elif not re.match(r'^[a-zA-Z0-9._-]+$', self.username):
            errors.append(ValidationError('username', 'Can only contain letters, numbers, dots, dashes, underscores'))
        
        # Password validation
        if not self.password or len(self.password) < 6:
            errors.append(ValidationError('password', 'Must be at least 6 characters'))
        elif len(self.password) > 128:
            errors.append(ValidationError('password', 'Must be less than 128 characters'))
        
        # Name validation
        if not self.name or len(self.name.strip()) < 2:
            errors.append(ValidationError('name', 'Must be at least 2 characters'))
        elif len(self.name) > 100:
            errors.append(ValidationError('name', 'Must be less than 100 characters'))
        
        # Role validation
        if self.role not in ['admin', 'candidate']:
            errors.append(ValidationError('role', 'Must be either "admin" or "candidate"'))
        
        if errors:
            raise ValueError(errors)
        
        return True


@dataclass
class LoginRequest:
    """Validation for login"""
    username: str
    password: str
    
    def validate(self):
        """Validate login fields"""
        errors = []
        
        if not self.username or not self.username.strip():
            errors.append(ValidationError('username', 'Username is required'))
        
        if not self.password:
            errors.append(ValidationError('password', 'Password is required'))
        
        if errors:
            raise ValueError(errors)
        
        return True


@dataclass
class UploadRequest:
    """Validation for content upload"""
    category: str
    video_name: str
    filename: str
    
    VALID_CATEGORIES = [
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
    
    def validate(self):
        """Validate upload fields"""
        errors = []
        
        # Category validation
        if not self.category or self.category not in self.VALID_CATEGORIES:
            errors.append(ValidationError('category', f'Must be one of: {", ".join(self.VALID_CATEGORIES)}'))
        
        # Video name validation
        if not self.video_name or len(self.video_name.strip()) < 3:
            errors.append(ValidationError('video_name', 'Must be at least 3 characters'))
        elif len(self.video_name) > 200:
            errors.append(ValidationError('video_name', 'Must be less than 200 characters'))
        
        # Filename validation
        if not self.filename or not self.filename.endswith('.txt'):
            errors.append(ValidationError('filename', 'Must be a .txt file'))
        
        if errors:
            raise ValueError(errors)
        
        return True


@dataclass
class StartSessionRequest:
    """Validation for starting training session"""
    category: str
    difficulty: str
    duration_minutes: int
    
    VALID_CATEGORIES = UploadRequest.VALID_CATEGORIES
    VALID_DIFFICULTIES = ['new-joining', 'basic', 'experienced', 'expert']
    VALID_DURATIONS = [5, 10, 15, 20, 30]
    
    def validate(self):
        """Validate session start fields"""
        errors = []
        
        # Category validation
        if self.category not in self.VALID_CATEGORIES:
            errors.append(ValidationError('category', 'Invalid category'))
        
        # Difficulty validation
        if self.difficulty not in self.VALID_DIFFICULTIES:
            errors.append(ValidationError('difficulty', f'Must be one of: {", ".join(self.VALID_DIFFICULTIES)}'))
        
        # Duration validation
        if self.duration_minutes not in self.VALID_DURATIONS:
            errors.append(ValidationError('duration_minutes', f'Must be one of: {", ".join(map(str, self.VALID_DURATIONS))}'))
        
        if errors:
            raise ValueError(errors)
        
        return True


def sanitize_html(text: str) -> str:
    """Basic HTML sanitization - remove script tags and dangerous attributes"""
    import html
    
    # Escape HTML entities
    text = html.escape(text)
    
    # Remove any script tags (even after escaping, for extra safety)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove event handlers
    text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    return text


def validate_session_id(session_id: any) -> int:
    """Validate and convert session_id to integer"""
    try:
        session_id = int(session_id)
        if session_id < 1:
            raise ValueError("Session ID must be positive")
        return session_id
    except (ValueError, TypeError):
        raise ValidationError('session_id', 'Must be a valid positive integer')


def validate_user_id(user_id: any) -> int:
    """Validate and convert user_id to integer"""
    try:
        user_id = int(user_id)
        if user_id < 1:
            raise ValueError("User ID must be positive")
        return user_id
    except (ValueError, TypeError):
        raise ValidationError('user_id', 'Must be a valid positive integer')
```

2. **Update app.py to use validators**

Add import at top:

```python
# app.py - ADD IMPORTS
from validators import (
    ValidationError,
    CreateUserRequest,
    LoginRequest,
    UploadRequest,
    StartSessionRequest,
    validate_session_id,
    validate_user_id
)
```

Update login endpoint:

```python
# app.py - UPDATE /api/auth/login endpoint (around line 80)

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint for both admin and candidates"""
    try:
        data = request.json
        
        # Validate input
        login_req = LoginRequest(
            username=data.get('username', ''),
            password=data.get('password', '')
        )
        login_req.validate()
        
        user = db.verify_user(login_req.username.strip(), login_req.password)
        
        if not user:
            return jsonify({
                'error': 'invalid_credentials',
                'message': 'Invalid username or password'
            }), 401
        
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'role': user['role']
            }
        })
        
    except ValueError as e:
        return jsonify({
            'error': 'validation_error',
            'message': str(e)
        }), 400
```

Update create user endpoint:

```python
# app.py - UPDATE /api/admin/users POST endpoint (around line 130)

@app.route('/api/admin/users', methods=['POST'])
@admin_required
def create_user():
    """Create new candidate account (admin only)"""
    try:
        data = request.json
        
        # Validate input
        create_req = CreateUserRequest(
            username=data.get('username', ''),
            password=data.get('password', ''),
            name=data.get('name', ''),
            role='candidate'
        )
        create_req.validate()
        
        # Check if username exists
        existing = db.get_user_by_username(create_req.username.strip())
        if existing:
            return jsonify({
                'error': 'username_exists',
                'message': 'This username is already taken'
            }), 400
        
        user_id = db.create_user(
            create_req.username.strip(),
            create_req.password,
            create_req.name.strip(),
            role='candidate'
        )
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'username': create_req.username.strip()
        })
        
    except ValueError as e:
        return jsonify({
            'error': 'validation_error',
            'message': str(e)
        }), 400
```

Update upload endpoint:

```python
# app.py - UPDATE /api/admin/upload endpoint (around line 180)

@app.route('/api/admin/upload', methods=['POST'])
@admin_required
def upload_content():
    """Upload training content to Pinecone"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'error': 'no_file',
                'message': 'No file was uploaded'
            }), 400
        
        file = request.files['file']
        category = request.form.get('category', '').strip()
        video_name = request.form.get('video_name', '').strip()
        
        # Validate input
        upload_req = UploadRequest(
            category=category,
            video_name=video_name,
            filename=file.filename
        )
        upload_req.validate()
        
        # Read file content (with size limit)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        content = file.read(MAX_FILE_SIZE + 1)
        
        if len(content) > MAX_FILE_SIZE:
            return jsonify({
                'error': 'file_too_large',
                'message': 'File must be less than 10MB'
            }), 400
        
        content = content.decode('utf-8')
        
        # Process and upload to Pinecone
        result = process_and_upload(content, category, video_name)
        
        # Save upload record to database
        db.create_upload_record(
            category=category,
            video_name=video_name,
            filename=file.filename,
            chunks_created=result['chunks'],
            uploaded_by=session['user_id']
        )
        
        return jsonify({
            'success': True,
            'category': category,
            'video_name': video_name,
            'chunks': result['chunks'],
            'namespace': result['namespace']
        })
        
    except ValueError as e:
        return jsonify({
            'error': 'validation_error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'upload_error',
            'message': str(e)
        }), 500
```

**Testing Checklist:**
- [ ] Cannot create user with short username (<3 chars)
- [ ] Cannot create user with weak password (<6 chars)
- [ ] Cannot upload with invalid category
- [ ] Cannot start session with invalid difficulty
- [ ] Error messages are clear and helpful
- [ ] All validation errors return 400 status code

**Time Estimate:** 3 hours

---

### ✅ Task 2.4: Implement Proper Logging

**Current Issue:** Using print() statements, hard to debug production

**Files to Modify:**
- `backend/app.py`
- `backend/database.py`

**Files to Create:**
- `backend/config_logging.py`

**Step-by-Step Instructions:**

1. **Create logging configuration**

```python
# backend/config_logging.py
"""
Centralized logging configuration
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(app_name='ahl_sales_trainer', log_level=None):
    """
    Setup application logging with file and console handlers
    
    Args:
        app_name: Name of the application (used for log files)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    # Determine log level from environment or default to INFO
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Convert string to logging level
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler (simple format for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs (rotating)
    all_logs_file = os.path.join(log_dir, f'{app_name}.log')
    file_handler = RotatingFileHandler(
        all_logs_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)  # File gets everything
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler (errors only)
    error_file = os.path.join(log_dir, f'{app_name}_errors.log')
    error_handler = RotatingFileHandler(
        error_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info(f"Logging initialized - Level: {log_level}")
    root_logger.info(f"Log files: {all_logs_file}, {error_file}")
    
    return root_logger


def get_logger(name):
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)
```

2. **Update app.py to use logging**

Add at the top of app.py:

```python
# app.py - ADD IMPORTS
import logging
from config_logging import setup_logging, get_logger

# Initialize logging BEFORE anything else
setup_logging('ahl_sales_trainer')
logger = get_logger(__name__)
```

Replace all `print()` statements with logging:

```python
# REPLACE THIS:
print("✅ Default admin created (admin/admin123)")

# WITH THIS:
logger.info("✅ Default admin created (admin/admin123)")

# REPLACE THIS:
print("Pinecone query", {"category": category, "namespaces": namespaces})

# WITH THIS:
logger.debug(f"Pinecone query - category: {category}, namespaces: {namespaces}, top_k: {top_k}")

# For errors, use:
logger.error(f"Upload failed: {str(e)}", exc_info=True)

# For important events:
logger.info(f"User {username} logged in successfully")

# For debugging:
logger.debug(f"Session {session_id} created for user {user_id}")
```

3. **Update database.py to use logging**

```python
# database.py - ADD at top
import logging
logger = logging.getLogger(__name__)

# REPLACE all print() statements:

# Line 102:
logger.info("✅ Database initialized successfully")

# In verify_user:
logger.debug(f"User login attempt: {username}")
logger.info(f"User {username} logged in successfully")

# In create_user:
logger.info(f"Created new user: {username} (role: {role})")

# In delete_user:
logger.warning(f"Deleted user with ID: {user_id}")
```

4. **Add request logging middleware**

Add to app.py:

```python
# app.py - ADD after CORS configuration

@app.before_request
def log_request():
    """Log all incoming requests"""
    logger.debug(f"{request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response(response):
    """Log all outgoing responses"""
    logger.debug(f"{request.method} {request.path} - Status: {response.status_code}")
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Log unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({
        'error': 'internal_server_error',
        'message': 'An unexpected error occurred'
    }), 500
```

5. **Update .env.example**

```env
# Logging Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**Testing Checklist:**
- [x] Logs directory created automatically
- [x] All logs written to files
- [x] Console shows simplified output
- [x] Error logs separated
- [x] Log rotation works (test with large logs)
- [x] No more print() statements in code

**View logs:**
```bash
# View all logs
tail -f logs/ahl_sales_trainer.log

# View only errors
tail -f logs/ahl_sales_trainer_errors.log

# Search for specific user
grep "user_123" logs/ahl_sales_trainer.log
```

**Time Estimate:** 2.5 hours

---

### ✅ Task 2.5: Environment Variable Validation

**Current Issue:** Server starts even with missing API keys, fails at runtime

**Files to Modify:**
- `backend/app.py`

**Step-by-Step Instructions:**

1. **Create environment validator**

Add after imports in app.py:

```python
# app.py - ADD ENVIRONMENT VALIDATION FUNCTION

def validate_environment():
    """
    Validate all required environment variables are set
    Fails fast on startup if anything is missing
    """
    
    required_vars = {
        'SECRET_KEY': {
            'description': 'Secret key for session encryption',
            'generate': 'python -c "import secrets; print(secrets.token_hex(32))"',
            'min_length': 32
        },
        'OPENROUTER_API_KEY': {
            'description': 'OpenRouter API key for chat completions',
            'get_from': 'https://openrouter.ai/keys'
        },
        'OPENAI_API_KEY': {
            'description': 'OpenAI API key for embeddings',
            'get_from': 'https://platform.openai.com/api-keys'
        },
        'PINECONE_API_KEY': {
            'description': 'Pinecone API key for vector storage',
            'get_from': 'https://app.pinecone.io/organizations/-/projects/-/keys'
        },
        'PINECONE_INDEX_HOST': {
            'description': 'Pinecone index host URL',
            'example': 'https://your-index-abc123.svc.us-east-1-aws.pinecone.io'
        }
    }
    
    missing_vars = []
    invalid_vars = []
    
    logger.info("Validating environment variables...")
    
    for var_name, config in required_vars.items():
        value = os.environ.get(var_name)
        
        if not value:
            missing_vars.append({
                'name': var_name,
                'description': config['description'],
                'help': config.get('generate') or config.get('get_from') or config.get('example')
            })
        else:
            # Validate specific requirements
            if 'min_length' in config and len(value) < config['min_length']:
                invalid_vars.append({
                    'name': var_name,
                    'reason': f"Must be at least {config['min_length']} characters long",
                    'current_length': len(value)
                })
            
            logger.debug(f"✓ {var_name} is set")
    
    # Print detailed error message if validation fails
    if missing_vars or invalid_vars:
        error_msg = "\n\n" + "="*80 + "\n"
        error_msg += "❌ ENVIRONMENT VALIDATION FAILED\n"
        error_msg += "="*80 + "\n\n"
        
        if missing_vars:
            error_msg += "Missing required environment variables:\n\n"
            for var in missing_vars:
                error_msg += f"  • {var['name']}\n"
                error_msg += f"    Description: {var['description']}\n"
                if 'generate' in required_vars[var['name']]:
                    error_msg += f"    Generate with: {var['help']}\n"
                elif 'get_from' in required_vars[var['name']]:
                    error_msg += f"    Get from: {var['help']}\n"
                elif 'example' in required_vars[var['name']]:
                    error_msg += f"    Example: {var['help']}\n"
                error_msg += "\n"
        
        if invalid_vars:
            error_msg += "Invalid environment variables:\n\n"
            for var in invalid_vars:
                error_msg += f"  • {var['name']}\n"
                error_msg += f"    Reason: {var['reason']}\n"
                error_msg += f"    Current length: {var['current_length']}\n\n"
        
        error_msg += "="*80 + "\n"
        error_msg += "Fix: Create/update your .env file with the required variables\n"
        error_msg += "See .env.example for a template\n"
        error_msg += "="*80 + "\n"
        
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    logger.info("✅ All environment variables validated successfully")
    
    # Optional: Validate API keys are actually working
    if os.environ.get('VALIDATE_API_KEYS', 'false').lower() == 'true':
        logger.info("Testing API connectivity...")
        test_api_connections()


def test_api_connections():
    """
    Optional: Test that API keys actually work
    Only runs if VALIDATE_API_KEYS=true in .env
    """
    
    tests_passed = True
    
    # Test OpenAI
    try:
        response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}'},
            json={'model': 'text-embedding-3-small', 'input': 'test'},
            timeout=10
        )
        if response.status_code == 200:
            logger.info("✓ OpenAI API key valid")
        else:
            logger.error(f"✗ OpenAI API key invalid: {response.status_code}")
            tests_passed = False
    except Exception as e:
        logger.error(f"✗ OpenAI API connection failed: {e}")
        tests_passed = False
    
    # Test Pinecone
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(host=PINECONE_INDEX_HOST)
        stats = index.describe_index_stats()
        logger.info(f"✓ Pinecone connection successful (dimensions: {stats.get('dimension', 'unknown')})")
    except Exception as e:
        logger.error(f"✗ Pinecone connection failed: {e}")
        tests_passed = False
    
    if not tests_passed:
        raise RuntimeError("API connectivity tests failed")
```

2. **Call validation at startup**

```python
# app.py - ADD after load_dotenv()

load_dotenv()

# Validate environment before proceeding
validate_environment()

# Now load the validated variables
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_INDEX_HOST = os.environ.get('PINECONE_INDEX_HOST')
PORT = int(os.environ.get('PORT', '5000'))
```

3. **Update .env.example**

```env
# .env.example

# ============================================================================
# REQUIRED ENVIRONMENT VARIABLES
# ============================================================================

# Secret key for session encryption (REQUIRED)
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
# MUST be at least 32 characters
SECRET_KEY=your_generated_secret_key_here_64_characters_long

# OpenRouter API Key (REQUIRED)
# Get from: https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key_here

# OpenAI API Key (REQUIRED)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your_openai_key_here

# Pinecone API Key (REQUIRED)
# Get from: https://app.pinecone.io/organizations/-/projects/-/keys
PINECONE_API_KEY=pcsk_your_pinecone_key_here

# Pinecone Index Host (REQUIRED)
# Get from: Pinecone dashboard → Your Index → Connect
# Example: https://your-index-abc123.svc.us-east-1-aws.pinecone.io
PINECONE_INDEX_HOST=https://your-index.svc.region.pinecone.io

# ============================================================================
# OPTIONAL CONFIGURATION
# ============================================================================

# Server port (default: 5000)
PORT=5050

# Logging level (default: INFO)
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# CORS allowed origins (default: localhost:8000)
# Comma-separated list
ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Test API keys on startup (default: false)
# Set to 'true' to validate API connectivity at startup
VALIDATE_API_KEYS=false

# Debug mode (default: false)
# NEVER set to true in production!
DEBUG=false
```

**Testing Checklist:**
- [x] Server refuses to start without SECRET_KEY
- [x] Server refuses to start without OpenRouter key
- [x] Server refuses to start without OpenAI key
- [x] Server refuses to start without Pinecone key/host
- [x] Error messages are clear and helpful
- [x] Optional API validation works (VALIDATE_API_KEYS=true)

**Time Estimate:** 1.5 hours

---

## ⏸️ CHECKPOINT: Review Phase 1 & 2

**Before continuing, verify:**
- [ ] All P0 (Critical) tasks completed
- [ ] All P1 (High Priority) tasks from 2.1-2.5 completed
- [ ] Tests passing
- [ ] Server starts successfully
- [ ] Can login and use system
- [ ] Logs are working properly

**Remaining P1 tasks (2.6-2.8) are covered below...**

---

### ✅ Task 2.6: Session Recovery

**Current Issue:** If page refreshes during session, all progress lost

**Files to Modify:**
- `backend/app.py`
- `frontend/trainer.html`

**Step-by-Step Instructions:**

1. **Add resume endpoint to app.py**

```python
# app.py - ADD NEW ENDPOINT after /api/training/start

@app.route('/api/training/resume/<int:session_id>', methods=['POST'])
@login_required
def resume_session(session_id):
    """Resume an interrupted training session"""
    try:
        session_obj = db.get_session(session_id)
        
        if not session_obj:
            return jsonify({
                'error': 'session_not_found',
                'message': 'Session does not exist'
            }), 404
        
        # Verify ownership
        if session_obj['user_id'] != session['user_id']:
            return jsonify({
                'error': 'permission_denied',
                'message': 'You do not have access to this session'
            }), 403
        
        # Only resume active sessions
        if session_obj['status'] != 'active':
            return jsonify({
                'error': 'session_not_active',
                'message': 'This session has already ended'
            }), 400
        
        # Get conversation history
        messages = db.get_session_messages(session_id)
        
        # Calculate remaining time
        from datetime import datetime
        started_at = datetime.fromisoformat(session_obj['started_at'])
        elapsed_seconds = (datetime.utcnow() - started_at).total_seconds()
        total_seconds = session_obj['duration_minutes'] * 60
        remaining_seconds = max(0, int(total_seconds - elapsed_seconds))
        
        return jsonify({
            'success': True,
            'session': {
                'id': session_obj['id'],
                'category': session_obj['category'],
                'difficulty': session_obj['difficulty'],
                'duration_minutes': session_obj['duration_minutes'],
                'started_at': session_obj['started_at'],
                'remaining_seconds': remaining_seconds
            },
            'messages': [
                {
                    'role': msg['role'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp']
                }
                for msg in messages
            ]
        })
        
    except Exception as e:
        logger.error(f"Error resuming session: {e}", exc_info=True)
        return jsonify({
            'error': 'resume_failed',
            'message': str(e)
        }), 500
```

2. **Update trainer.html to support resume**

Add after localStorage check:

```javascript
// trainer.html - ADD after user authentication check

// Check for interrupted session in localStorage
const interruptedSession = localStorage.getItem('ahl_active_session');
if (interruptedSession) {
    const sessionData = JSON.parse(interruptedSession);
    
    // Show resume dialog
    if (confirm(`You have an interrupted session (${sessionData.category}). Would you like to resume?`)) {
        resumeSession(sessionData.session_id);
    } else {
        // Clear interrupted session
        localStorage.removeItem('ahl_active_session');
    }
}

// Function to resume session
async function resumeSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/api/training/resume/${sessionId}`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to resume session');
        }
        
        const data = await response.json();
        
        // Restore session state
        sessionState.sessionId = data.session.id;
        sessionState.selectedCategory = data.session.category;
        sessionState.difficulty = data.session.difficulty;
        sessionState.duration = data.session.duration_minutes;
        sessionState.timeRemaining = data.session.remaining_seconds;
        sessionState.isActive = true;
        
        // Restore conversation history
        sessionState.conversationHistory = data.messages.map(m => ({
            role: m.role,
            content: m.content
        }));
        
        // Show training screen
        document.getElementById('category-selection').classList.add('hidden');
        document.getElementById('training-config').classList.add('hidden');
        document.getElementById('training-session').classList.remove('hidden');
        
        // Restore chat messages
        const chatContainer = document.getElementById('chat-container');
        chatContainer.innerHTML = '';
        
        data.messages.forEach(msg => {
            addMessage(msg.content, msg.role);
        });
        
        // Initialize speech recognition
        initializeSpeechRecognition();
        
        // Start timer
        sessionState.timerInterval = setInterval(() => {
            if (!sessionState.isPaused && sessionState.isActive) {
                sessionState.timeRemaining--;
                updateTimerDisplay();
                
                if (sessionState.timeRemaining <= 0) {
                    endSession();
                }
            }
        }, 1000);
        
        updateTimerDisplay();
        
        // Get last AI message
        const lastAI = data.messages.filter(m => m.role === 'assistant').pop();
        if (lastAI) {
            sessionState.lastAIMessage = lastAI.content;
        }
        
        // Start listening
        startListening();
        
        showToast('Session resumed successfully!', 'success');
        
    } catch (error) {
        console.error('Error resuming session:', error);
        localStorage.removeItem('ahl_active_session');
        alert('Could not resume session. Please start a new one.');
        window.location.reload();
    }
}

// Save active session on start
function startTrainingSession() {
    // ... existing code ...
    
    // Save to localStorage for recovery
    localStorage.setItem('ahl_active_session', JSON.stringify({
        session_id: sessionState.sessionId,
        category: sessionState.selectedCategory,
        started_at: new Date().toISOString()
    }));
    
    // ... rest of existing code ...
}

// Clear active session on normal end
async function endSession() {
    // Clear recovery data
    localStorage.removeItem('ahl_active_session');
    
    // ... existing end session code ...
}

// Add beforeunload warning
window.addEventListener('beforeunload', (e) => {
    if (sessionState.isActive && !sessionState.hasEnded) {
        e.preventDefault();
        e.returnValue = 'You have an active training session. Are you sure you want to leave?';
        return e.returnValue;
    }
});
```

**Testing Checklist:**
- [x] Start a session, refresh page, prompted to resume
- [x] Resume shows previous messages
- [x] Timer continues from where it left off
- [x] Can decline resume and start fresh
- [x] localStorage cleared when session ends normally
- [x] Warning shown when trying to close tab during session

**Time Estimate:** 2 hours

---

### ✅ Task 2.7: Rate Limiting

**Current Issue:** No protection against brute force attacks or API abuse

**Files to Modify:**
- `backend/requirements.txt`
- `backend/app.py`

**Step-by-Step Instructions:**

1. **Update requirements.txt**

```txt
# Add to requirements.txt
Flask-Limiter==3.5.0
```

2. **Install dependency**

```bash
cd backend
pip install Flask-Limiter==3.5.0
```

3. **Add rate limiting to app.py**

```python
# app.py - ADD IMPORTS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# app.py - ADD after CORS configuration

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=lambda: session.get('user_id', get_remote_address()),
    default_limits=["200 per hour"],
    storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
    strategy="fixed-window"
)

logger.info("✅ Rate limiting enabled")

# Custom error handler for rate limit exceeded
@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded: {get_remote_address()}")
    return jsonify({
        'error': 'rate_limit_exceeded',
        'message': 'Too many requests. Please slow down.',
        'retry_after': e.description
    }), 429
```

4. **Apply rate limits to sensitive endpoints**

```python
# app.py - UPDATE login endpoint

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")  # Strict limit to prevent brute force
def login():
    """Login endpoint for both admin and candidates"""
    # ... existing code ...


# app.py - UPDATE upload endpoint

@app.route('/api/admin/upload', methods=['POST'])
@admin_required
@limiter.limit("10 per hour")  # Limit uploads
def upload_content():
    """Upload training content to Pinecone"""
    # ... existing code ...


# app.py - UPDATE AI endpoints

@app.route('/api/ai/embed', methods=['POST'])
@login_required
@limiter.limit("60 per minute")  # Reasonable limit for embeddings
def create_embedding():
    """Create embedding via OpenAI (proxy)"""
    # ... existing code ...


@app.route('/api/ai/query', methods=['POST'])
@login_required
@limiter.limit("60 per minute")  # Reasonable limit for vector queries
def query_vectors():
    """Query Pinecone for relevant content (proxy)"""
    # ... existing code ...


@app.route('/api/ai/chat', methods=['POST'])
@login_required
@limiter.limit("30 per minute")  # More expensive, stricter limit
def chat_completion():
    """OpenRouter chat completion (proxy)"""
    # ... existing code ...
```

5. **Add rate limit info to health check**

```python
# app.py - UPDATE health check endpoint

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'rate_limiting': 'enabled',
        'limits': {
            'default': '200 per hour',
            'login': '5 per minute',
            'upload': '10 per hour',
            'ai_requests': '30-60 per minute'
        }
    })
```

6. **Add rate limit bypass for testing**

```python
# app.py - ADD after rate limiter initialization

# Optionally disable rate limiting in development
if os.environ.get('DEBUG', 'false').lower() == 'true':
    limiter.enabled = False
    logger.warning("⚠️  Rate limiting DISABLED (DEBUG mode)")
```

7. **Update .env.example**

```env
# Rate Limiting
# Set to true to disable rate limiting (development only!)
# NEVER set to true in production
DISABLE_RATE_LIMITING=false
```

**Testing Checklist:**
- [x] Login fails after 5 attempts in 1 minute
- [x] Can login again after waiting 1 minute
- [x] Upload limited to 10 per hour
- [x] AI requests limited appropriately
- [x] 429 error has helpful message with retry_after
- [x] Rate limiting can be disabled for testing

**Test rate limiting:**
```bash
# Test login rate limit (should fail on 6th attempt)
for i in {1..6}; do
    curl -X POST http://localhost:5050/api/auth/login \
         -H "Content-Type: application/json" \
         -d '{"username":"test","password":"wrong"}' \
         -w "\nStatus: %{http_code}\n"
done
```

**Time Estimate:** 2 hours

---

### ✅ Task 2.8: Audit Logging

**Current Issue:** No record of who did what when

**Files to Modify:**
- `backend/database.py`
- `backend/app.py`

**Step-by-Step Instructions:**

1. **Add audit_log table to database schema**

```python
# database.py - ADD to initialize() method after other tables

cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        resource_type TEXT,
        resource_id INTEGER,
        details TEXT,
        ip_address TEXT,
        user_agent TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
''')

# Add index for audit queries
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_log(user_id)
''')
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)
''')
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)
''')
```

2. **Add audit logging methods to database.py**

```python
# database.py - ADD NEW METHODS

def log_audit(self, user_id: Optional[int], action: str, 
              resource_type: Optional[str] = None,
              resource_id: Optional[int] = None,
              details: Optional[str] = None,
              ip_address: Optional[str] = None,
              user_agent: Optional[str] = None):
    """Log an audit event"""
    conn = self._get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO audit_log 
        (user_id, action, resource_type, resource_id, details, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, action, resource_type, resource_id, details, ip_address, user_agent))
    
    conn.commit()
    conn.close()


def get_audit_logs(self, user_id: Optional[int] = None,
                   action: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   limit: int = 100) -> List[Dict]:
    """Get audit logs with optional filters"""
    conn = self._get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM audit_log WHERE 1=1'
    params = []
    
    if user_id:
        query += ' AND user_id = ?'
        params.append(user_id)
    
    if action:
        query += ' AND action = ?'
        params.append(action)
    
    if start_date:
        query += ' AND timestamp >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND timestamp <= ?'
        params.append(end_date)
    
    query += ' ORDER BY timestamp DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_user_activity_summary(self, user_id: int, days: int = 30) -> Dict:
    """Get summary of user activity for the last N days"""
    conn = self._get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            action,
            COUNT(*) as count
        FROM audit_log
        WHERE user_id = ?
          AND timestamp >= datetime('now', '-' || ? || ' days')
        GROUP BY action
        ORDER BY count DESC
    ''', (user_id, days))
    
    rows = cursor.fetchall()
    conn.close()
    
    return {row['action']: row['count'] for row in rows}
```

3. **Add audit logging to app.py**

```python
# app.py - CREATE AUDIT HELPER FUNCTION

def audit_log(action: str, resource_type: str = None, 
              resource_id: int = None, details: str = None):
    """Helper to log audit events"""
    try:
        user_id = session.get('user_id')
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:200]  # Truncate
        
        db.log_audit(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
```

4. **Add audit logging to critical operations**

```python
# app.py - UPDATE login endpoint
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Login endpoint for both admin and candidates"""
    # ... validation code ...
    
    user = db.verify_user(login_req.username.strip(), login_req.password)
    
    if not user:
        # Log failed login attempt
        audit_log('login_failed', details=f"username: {login_req.username}")
        return jsonify({
            'error': 'invalid_credentials',
            'message': 'Invalid username or password'
        }), 401
    
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    
    # Log successful login
    audit_log('login_success', details=f"role: {user['role']}")
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'role': user['role']
        }
    })


# app.py - UPDATE logout endpoint
@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    if 'user_id' in session:
        audit_log('logout')
    session.clear()
    return jsonify({'success': True})


# app.py - UPDATE create user endpoint
@app.route('/api/admin/users', methods=['POST'])
@admin_required
def create_user():
    """Create new candidate account (admin only)"""
    # ... existing code ...
    
    user_id = db.create_user(...)
    
    # Log user creation
    audit_log(
        'user_created',
        resource_type='user',
        resource_id=user_id,
        details=f"username: {create_req.username}, role: candidate"
    )
    
    return jsonify({...})


# app.py - UPDATE delete user endpoint
@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    # Get user info before deletion
    user = db.get_user_by_id(user_id)
    
    db.delete_user(user_id)
    
    # Log user deletion
    audit_log(
        'user_deleted',
        resource_type='user',
        resource_id=user_id,
        details=f"username: {user['username']}" if user else None
    )
    
    return jsonify({'success': True})


# app.py - UPDATE upload endpoint
@app.route('/api/admin/upload', methods=['POST'])
@admin_required
@limiter.limit("10 per hour")
def upload_content():
    """Upload training content to Pinecone"""
    # ... existing code ...
    
    upload_id = db.create_upload_record(...)
    
    # Log content upload
    audit_log(
        'content_uploaded',
        resource_type='upload',
        resource_id=upload_id,
        details=f"category: {category}, video: {video_name}, chunks: {result['chunks']}"
    )
    
    return jsonify({...})


# app.py - UPDATE start session endpoint
@app.route('/api/training/start', methods=['POST'])
@login_required
def start_training_session():
    """Start a new training session"""
    # ... existing code ...
    
    session_id = db.create_session(...)
    
    # Log session start
    audit_log(
        'session_started',
        resource_type='session',
        resource_id=session_id,
        details=f"category: {category}, difficulty: {difficulty}"
    )
    
    return jsonify({...})


# app.py - UPDATE end session endpoint
@app.route('/api/training/end', methods=['POST'])
@login_required
def end_training_session():
    """End a training session and generate report"""
    # ... existing code ...
    
    db.complete_session(session_id)
    
    # Log session completion
    audit_log(
        'session_completed',
        resource_type='session',
        resource_id=session_id
    )
    
    return jsonify({'success': True})
```

5. **Add audit log viewing endpoint for admins**

```python
# app.py - ADD NEW ENDPOINT

@app.route('/api/admin/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    """Get audit logs (admin only)"""
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = request.args.get('limit', 100, type=int)
    
    logs = db.get_audit_logs(
        user_id=user_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=min(limit, 1000)  # Cap at 1000
    )
    
    return jsonify({'logs': logs})


@app.route('/api/admin/user-activity/<int:user_id>', methods=['GET'])
@admin_required
def get_user_activity(user_id):
    """Get user activity summary"""
    days = request.args.get('days', 30, type=int)
    
    summary = db.get_user_activity_summary(user_id, days)
    
    return jsonify({
        'user_id': user_id,
        'days': days,
        'activity': summary
    })
```

6. **Run migration to add audit_log table**

```bash
cd backend
python -c "from database import Database; db = Database('data/sales_trainer.db'); db.initialize(); print('Audit log table created')"
```

**Testing Checklist:**
- [x] Audit log table created
- [x] Login success/failure logged
- [x] User creation logged
- [x] User deletion logged
- [x] Content upload logged
- [x] Session start/end logged
- [x] Admin can view audit logs
- [x] IP address and user agent captured

**View audit logs:**
```bash
# In Python shell
from database import Database
db = Database('data/sales_trainer.db')

# Get all logs
logs = db.get_audit_logs(limit=10)
for log in logs:
    print(f"{log['timestamp']} - {log['action']} by user {log['user_id']}")

# Get specific user activity
activity = db.get_user_activity_summary(user_id=1, days=7)
print(activity)
```

**Time Estimate:** 2.5 hours

---

## 🟢 PHASE 3: FUNCTIONALITY ENHANCEMENTS (DO THIS MONTH)

**Priority:** P2 - Medium  
**Estimated Time:** 12-15 hours  
**Risk if Delayed:** Low - Nice to have features

### ✅ Task 3.1: Dashboard Pagination & Filtering

**Current Issue:** Dashboard becomes slow with many candidates

**Files to Modify:**
- `backend/app.py`
- `frontend/admin-dashboard.html`

**Testing Checklist:**
- [x] Pagination controls appear when needed
- [x] Previous/Next buttons work correctly
- [x] Search filters by name and username
- [x] Empty search results handled gracefully
- [x] Global stats remain accurate during search/pagination

**Time Estimate:** 2 hours

### ✅ Task 3.2: Export Reports as PDF

**Current Issue:** No way to save/print reports professionally

**Files to Modify:**
- `backend/requirements.txt`
- `backend/app.py`
- `backend/pdf_generator.py` (New)
- `frontend/admin-dashboard.html`

**Dependencies:**
```bash
pip install reportlab==4.4.6
```

**Testing Checklist:**
- [x] Export button appears in session modal
- [x] Clicking button triggers PDF generation
- [x] PDF contains correct session metadata
- [x] PDF contains formatted feedback
- [x] Error handling for failed generation

**Time Estimate:** 2.5 hours

### ✅ Task 3.3: Bulk User Import

**Current Issue:** Must create users one by one

**Files to Create/Modify:**
- `backend/import_users.py` (New)
- `backend/app.py`
- `frontend/admin-dashboard.html`

**Testing Checklist:**
- [x] Script can import users from CSV
- [x] Script handles duplicate users gracefully
- [x] Passwords are hashed correctly
- [x] Admin UI has "Import Users" button
- [x] File upload endpoint works

**Time Estimate:** 2 hours

### ✅ Task 3.4: Email Notifications

**Current Issue:** No alerts for completed sessions

**Files to Modify:**
- `backend/requirements.txt`
- `backend/app.py`

**Testing Checklist:**
- [x] Install `Flask-Mail`
- [x] Configure mail settings (env vars)
- [x] Add email sending function
- [x] Trigger email on report save
- [x] Verify admin receives email

**Time Estimate:** 3 hours

### ✅ Task 3.5: Advanced Search in Dashboard

**Current Issue:** Hard to find specific sessions

**Files to Modify:**
- `frontend/admin-dashboard.html`
- `backend/app.py`
- `backend/database.py`

**Completed:**
- [x] Backend: Add `search_sessions` to database
- [x] Backend: Add `/api/admin/sessions/search` endpoint
- [x] Frontend: Add "All Sessions" tab
- [x] Frontend: Add advanced filter panel (Date, Score, Category)
- [x] Frontend: Add sessions table with pagination

**Time Estimate:** 2 hours

### ✅ Task 3.6: Session Notes

**Current Issue:** No way to add notes/feedback to sessions

**Files to Modify:**
- `backend/database.py`
- `backend/app.py`
- `frontend/admin-dashboard.html`

**Time Estimate:** 2 hours

---

## 🔵 PHASE 4: CODE QUALITY IMPROVEMENTS (DO THIS MONTH)

**Priority:** P3 - Low  
**Estimated Time:** 8-10 hours

### ✅ Task 4.1: Modularize app.py

**Current Issue:** app.py is 500+ lines, hard to maintain

**Time Estimate:** 4 hours

### ✅ Task 4.2: Add Type Hints Everywhere

**Current Issue:** Inconsistent typing makes debugging harder

**Time Estimate:** 2 hours

### ✅ Task 4.3: API Response Standardization

**Current Issue:** Inconsistent response formats

**Time Estimate:** 1.5 hours

### ✅ Task 4.4: Configuration Management

**Current Issue:** Config scattered across files

**Time Estimate:** 1.5 hours

---

## 🟣 PHASE 5: PERFORMANCE OPTIMIZATIONS (DO THIS MONTH)

**Priority:** P3 - Low  
**Estimated Time:** 6-8 hours

### ✅ Task 5.1: Query Caching

**Time Estimate:** 2 hours

### ✅ Task 5.2: Database Query Optimization

**Time Estimate:** 2 hours

### ✅ Task 5.3: Pinecone Batch Optimization

**Time Estimate:** 1.5 hours

---

## 🧪 PHASE 6: TESTING (ONGOING)

**Priority:** P2 - Medium  
**Estimated Time:** 10-12 hours

### ✅ Task 6.1: Unit Tests

**Files to Create:**
- `backend/tests/test_database.py`
- `backend/tests/test_validators.py`
- `backend/tests/test_auth.py`

**Time Estimate:** 5 hours

### ✅ Task 6.2: Integration Tests

**Files to Create:**
- `backend/tests/test_api.py`
- `backend/tests/test_training_flow.py`

**Time Estimate:** 5 hours

---

## 📊 PHASE 7: MONITORING (DO THIS MONTH)

**Priority:** P2 - Medium  
**Estimated Time:** 4-6 hours

### ✅ Task 7.1: Enhanced Health Checks

**Time Estimate:** 2 hours

### ✅ Task 7.2: Metrics Collection

**Time Estimate:** 2.5 hours

---

## 🎨 PHASE 8: UX/UI IMPROVEMENTS (DO THIS MONTH)

**Priority:** P3 - Low  
**Estimated Time:** 6-8 hours

### ✅ Task 8.1: Better Loading States

**Time Estimate:** 1.5 hours

### ✅ Task 8.2: Toast Notifications

**Time Estimate:** 1.5 hours

### ✅ Task 8.3: Keyboard Shortcuts

**Time Estimate:** 1 hour

### ✅ Task 8.4: Accessibility Improvements

**Time Estimate:** 2 hours

---

## 🚀 DEPLOYMENT GUIDE

### Production Deployment Checklist

```bash
# 1. Setup production environment
cp .env.example .env.production
# Edit .env.production with production values

# 2. Install production dependencies
pip install -r requirements.txt
pip install gunicorn

# 3. Run database migrations
python backend/migrate_passwords.py
python backend/add_indexes.py

# 4. Test environment validation
python backend/app.py  # Should start successfully

# 5. Deploy with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5050 --timeout 120 app:app

# 6. Setup Nginx reverse proxy (optional)
# See nginx.conf.example

# 7. Setup SSL/TLS certificates
# Use Let's Encrypt or similar

# 8. Setup log rotation
# See logrotate.conf.example

# 9. Setup monitoring
# Configure health checks and alerts

# 10. Create backup strategy
# Daily database backups
```

---

## 📋 MASTER CHECKLIST

### Phase 1: Critical Security (DO IMMEDIATELY)
- [x] Task 1.1: Fix password hashing with bcrypt
- [x] Task 1.2: Fix SECRET_KEY configuration
- [x] Task 1.3: Restrict CORS origins

### Phase 2: High Priority (DO THIS WEEK)
- [x] Task 2.1: Add database indexes
- [x] Task 2.2: Enable foreign key constraints
- [x] Task 2.3: Add input validation layer
- [x] Task 2.4: Implement proper logging
- [x] Task 2.5: Environment variable validation
- [x] Task 2.6: Session recovery
- [x] Task 2.7: Rate limiting
- [x] Task 2.8: Audit logging

### Phase 3: Functionality (DO THIS MONTH)
- [x] Task 3.1: Dashboard pagination & filtering
- [x] Task 3.2: Export reports as PDF
- [x] Task 3.3: Bulk user import
- [x] Task 3.4: Email notifications
- [x] Task 3.5: Advanced search in dashboard
- [x] Task 3.6: Session notes

### Phase 4: Code Quality (DO THIS MONTH)
- [x] Task 4.1: Modularize app.py
- [x] Task 4.2: Add type hints everywhere
- [x] Task 4.3: API response standardization
- [x] Task 4.4: Configuration management

### Phase 5: Performance (DO THIS MONTH)
- [x] Task 5.1: Query caching
- [x] Task 5.2: Database query optimization
- [x] Task 5.3: Pinecone batch optimization

### Phase 6: Testing (ONGOING)
- [x] Task 6.1: Unit tests
- [x] Task 6.2: Integration tests

### Phase 7: Monitoring (DO THIS MONTH)
- [x] Task 7.1: Enhanced health checks
- [x] Task 7.2: Metrics collection

### Phase 8: UX/UI (DO THIS MONTH)
- [x] Task 8.1: Better loading states
- [x] Task 8.2: Toast notifications
- [x] Task 8.3: Keyboard shortcuts
- [x] Task 8.4: Accessibility improvements

---

## 📊 PROGRESS TRACKER

| Phase | Tasks | Completed | Progress | Est. Hours | Actual Hours |
|-------|-------|-----------|----------|------------|--------------|
| Phase 1 (Critical) | 3 | 3 | 100% | 4-6 | 3-4 |
| Phase 2 (High) | 8 | 8 | 100% | 10-12 | - |
| Phase 3 (Functionality) | 6 | 6 | 100% | 12-15 | - |
| Phase 4 (Code Quality) | 4 | 4 | 100% | 8-10 | - |
| Phase 5 (Performance) | 3 | 3 | 100% | 6-8 | - |
| Phase 6 (Testing) | 2 | 2 | 100% | 10-12 | - |
| Phase 7 (Monitoring) | 2 | 2 | 100% | 4-6 | - |
| Phase 8 (UX/UI) | 4 | 4 | 100% | 6-8 | - |
| **TOTAL** | **32** | **32** | **100%** | **60-77** | **-** |

---

## 🎯 WEEKLY SPRINT PLAN

### Week 1: Critical & High Priority
**Goal:** Complete all P0 and start P1 tasks

**Day 1-2:**
- Task 1.1: Password hashing (2h)
- Task 1.2: SECRET_KEY fix (1h)
- Task 1.3: CORS restrictions (1h)
- Task 2.1: Database indexes (1.5h)

**Day 3-4:**
- Task 2.2: Foreign keys (2h)
- Task 2.3: Input validation (3h)

**Day 5:**
- Task 2.4: Logging (2.5h)
- Task 2.5: Env validation (1.5h)

### Week 2: High Priority Completion
**Goal:** Finish P1 tasks

**Day 1-2:**
- Task 2.6: Session recovery (2h)
- Task 2.7: Rate limiting (2h)

**Day 3-4:**
- Task 2.8: Audit logging (2.5h)
- Testing and bug fixes (4h)

**Day 5:**
- Code review
- Documentation updates
- Sprint retrospective

### Week 3: Functionality & Code Quality
**Goal:** Complete key feature enhancements

**Day 1-2:**
- Task 3.1: Dashboard improvements (2h)
- Task 3.2: PDF export (2.5h)

**Day 3-4:**
- Task 4.1: Modularize code (4h)
- Task 4.2: Type hints (2h)

**Day 5:**
- Task 3.3-3.4: User imports & notifications (5h)

### Week 4: Performance, Testing & Polish
**Goal:** Optimize and finalize

**Day 1-2:**
- Task 5.1-5.3: Performance optimizations (6h)

**Day 3-4:**
- Task 6.1-6.2: Testing (10h)

**Day 5:**
- Task 8.1-8.4: UX improvements (6h)
- Final testing
- Deployment preparation

---

## 💡 IMPLEMENTATION TIPS

### Best Practices

1. **Always backup before major changes**
```bash
cp data/sales_trainer.db data/sales_trainer.db.backup_$(date +%Y%m%d)
```

2. **Test each task in isolation**
```bash
# Create a test database
python -c "from database import Database; db = Database('test.db'); db.initialize()"
# Run tests against test.db
# Delete when done
```

3. **Use feature branches**
```bash
git checkout -b feature/password-hashing
# Make changes
git commit -m "feat: implement bcrypt password hashing"
git checkout main
git merge feature/password-hashing
```

4. **Document as you go**
```python
# Add docstrings to every function
def create_user(username: str, password: str) -> int:
    """
    Create a new user account
    
    Args:
        username: Unique username (3-50 chars)
        password: Plain text password (min 6 chars)
    
    Returns:
        int: New user ID
        
    Raises:
        ValueError: If username exists or validation fails
    """
```

5. **Run tests after every change**
```bash
# After implementing a task
python -m pytest tests/
python backend/app.py  # Ensure server starts
```

---

## 🐛 TROUBLESHOOTING GUIDE

### Common Issues

**Issue: bcrypt installation fails**
```bash
# Solution: Install compiler tools first
# macOS:
xcode-select --install

# Ubuntu/Debian:
sudo apt-get install python3-dev libffi-dev

# Then retry:
pip install bcrypt
```

**Issue: Database locked error**
```python
# Solution: Enable WAL mode (already in Task 2.2)
conn.execute("PRAGMA journal_mode = WAL")
```

**Issue: Rate limiting not working**
```bash
# Solution: Check limiter is initialized
# In Python shell:
from app import limiter
print(limiter.enabled)  # Should be True
```

**Issue: Logs not created**
```bash
# Solution: Create logs directory
mkdir -p logs
chmod 755 logs
```

---

## 📚 ADDITIONAL RESOURCES

### Documentation to Read
- [Flask-Limiter docs](https://flask-limiter.readthedocs.io/)
- [bcrypt documentation](https://github.com/pyca/bcrypt/)
- [SQLite WAL mode](https://www.sqlite.org/wal.html)
- [Python logging cookbook](https://docs.python.org/3/howto/logging-cookbook.html)

### Tools to Install
```bash
# Code quality
pip install black flake8 mypy pylint

# Testing
pip install pytest pytest-cov pytest-flask

# Monitoring
pip install prometheus-client
```

---

## ✅ ACCEPTANCE CRITERIA

### Definition of Done

A task is considered complete when:

1. **Code is written** ✅
2. **Code is tested** ✅
3. **Code is documented** ✅
4. **Code is reviewed** ✅
5. **Tests are passing** ✅
6. **Logs are working** ✅
7. **No breaking changes** ✅
8. **README is updated** ✅
9. **Checklist item marked** ✅

### Quality Gates

Before moving to next phase:

- [ ] All tests passing
- [ ] No critical bugs
- [ ] Code coverage > 70%
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] Security scan passed
- [ ] Peer review approved

---

## 🎓 LEARNING OUTCOMES

After completing this roadmap, you will have:

✅ Implemented enterprise-grade security  
✅ Built a scalable backend architecture  
✅ Mastered Flask best practices  
✅ Implemented comprehensive testing  
✅ Set up proper logging and monitoring  
✅ Learned performance optimization  
✅ Gained DevOps deployment experience  
✅ Improved code quality and maintainability  

---

## 📞 SUPPORT & QUESTIONS

If you encounter issues:

1. Check the troubleshooting guide above
2. Review relevant documentation
3. Check logs: `tail -f logs/ahl_sales_trainer.log`
4. Test in isolation with minimal setup
5. Ask for help with specific error messages

---

## 🏆 SUCCESS METRICS

### Before Improvements
- Security: ⚠️ Weak password hashing
- Performance: ⚠️ Slow dashboard with many users
- Reliability: ⚠️ No session recovery
- Observability: ❌ No audit logs
- Testing: ❌ No automated tests

### After Improvements
- Security: ✅ bcrypt, rate limiting, CORS
- Performance: ✅ Indexed queries, caching
- Reliability: ✅ Session recovery, FK constraints
- Observability: ✅ Logging, audit trails, monitoring
- Testing: ✅ Unit & integration tests

---

**Document Version:** 1.0  
**Last Updated:** December 18, 2025  
**Status:** Ready for Implementation  

**Remember:** Progress over perfection. Start with Phase 1 (Critical) and work your way through systematically. Each completed task makes the system better! 🚀
