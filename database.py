"""
Database layer for AHL Sales Trainer
Handles all SQLite operations
"""

import sqlite3
import hashlib
import bcrypt
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
from config_logging import get_logger

logger = get_logger('database')


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        # CRITICAL: Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        # Enable Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn
    
    def initialize(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Upload records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                video_name TEXT NOT NULL,
                filename TEXT NOT NULL,
                chunks_created INTEGER NOT NULL,
                uploaded_by INTEGER NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Training sessions table
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
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Conversation messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                context_source TEXT,
                evaluation_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        ''')

        # Ensure new column exists for existing databases
        try:
            cursor.execute("PRAGMA table_info(messages)")
            cols = [r[1] for r in cursor.fetchall()]
            if 'evaluation_data' not in cols:
                cursor.execute('ALTER TABLE messages ADD COLUMN evaluation_data TEXT')
        except Exception as e:
            logger.error(f"Failed ensuring messages.evaluation_data column: {e}")
        
        # Reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER UNIQUE NOT NULL,
                report_html TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        ''')

        # Question bank (pre-generated questions per session)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                expected_answer TEXT,
                key_points_json TEXT,
                source TEXT,
                difficulty TEXT,
                is_objection INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        ''')

        # Answer evaluations (per answer scoring)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS answer_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                user_answer TEXT NOT NULL,
                accuracy REAL,
                completeness REAL,
                clarity REAL,
                tone REAL,
                technique REAL,
                closing REAL,
                overall_score REAL,
                feedback TEXT,
                evidence TEXT,
                objection_score REAL,
                technique_adherence INTEGER,
                what_correct TEXT,
                what_missed TEXT,
                what_wrong TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES question_bank(id) ON DELETE CASCADE
            )
        ''')

        # Ensure new columns exist for existing databases
        try:
            cursor.execute("PRAGMA table_info(answer_evaluations)")
            cols = [r[1] for r in cursor.fetchall()]
            for col in ('what_correct', 'what_missed', 'what_wrong'):
                if col not in cols:
                    cursor.execute(f'ALTER TABLE answer_evaluations ADD COLUMN {col} TEXT')
        except Exception as e:
            logger.error(f"Failed ensuring answer_evaluations detail columns: {e}")

        # Audit log table
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
        
        # Create indexes for better query performance
        logger.info("Creating indexes...")
        
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
            'CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_log(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)',
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Database initialized successfully")
    
    # ========================================================================
    # USER OPERATIONS
    # ========================================================================
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against bcrypt hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    def create_user(self, username: str, password: str, name: str, role: str = 'candidate') -> int:
        """Create a new user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        password_hash = self._hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, name, role)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, name, role))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return user_id
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """Verify user credentials"""
        user = self.get_user_by_username(username)
        
        if not user:
            return None
        
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
    
    def list_users(self, role: Optional[str] = None, page: int = 1, limit: int = 1000, search: Optional[str] = None) -> Tuple[List[Dict], int]:
        """List users with pagination and filtering"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        params = []
        count_params = []
        
        query = 'SELECT * FROM users WHERE 1=1'
        count_query = 'SELECT COUNT(*) FROM users WHERE 1=1'
        
        if role:
            query += ' AND role = ?'
            count_query += ' AND role = ?'
            params.append(role)
            count_params.append(role)
            
        if search:
            search_term = f"%{search}%"
            query += ' AND (username LIKE ? OR name LIKE ?)'
            count_query += ' AND (username LIKE ? OR name LIKE ?)'
            params.extend([search_term, search_term])
            count_params.extend([search_term, search_term])
            
        # Get total count first
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated results
        query += ' ORDER BY role, name LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows], total_count
    
    def delete_user(self, user_id: int):
        """Delete a user and all related data"""
        import time, sqlite3
        attempts = 0
        while True:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # 1. Get user's sessions to manually delete their data
                cursor.execute('SELECT id FROM sessions WHERE user_id = ?', (user_id,))
                session_ids = [row['id'] for row in cursor.fetchall()]
                
                # 2. Delete all data for each session
                for sid in session_ids:
                    cursor.execute('DELETE FROM answer_evaluations WHERE session_id = ?', (sid,))
                    cursor.execute('DELETE FROM question_bank WHERE session_id = ?', (sid,))
                    cursor.execute('DELETE FROM messages WHERE session_id = ?', (sid,))
                    cursor.execute('DELETE FROM reports WHERE session_id = ?', (sid,))
                    cursor.execute('DELETE FROM sessions WHERE id = ?', (sid,))
                
                # 3. Delete user's uploads
                cursor.execute('DELETE FROM uploads WHERE uploaded_by = ?', (user_id,))
                
                # 4. Anonymize audit logs (in case ON DELETE SET NULL is missing)
                cursor.execute('UPDATE audit_log SET user_id = NULL WHERE user_id = ?', (user_id,))
                
                # 5. Delete user
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                
                conn.commit()
                return
            except sqlite3.OperationalError as e:
                # Retry on database locked
                if 'locked' in str(e).lower() and attempts < 5:
                    attempts += 1
                    time.sleep(0.2 * attempts)
                else:
                    raise
            finally:
                conn.close()
    
    # ========================================================================
    # UPLOAD OPERATIONS
    # ========================================================================
    
    def create_upload_record(self, category: str, video_name: str, filename: str,
                            chunks_created: int, uploaded_by: int) -> int:
        """Create upload record"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO uploads (category, video_name, filename, chunks_created, uploaded_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (category, video_name, filename, chunks_created, uploaded_by))
        
        upload_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return upload_id
    
    def get_uploads_by_category(self, category: str) -> List[Dict]:
        """Get all uploads for a category"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM uploads WHERE category = ? ORDER BY uploaded_at DESC
        ''', (category,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_upload_stats_by_category(self) -> Dict:
        """Get upload statistics grouped by category"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                category,
                COUNT(DISTINCT video_name) as video_count,
                SUM(chunks_created) as total_chunks
            FROM uploads
            GROUP BY category
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        stats = {}
        for row in rows:
            stats[row['category']] = {
                'video_count': row['video_count'],
                'total_chunks': row['total_chunks']
            }
        
        return stats
    
    # ========================================================================
    # SESSION OPERATIONS
    # ========================================================================
    
    def create_session(self, user_id: int, category: str, difficulty: str,
                      duration_minutes: int) -> int:
        """Create a new training session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sessions (user_id, category, difficulty, duration_minutes)
            VALUES (?, ?, ?, ?)
        ''', (user_id, category, difficulty, duration_minutes))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
    
    def get_session(self, session_id: int) -> Optional[Dict]:
        """Get session by ID with user details"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, u.username, u.name 
            FROM sessions s 
            JOIN users u ON s.user_id = u.id 
            WHERE s.id = ?
        ''', (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def complete_session(self, session_id: int, overall_score: Optional[float] = None):
        """Mark session as completed"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if overall_score is not None:
            cursor.execute('''
                UPDATE sessions
                SET status = 'completed', ended_at = CURRENT_TIMESTAMP, overall_score = ?
                WHERE id = ?
            ''', (overall_score, session_id))
        else:
            cursor.execute('''
                UPDATE sessions
                SET status = 'completed', ended_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (session_id,))
        
        conn.commit()
        conn.close()
    
    def get_user_sessions(self, user_id: int) -> List[Dict]:
        """Get all sessions for a user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sessions
            WHERE user_id = ?
            ORDER BY started_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def search_sessions(self, start_date: Optional[str] = None, end_date: Optional[str] = None,
                       min_score: Optional[float] = None, max_score: Optional[float] = None,
                       category: Optional[str] = None, search_term: Optional[str] = None,
                       page: int = 1, limit: int = 20) -> Tuple[List[Dict], int]:
        """Search sessions with multiple filters"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        params = []
        count_params = []
        
        # Base query joining sessions and users
        query = '''
            SELECT s.*, u.username, u.name as candidate_name 
            FROM sessions s 
            JOIN users u ON s.user_id = u.id 
            WHERE 1=1
        '''
        count_query = '''
            SELECT COUNT(*) 
            FROM sessions s 
            JOIN users u ON s.user_id = u.id 
            WHERE 1=1
        '''
        
        if start_date:
            query += ' AND s.started_at >= ?'
            count_query += ' AND s.started_at >= ?'
            params.append(start_date)
            count_params.append(start_date)
            
        if end_date:
            query += ' AND s.started_at <= ?'
            count_query += ' AND s.started_at <= ?'
            params.append(end_date)
            count_params.append(end_date)
            
        if min_score is not None:
            query += ' AND s.overall_score >= ?'
            count_query += ' AND s.overall_score >= ?'
            params.append(min_score)
            count_params.append(min_score)
            
        if max_score is not None:
            query += ' AND s.overall_score <= ?'
            count_query += ' AND s.overall_score <= ?'
            params.append(max_score)
            count_params.append(max_score)
            
        if category:
            query += ' AND s.category = ?'
            count_query += ' AND s.category = ?'
            params.append(category)
            count_params.append(category)
            
        if search_term:
            term = f"%{search_term}%"
            query += ' AND (u.username LIKE ? OR u.name LIKE ?)'
            count_query += ' AND (u.username LIKE ? OR u.name LIKE ?)'
            params.extend([term, term])
            count_params.extend([term, term])
            
        # Get total count
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated results
        query += ' ORDER BY s.started_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows], total_count
    
    def delete_session(self, session_id: int):
        """Delete a session and all related data"""
        import time, sqlite3
        attempts = 0
        while True:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # Manually delete related records to avoid foreign key constraints issues
                # (In case ON DELETE CASCADE is missing in older DB schemas)
                cursor.execute('DELETE FROM answer_evaluations WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM question_bank WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
                cursor.execute('DELETE FROM reports WHERE session_id = ?', (session_id,))
                
                # Finally delete the session
                cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
                
                conn.commit()
                return
            except sqlite3.OperationalError as e:
                # Retry on database locked
                if 'locked' in str(e).lower() and attempts < 5:
                    attempts += 1
                    time.sleep(0.2 * attempts)
                else:
                    raise
            finally:
                conn.close()

    # ========================================================================
    # MESSAGE OPERATIONS
    # ========================================================================
    
    def add_message(self, session_id: int, role: str, content: str, context_source: str, evaluation_data: Optional[Dict] = None):
        """Add a message to a session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (session_id, role, content, context_source, evaluation_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, role, content, context_source, json.dumps(evaluation_data) if evaluation_data is not None else None))
        
        conn.commit()
        conn.close()
    
    def get_session_messages(self, session_id: int) -> List[Dict]:
        """Get all messages for a session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        ''', (session_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ========================================================================
    # REPORT OPERATIONS
    # ========================================================================
    
    def save_report(self, session_id: int, report_html: str, overall_score: Optional[float]):
        """Save report for a session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Save report
        cursor.execute('''
            INSERT OR REPLACE INTO reports (session_id, report_html)
            VALUES (?, ?)
        ''', (session_id, report_html))
        
        # Update session score
        if overall_score is not None:
            cursor.execute('''
                UPDATE sessions SET overall_score = ? WHERE id = ?
            ''', (overall_score, session_id))
        
        conn.commit()
        conn.close()
    
    def get_report(self, session_id: int) -> Optional[Dict]:
        """Get report for a session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM reports WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None

    # ========================================================================
    # QUESTION/EVALUATION OPERATIONS
    # ========================================================================

    def save_prepared_questions(self, session_id: int, questions: List[Dict]) -> List[int]:
        """Save a list of prepared questions for a session. Returns inserted IDs."""
        conn = self._get_connection()
        cursor = conn.cursor()
        inserted_ids: List[int] = []
        for i, q in enumerate(questions, start=1):
            key_points_json = json.dumps(q.get('key_points', []))
            cursor.execute('''
                INSERT INTO question_bank 
                (session_id, position, question_text, expected_answer, key_points_json, source, difficulty, is_objection)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                i,
                q.get('question') or q.get('question_text') or '',
                q.get('expected_answer'),
                key_points_json,
                q.get('source'),
                q.get('difficulty'),
                1 if q.get('is_objection') else 0
            ))
            inserted_ids.append(cursor.lastrowid)
        conn.commit()
        conn.close()
        return inserted_ids

    def get_session_questions(self, session_id: int) -> List[Dict]:
        """Get all prepared questions for a session ordered by position"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM question_bank
            WHERE session_id = ?
            ORDER BY position ASC
        ''', (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_next_unanswered_question(self, session_id: int) -> Optional[Dict]:
        """Get the next question that has not yet been evaluated"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT qb.*
            FROM question_bank qb
            LEFT JOIN answer_evaluations ae ON ae.question_id = qb.id
            WHERE qb.session_id = ? AND ae.id IS NULL
            ORDER BY qb.position ASC
            LIMIT 1
        ''', (session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def save_answer_evaluation(self, session_id: int, question_id: int, evaluation: Dict):
        """Save evaluation results for an answer"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO answer_evaluations
            (session_id, question_id, user_answer, accuracy, completeness, clarity, tone, technique, closing, overall_score, feedback, evidence, objection_score, technique_adherence, what_correct, what_missed, what_wrong)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            question_id,
            evaluation.get('user_answer', ''),
            evaluation.get('accuracy'),
            evaluation.get('completeness'),
            evaluation.get('clarity'),
            evaluation.get('tone'),
            evaluation.get('technique'),
            evaluation.get('closing'),
            evaluation.get('overall_score'),
            evaluation.get('feedback'),
            evaluation.get('evidence_from_training') or evaluation.get('evidence'),
            evaluation.get('objection_score'),
            1 if evaluation.get('prescribed_language_used') or evaluation.get('technique_adherence') else 0,
            evaluation.get('what_correct'),
            evaluation.get('what_missed'),
            evaluation.get('what_wrong') if isinstance(evaluation.get('what_wrong'), str) else json.dumps(evaluation.get('what_wrong')) if evaluation.get('what_wrong') is not None else None
        ))
        conn.commit()
        conn.close()

    def update_session_notes(self, session_id: int, notes: str):
        """Update notes for a session"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE sessions SET notes = ? WHERE id = ?', (notes, session_id))
        
        conn.commit()
        conn.close()

    # ========================================================================
    # AUDIT LOG OPERATIONS
    # ========================================================================

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

    def get_dashboard_stats(self) -> Dict:
        """Get overall dashboard statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'candidate'")
        total_candidates = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(overall_score) FROM sessions WHERE overall_score IS NOT NULL")
        avg_score = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_candidates': total_candidates,
            'total_sessions': total_sessions,
            'avg_score': round(avg_score, 1) if avg_score else 0.0
        }

    def get_user_stats(self, user_id: int) -> Dict:
        """Get statistics for a specific user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                AVG(overall_score) as avg_score
            FROM sessions 
            WHERE user_id = ?
        ''', (user_id,))
        basic = cursor.fetchone()
        
        # Difficulty breakdown
        cursor.execute('''
            SELECT difficulty, COUNT(*) as count
            FROM sessions
            WHERE user_id = ?
            GROUP BY difficulty
        ''', (user_id,))
        diff_rows = cursor.fetchall()
        
        conn.close()
        
        difficulty_stats = {row['difficulty']: row['count'] for row in diff_rows}
        
        return {
            'total_sessions': basic['total'],
            'avg_score': round(basic['avg_score'], 1) if basic['avg_score'] else 0.0,
            'sessions_by_difficulty': difficulty_stats
        }

    def get_global_stats(self) -> Dict:
        """Get global statistics for dashboard"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'candidate'")
        total_candidates = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE status = 'completed'")
        completed_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(overall_score) FROM sessions WHERE overall_score IS NOT NULL")
        avg_score = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE started_at >= datetime('now','start of day')")
        active_today = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_candidates': total_candidates,
            'completed_sessions': completed_sessions,
            'average_score': round(avg_score, 1) if avg_score else 0.0,
            'active_today': active_today
        }
