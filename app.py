"""
AHL Sales Trainer - Main Backend Server
Handles authentication, data upload, training sessions, and reporting
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from typing import Dict, List, Optional

from flask import Flask, request, jsonify, session, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail, Message
import requests
from pinecone import Pinecone
from dotenv import load_dotenv

from database import Database
from config_logging import setup_logging, get_logger
from pdf_generator import generate_session_pdf
from report_builder import build_enhanced_report_html, build_candidate_report_html
from import_users import import_users_from_csv
import tempfile

# Setup logging
logger = setup_logging()

from config import init_mail, init_cors, init_limiter
# Initialize Flask
app = Flask(__name__)

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
    },
    'MAIL_USERNAME': {
        'description': 'Email address for sending notifications',
        'example': 'notifications@example.com',
        'optional': True
    },
    'MAIL_PASSWORD': {
        'description': 'Email password or app password',
        'example': 'xxxx-xxxx-xxxx-xxxx',
        'optional': True
    },
    'ADMIN_EMAIL': {
        'description': 'Email to receive notifications',
        'example': 'admin@example.com',
        'optional': True
    }
}
    
    missing_vars = []
    invalid_vars = []
    
    logger.info("Validating environment variables...")
    
    for var_name, config in required_vars.items():
        value = os.environ.get(var_name)
        
        if not value:
            if config.get('optional'):
                continue
                
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
            headers={'Authorization': f'Bearer {os.environ.get("OPENAI_API_KEY")}'},
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
        pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
        index = pc.Index(host=os.environ.get("PINECONE_INDEX_HOST"))
        stats = index.describe_index_stats()
        logger.info(f"✓ Pinecone connection successful (dimensions: {stats.get('dimension', 'unknown')})")
    except Exception as e:
        logger.error(f"✗ Pinecone connection failed: {e}")
        tests_passed = False
    
    if not tests_passed:
        raise RuntimeError("API connectivity tests failed")

from validators import (
    ValidationError,
    CreateUserRequest,
    LoginRequest,
    UploadRequest,
    StartSessionRequest,
    ResumeSessionRequest,
    validate_session_id,
    validate_user_id
)

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Validate environment before proceeding
validate_environment()

# SECRET_KEY must be provided via environment
SECRET_KEY = os.environ.get('SECRET_KEY')
app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False

init_cors(app)

limiter = init_limiter(app)
mail = init_mail(app)

CACHE = {}
CACHE_ENABLED = os.environ.get('DISABLE_CACHE', 'false').lower() != 'true'

def cache_get(key: str):
    if not CACHE_ENABLED or app.config.get('TESTING'):
        return None
    entry = CACHE.get(key)
    if not entry:
        return None
    expires, value = entry
    if expires < datetime.now(timezone.utc):
        del CACHE[key]
        return None
    return value

def cache_set(key: str, value, ttl_seconds: int):
    if not CACHE_ENABLED or app.config.get('TESTING'):
        return
    CACHE[key] = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds), value)
@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded: {get_remote_address()}")
    return jsonify({
        'error': 'rate_limit_exceeded',
        'message': 'Too many requests. Please slow down.',
        'retry_after': str(e.description)
    }), 429

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', '')
PINECONE_INDEX_HOST = os.environ.get('PINECONE_INDEX_HOST', '')
PORT = int(os.environ.get('PORT', '5000'))

# Initialize database - support Render persistent disk
DB_PATH = os.environ.get('DATABASE_PATH', 'data/sales_trainer.db')
db = Database(DB_PATH)

FRONTEND_DIR = os.path.abspath(os.path.dirname(__file__))

# Categories configuration
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

# ============================================================================
# AUDIT LOGGING HELPER
# ============================================================================

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

def send_email_notification(subject, recipients, body_html):
    """Send email notification"""
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        logger.warning("Email not configured, skipping notification")
        return False
        
    try:
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=recipients)
        msg.html = body_html
        mail.send(msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

@app.route('/', methods=['GET'])
def root_page():
    return send_file(os.path.join(FRONTEND_DIR, 'login.html'))

@app.route('/login.html', methods=['GET'])
def login_page():
    return send_file(os.path.join(FRONTEND_DIR, 'login.html'))

@app.route('/admin-dashboard.html', methods=['GET'])
def admin_dashboard_page():
    return send_file(os.path.join(FRONTEND_DIR, 'admin-dashboard.html'))

@app.route('/admin-upload.html', methods=['GET'])
def admin_upload_page():
    return send_file(os.path.join(FRONTEND_DIR, 'admin-upload.html'))

@app.route('/trainer.html', methods=['GET'])
def trainer_page():
    return send_file(os.path.join(FRONTEND_DIR, 'trainer.html'))

# ============================================================================
# AUTHENTICATION
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'authentication_required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'authentication_required'}), 401
        user = db.get_user_by_id(session['user_id'])
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'admin_required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
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
        
    except ValueError as e:
        errs = e.args[0] if e.args else None
        if isinstance(errs, list):
            return jsonify({
                'error': 'validation_error',
                'errors': [{'field': getattr(err, 'field', 'unknown'), 'message': getattr(err, 'message', str(err))} for err in errs]
            }), 400
        return jsonify({'error': 'validation_error', 'message': str(e)}), 400

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    if 'user_id' in session:
        audit_log('logout')
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current logged-in user info"""
    user = db.get_user_by_id(session['user_id'])
    if not user:
        return jsonify({'error': 'user_not_found'}), 404
    
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'name': user['name'],
        'role': user['role']
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    db_ok = True
    sqlite_version = None
    try:
        conn = db._get_connection()
        cur = conn.cursor()
        cur.execute('SELECT sqlite_version()')
        sqlite_version = cur.fetchone()[0]
        cur.execute('SELECT 1')
        conn.close()
    except Exception:
        db_ok = False
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'db': {
            'ok': db_ok,
            'sqlite_version': sqlite_version
        },
        'rate_limiting': getattr(limiter, 'enabled', True),
        'mail_configured': bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'))
    })

@app.route('/api/admin/dashboard/stats', methods=['GET'])
@admin_required
def get_dashboard_stats():
    """Get dashboard statistics"""
    cache_key = 'dashboard_stats'
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    stats = db.get_dashboard_stats()
    cache_set(cache_key, stats, ttl_seconds=30)
    return jsonify(stats)

# ============================================================================
# ADMIN - USER MANAGEMENT
# ============================================================================

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def list_users():
    """List all users (admin only)"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    role = request.args.get('role')
    search = request.args.get('search')
    
    users, total_count = db.list_users(
        role=role,
        page=page,
        limit=limit,
        search=search
    )
    
    return jsonify({
        'users': users,
        'pagination': {
            'total': total_count,
            'page': page,
            'limit': limit,
            'pages': (total_count + limit - 1) // limit
        }
    })

@app.route('/api/admin/users/import', methods=['POST'])
@admin_required
def import_users():
    """Bulk import users from CSV"""
    if 'file' not in request.files:
        return jsonify({'error': 'no_file'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'no_filename'}), 400
        
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'invalid_format', 'message': 'File must be a CSV'}), 400
        
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            file.save(temp.name)
            temp_path = temp.name
            
        # Process
        results = import_users_from_csv(temp_path, db_path=db.db_path)
        
        # Cleanup
        os.unlink(temp_path)
        
        return jsonify({
            'success': True,
            'summary': results
        })
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return jsonify({'error': 'import_failed', 'message': str(e)}), 500

@app.route('/api/admin/users', methods=['POST'])
@admin_required
@limiter.limit("10 per hour")
def create_user():
    """Create new candidate account (admin only)"""
    try:
        data = request.json
        
        # Validate input
        create_req = CreateUserRequest(
            username=data.get('username', ''),
            password=data.get('password', ''),
            name=data.get('name', ''),
            role=data.get('role', 'candidate')
        )
        create_req.validate()
        
        # Check if username exists
        existing = db.get_user_by_username(create_req.username)
        if existing:
            return jsonify({'error': 'username_exists', 'message': 'Username already exists'}), 400
        
        user_id = db.create_user(
            create_req.username, 
            create_req.password, 
            create_req.name, 
            role=create_req.role
        )
        
        # Log user creation
        audit_log(
            'user_created',
            resource_type='user',
            resource_id=user_id,
            details=f"username: {create_req.username}, role: {create_req.role}"
        )
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'username': create_req.username
        })
        
    except ValueError as e:
        return jsonify({
            'error': 'validation_error',
            'message': str(e)
        }), 400

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    try:
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
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({'error': 'deletion_failed', 'message': str(e)}), 500

@app.route('/api/admin/sessions/<int:session_id>', methods=['DELETE'])
@admin_required
def delete_session(session_id):
    """Delete a session (admin only)"""
    try:
        db.delete_session(session_id)
        
        audit_log(
            'session_deleted',
            resource_type='session',
            resource_id=session_id
        )
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        return jsonify({'error': 'deletion_failed', 'message': str(e)}), 500

@app.route('/api/admin/sessions/bulk-delete', methods=['POST'])
@admin_required
def delete_sessions_bulk():
    """Bulk delete sessions (admin only)"""
    try:
        data = request.json
        session_ids = data.get('session_ids', [])
        
        if not session_ids:
            return jsonify({'error': 'no_ids_provided'}), 400
            
        count = 0
        for session_id in session_ids:
            db.delete_session(session_id)
            count += 1
            
        audit_log(
            'sessions_bulk_deleted',
            details=f"deleted {count} sessions"
        )
        
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Error bulk deleting sessions: {e}")
        return jsonify({'error': 'deletion_failed', 'message': str(e)}), 500

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

@app.route('/api/admin/sessions/search', methods=['GET'])
@admin_required
def search_sessions():
    """Search sessions with filters"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    category = request.args.get('category')
    search_term = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    sessions, total_count = db.search_sessions(
        start_date=start_date,
        end_date=end_date,
        min_score=min_score,
        max_score=max_score,
        category=category,
        search_term=search_term,
        page=page,
        limit=limit
    )
    
    total_pages = (total_count + limit - 1) // limit
    
    return jsonify({
        'sessions': sessions,
        'pagination': {
            'total': total_count,
            'page': page,
            'pages': total_pages,
            'limit': limit
        }
    })

# ============================================================================
# ADMIN - DATA UPLOAD & MANAGEMENT
# ============================================================================

@app.route('/api/admin/categories', methods=['GET'])
@login_required
def get_categories():
    """Get all available categories with upload status"""
    stats = db.get_upload_stats_by_category()
    
    categories_data = []
    for cat in CATEGORIES:
        cat_stats = stats.get(cat, {'video_count': 0, 'total_chunks': 0})
        categories_data.append({
            'name': cat,
            'video_count': cat_stats['video_count'],
            'chunks': cat_stats['total_chunks']
        })
    
    return jsonify({'categories': categories_data})

@app.route('/api/admin/sync-content', methods=['POST'])
@admin_required
def sync_content():
    """Sync local database with Pinecone"""
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(host=PINECONE_INDEX_HOST)
        stats = index.describe_index_stats()
        
        pinecone_namespaces = stats.get('namespaces', {})
        
        # Pre-process categories for matching
        cat_map = {c.lower().replace(' ', '_'): c for c in CATEGORIES}
        sorted_cat_keys = sorted(cat_map.keys(), key=len, reverse=True)
        
        synced_count = 0
        deleted_count = 0
        active_db_keys = set()
        
        conn = db._get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Sync Pinecone -> SQLite
            for ns_name, ns_data in pinecone_namespaces.items():
                vector_count = ns_data.get('vector_count', 0)
                
                matched_category = None
                video_slug = None
                
                for cat_key in sorted_cat_keys:
                    if ns_name.startswith(cat_key + '_'):
                        matched_category = cat_map[cat_key]
                        video_slug = ns_name[len(cat_key)+1:]
                        break
                
                if not matched_category:
                    continue
                    
                video_name = video_slug.replace('_', ' ').title()
                active_db_keys.add((matched_category, video_name))
                
                cursor.execute('''
                    SELECT id FROM uploads 
                    WHERE category = ? AND video_name = ?
                ''', (matched_category, video_name))
                
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute('''
                        UPDATE uploads SET chunks_created = ? WHERE id = ?
                    ''', (vector_count, existing['id']))
                else:
                    cursor.execute('''
                        INSERT INTO uploads (category, video_name, filename, chunks_created, uploaded_by)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (matched_category, video_name, 'Synced from Pinecone', vector_count, session['user_id']))
                    synced_count += 1
            
            # 2. Sync SQLite -> Pinecone (Delete stale local)
            cursor.execute('SELECT id, category, video_name FROM uploads')
            all_uploads = cursor.fetchall()
            
            for upload in all_uploads:
                key = (upload['category'], upload['video_name'])
                if key not in active_db_keys:
                    cursor.execute('DELETE FROM uploads WHERE id = ?', (upload['id'],))
                    deleted_count += 1
            
            conn.commit()
            
            audit_log('content_sync', details=f"added: {synced_count}, deleted: {deleted_count}")
            
            return jsonify({
                'success': True,
                'added': synced_count,
                'deleted': deleted_count
            })
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return jsonify({'error': 'sync_failed', 'message': str(e)}), 500

@app.route('/api/admin/upload', methods=['POST'])
@admin_required
@limiter.limit(lambda: os.environ.get('ADMIN_UPLOAD_RATE', '120 per hour') if session.get('role') == 'admin' else os.environ.get('CANDIDATE_UPLOAD_RATE', '10 per hour'))
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
        upload_id = db.create_upload_record(
            category=category,
            video_name=video_name,
            filename=file.filename,
            chunks_created=result['chunks'],
            uploaded_by=session['user_id']
        )
        
        # Log content upload
        audit_log(
            'content_uploaded',
            resource_type='upload',
            resource_id=upload_id,
            details=f"category: {category}, video: {video_name}, chunks: {result['chunks']}"
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

def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    """Chunk text into smaller pieces with overlap"""
    import re
    
    # Split into paragraphs
    paragraphs = re.split(r'\n{2,}', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 1 <= max_chars:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            
            # Handle oversized paragraphs
            if len(para) > max_chars:
                # Split long paragraph
                words = para.split()
                temp = ""
                for word in words:
                    if len(temp) + len(word) + 1 <= max_chars:
                        temp += (" " if temp else "") + word
                    else:
                        if temp:
                            chunks.append(temp)
                        temp = word
                if temp:
                    current_chunk = temp
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Create embeddings for batch of texts using OpenAI"""
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

# ============================================================================
# TRAINING SESSION ENDPOINTS
# ============================================================================

@app.route('/api/training/start', methods=['POST'])
@login_required
def start_training_session():
    """Start a new training session"""
    try:
        data = request.json
        
        # Validate input
        start_req = StartSessionRequest(
            category=data.get('category', ''),
            difficulty=data.get('difficulty', 'trial'),
            duration_minutes=int(data.get('duration_minutes', 10))
        )
        start_req.validate()
        
        session_id = db.create_session(
            user_id=session['user_id'],
            category=start_req.category,
            difficulty=start_req.difficulty,
            duration_minutes=start_req.duration_minutes
        )
        
        # Log session start
        audit_log(
            'session_started',
            resource_type='session',
            resource_id=session_id,
            details=f"category: {start_req.category}, difficulty: {start_req.difficulty}"
        )

        # Optional: Prepare questions immediately
        try:
            prepared = prepare_questions_internal_v3(
                session_id=session_id, 
                category=start_req.category, 
                difficulty=start_req.difficulty,
                duration_minutes=start_req.duration_minutes
            )
            questions = prepared.get('questions', [])
        except Exception as e:
            logger.error(f"Failed to prepare questions at session start: {e}")
            questions = []
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'category': start_req.category,
            'prepared_questions': questions
        })
        
    except ValueError as e:
        return jsonify({
            'error': 'validation_error',
            'message': str(e)
        }), 400

def build_category_embedding_prompt(category: str) -> str:
    return f"Summarize key facts, procedures, and scenarios for training category: {category}"

def aggregate_category_content(category: str, top_k: int = 50) -> str:
    try:
        response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={'model': 'text-embedding-3-small', 'input': build_category_embedding_prompt(category)},
            timeout=15
        )
        response.raise_for_status()
        embedding = response.json()['data'][0]['embedding']
    except Exception as e:
        logger.error(f"Failed to create category embedding: {e}")
        embedding = None
    
    text_chunks: List[str] = []
    try:
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
        
        # Collect metadata text
        for m in results:
            meta = m.get('metadata', {}) or {}
            txt = meta.get('text')
            video = meta.get('video_name', 'Unknown')
            if txt:
                # distinct source marker for LLM
                text_chunks.append(f"SOURCE: {video}\nCONTENT: {txt}")
    except Exception as e:
        logger.error(f"Failed to aggregate category content: {e}")
    
    combined = "\n\n".join(text_chunks)
    return combined[:20000]


def build_answer_rag_context(category: str, user_answer: str, top_k: int = 5) -> str:
    """
    Build RAG context specifically for a user's answer by:
    - Embedding the answer
    - Querying Pinecone with that embedding within the category namespaces
    - Joining top_k chunk texts
    Fallbacks to aggregate_category_content if anything fails.
    """
    try:
        # Embed user answer
        embed_resp = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={'model': 'text-embedding-3-small', 'input': user_answer},
            timeout=15
        )
        embed_resp.raise_for_status()
        emb_data = embed_resp.json()
        embedding = emb_data['data'][0]['embedding']

        # Query Pinecone using same namespaces as question generation
        namespaces = get_namespaces_for_category(category)
        if not namespaces:
            return aggregate_category_content(category, top_k=top_k)

        # Initialize Pinecone
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(host=PINECONE_INDEX_HOST)

        texts: List[str] = []
        for ns in namespaces:
            try:
                res = index.query(
                    vector=embedding,
                    top_k=top_k,
                    namespace=ns,
                    include_metadata=True
                )
                for m in res.matches or []:
                    txt = (m.metadata or {}).get('text')
                    if txt:
                        texts.append(txt)
            except Exception as e:
                logger.error(f"Pinecone query failed for namespace {ns}: {e}")
        if not texts:
            return aggregate_category_content(category, top_k=top_k)
        combined = "\n\n".join(texts)
        return combined[:20000]
    except Exception as e:
        logger.error(f"Answer RAG context build failed: {e}")
        return aggregate_category_content(category, top_k=top_k)

def prepare_questions_internal(session_id: int, category: str, difficulty: str) -> Dict:
    # Determine desired number of questions by difficulty
    target_counts = {
        'trial': 7,
        'basics': 8,
        'field-ready': 9
    }
    num_questions = target_counts.get(difficulty.lower(), 8)
    
    content = aggregate_category_content(category, top_k=50)
    
    system_prompt = f"""You are an expert sales training coach creating exam questions.

TRAINING MATERIAL:
{content[:8000]}

TASK: Generate exactly {num_questions} questions to test knowledge of "{category}" based ONLY on the training material above.

QUESTION TYPES NEEDED by difficulty "{difficulty}":
- Factual (what/when/how much)
- Procedural (steps/how to)
- Scenario (what if/how would you handle)

RULES:
1. Questions must be answerable from the training material
2. For each question, provide expected_answer from the material
3. For each question, list 3-5 key_points a good answer should include
4. Include source reference (video/section)
5. Make questions natural as if a customer is asking
6. Add field is_objection=true only if question tests objection handling methodology
7. Include difficulty field

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "question": "text...",
      "expected_answer": "text...",
      "key_points": ["a","b","c"],
      "source": "Video X - Section",
      "difficulty": "{difficulty}",
      "is_objection": false
    }}
  ]
}}"""
    try:
        max_tokens_qgen = min(300 + num_questions * 120, 4500)
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'X-Title': 'AHL Sales Trainer'
            },
            json={
                'model': 'openai/gpt-4o',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f'Generate {num_questions} exam questions for {category} at {difficulty} level.'}
                ],
                'temperature': 0.7,
                'max_tokens': max_tokens_qgen
            },
            timeout=45
        )
        response.raise_for_status()
        result = response.json()
        content_response = result['choices'][0]['message']['content']
        if '```json' in content_response:
            content_response = content_response.split('```json')[1].split('```')[0]
        elif '```' in content_response:
            content_response = content_response.split('```')[1].split('```')[0]
        data = json.loads(content_response.strip())
        questions = data.get('questions', [])
    except Exception as e:
        logger.error(f"Question generation failed: {e}", exc_info=True)
        questions = []
    
    try:
        ids = db.save_prepared_questions(session_id, questions)
        stored = db.get_session_questions(session_id)
    except Exception as e:
        logger.error(f"Saving prepared questions failed: {e}")
        stored = []
    
    return {'questions': stored}

def prepare_questions_internal_v3(session_id: int, category: str, difficulty: str, duration_minutes: int = 10) -> Dict:
    # Base minimum counts by difficulty
    min_counts = {
        'trial': 7,
        'basics': 8,
        'field-ready': 9
    }
    dl = (difficulty or '').lower()
    base_min = min_counts.get(dl, 7)
    
    # Dynamic Calculation: 0.6 questions per minute (approx 1.6 mins per Q)
    # Examples: 10m -> 6q, 20m -> 12q, 30m -> 18q
    calculated_count = int(duration_minutes * 0.6)
    
    # Use max of base_min or calculated, cap at 25
    num_questions = min(max(calculated_count, base_min), 25)
    
    logger.info(f"Preparing {num_questions} questions for {duration_minutes} min session (difficulty: {difficulty})")

    content = aggregate_category_content(category, top_k=50)
    is_objection_category = 'objection' in (category or '').lower()
    distribution_hint = {
        'trial': 'Mostly factual (approx 70%) with some procedural (approx 30%); no complex scenarios',
        'basics': 'Balanced mix of factual (40%), procedural (30%), and scenario (30%) questions',
        'field-ready': 'Focus on procedural (30%) and complex scenario/edge-case (70%) questions'
    }.get(dl, 'balanced mix of factual, procedural, and scenario questions')
    objection_hint = ''
    if is_objection_category:
        objection_hint = (
            "\nOBJECTION SCENARIOS TO COVER (mark is_objection=true):\n"
            "- Longevity vs natural look tradeoff\n"
            "- Budget below ₹35,000 (two-option framing)\n"
            "- Why not transplant? (donor limitations and density)\n"
            "- Proper closing technique after handling objections\n"
            "- Indecisive customer (remove pressure, maintain authority)\n"
        )
    system_prompt = f"""You are an expert sales training coach creating exam questions.

TRAINING MATERIAL (verbatim excerpts; do not invent facts):
{content[:8000]}

TASK: Generate exactly {num_questions} questions to test knowledge of "{category}" based ONLY on the training material above.

QUESTION MIX for difficulty "{difficulty}": {distribution_hint}
{objection_hint}

STRICT RULES:
1) Every question must be answerable from the material. No outside knowledge.
2) Provide an "expected_answer" based on the material.
3) Provide 3-5 "key_points" the answer should include (short phrases).
4) Provide a "source" reference (exact video name from SOURCE: ... lines).
5) Phrase questions like a real customer would ask.
6) Set "is_objection"=true only for objection-handling technique questions.
7) Include a "difficulty" field matching the input difficulty.

OUTPUT (JSON only):
{{
  "questions": [
    {{
      "question": "...",
      "expected_answer": "...",
      "key_points": ["a","b","c"],
      "source": "Video Name",
      "difficulty": "{difficulty}",
      "is_objection": false
    }}
  ]
}}"""
    try:
        t0 = datetime.now()
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'X-Title': 'AHL Sales Trainer'
            },
            json={
                'model': 'openai/gpt-4o',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f'Generate {num_questions} exam questions for {category} at {difficulty} level.'}
                ],
                'temperature': 0.7,
                'max_tokens': min(300 + num_questions * 150, 4500)
            },
            timeout=45
        )
        response.raise_for_status()
        result = response.json()
        content_response = result['choices'][0]['message']['content']
        if '```json' in content_response:
            content_response = content_response.split('```json')[1].split('```')[0]
        elif '```' in content_response:
            content_response = content_response.split('```')[1].split('```')[0]
        data = json.loads(content_response.strip())
        questions = data.get('questions', [])
        logger.info(f"question_generation_duration_ms={int((datetime.now()-t0).total_seconds()*1000)} category={category} difficulty={difficulty}")
    except Exception as e:
        logger.error(f"Question generation v3 failed: {e}", exc_info=True)
        questions = []
    try:
        db.save_prepared_questions(session_id, questions)
        stored = db.get_session_questions(session_id)
    except Exception as e:
        logger.error(f"Saving prepared questions v3 failed: {e}")
        stored = []
    return {'questions': stored}

@app.route('/api/training/prepare', methods=['POST'])
@login_required
def prepare_training_questions():
    """Prepare questions for an existing session"""
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'missing_session_id'}), 400
    sess = db.get_session(session_id)
    if not sess or sess['user_id'] != session['user_id']:
        return jsonify({'error': 'not_found'}), 404
    
    result = prepare_questions_internal_v3(
        session_id=session_id, 
        category=sess['category'], 
        difficulty=sess['difficulty'],
        duration_minutes=sess.get('duration_minutes', 10)
    )
    return jsonify(result)

def evaluate_answer_internal(session_id: int, question: Dict, user_answer: str, category: str) -> Dict:
    # Build evaluation prompt (objection vs standard)
    key_points = json.loads(question.get('key_points_json') or '[]')
    is_objection = bool(question.get('is_objection'))
    training_content = build_answer_rag_context(category, user_answer, top_k=5)
    if is_objection:
        forbidden = [
            'apologizing for price/limitations',
            'arguing with customer',
            'over-explaining',
            'losing control of conversation'
        ]
        forbidden_str = "\n".join([f"- {m}" for m in forbidden])
        evaluation_prompt = f"""You are evaluating a sales trainee's objection-handling response.
EVALUATION CRITERIA:
- IGNORE filler words (um, uh, like, you know) and minor stammering.
- Focus strictly on MEANING and INTENT.
- Paraphrasing is ENCOURAGED. If they convey the right concept in different words, give FULL CREDIT.
- Do not penalize for conversational style or informal grammar.

SCORING RULES:
- If the core meaning matches: Minimum Score = 7/10
- If technique is correct but wording is different: Score = 8/10 or higher
- Only penalize if they explicitly violate a Forbidden Mistake or give factually wrong info.

FEEDBACK GUIDELINES:
- Start with what they did RIGHT (e.g., "Good job staying calm").
- If they paraphrased correctly, acknowledge it (e.g., "You captured the right idea about...").
- Keep criticism constructive and focused on major missing points, not minor word choices.

PENALTIES: apologizing (-3), arguing (-5), over-explaining (-2), losing control (-4)
BONUS: using prescribed language OR equivalent professional phrasing (+2)

OBJECTION SCENARIO:
{question.get('question_text')}

EXPECTED (from training):
{question.get('expected_answer')}

KEY POINTS:
{json.dumps(key_points, indent=2)}

FORBIDDEN MISTAKES:
{forbidden_str}

RELEVANT TRAINING CONTENT:
{training_content[:1500]}

USER'S ANSWER:
"{user_answer}"

OUTPUT JSON:
{{
  "tone": 0,
  "technique": 0,
  "key_points_covered": 0,
  "closing": 0,
  "objection_score": 0,
  "overall_score": 0,
  "what_correct": "",
  "what_missed": "",
  "what_wrong": null,
  "forbidden_mistakes_made": [],
  "prescribed_language_used": false,
  "feedback": "",
  "spoken_feedback": "Short, encouraging, specific 1-2 sentences for TTS",
  "evidence_from_training": ""
}}"""
    else:
        evaluation_prompt = f"""You are a supportive sales training evaluator.
Your goal is to verify understanding, not memorization.

IMPORTANT INSTRUCTIONS:
1. IGNORE filler words, hesitations, or conversational fluff.
2. If the user captures the CORE IDEA, mark it correct (8/10+).
3. Do NOT penalize for using different vocabulary if the meaning is preserved.
4. Example: If expected is "Build trust", and user says "Make them feel comfortable", count it as CORRECT.

SCORING GUIDANCE:
- Semantically correct but informal: 8/10
- Covers key points with fillers: 9/10
- Factually wrong: <5/10

FEEDBACK GUIDELINES:
- If the answer is correct but informal, praise the understanding (e.g., "Spot on! You understood that...").
- Do NOT correct their grammar or word choice unless it changes the meaning.
- Keep spoken_feedback conversational and encouraging.

QUESTION:
{question.get('question_text')}

EXPECTED ANSWER:
{question.get('expected_answer')}

KEY POINTS:
{json.dumps(key_points, indent=2)}

RELEVANT TRAINING MATERIAL:
{training_content[:1500]}

USER'S ANSWER:
"{user_answer}"

OUTPUT JSON:
{{
  "accuracy": 0,
  "completeness": 0,
  "clarity": 0,
  "overall_score": 0,
  "what_correct": "",
  "what_missed": "",
  "what_wrong": null,
  "feedback": "",
  "spoken_feedback": "Short, encouraging, specific 1-2 sentences for TTS",
  "evidence_from_training": ""
}}"""
    try:
        t0 = datetime.now()
        eval_response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'X-Title': 'AHL Sales Trainer'
            },
            json={
                'model': 'openai/gpt-4o',
                'messages': [
                    {'role': 'system', 'content': evaluation_prompt},
                    {'role': 'user', 'content': 'Evaluate this answer strictly but fairly.'}
                ],
                'temperature': 0.3,
                'max_tokens': 800
            },
            timeout=30
        )
        eval_response.raise_for_status()
        result = eval_response.json()
        content = result['choices'][0]['message']['content']
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        evaluation = json.loads(content.strip())
        logger.info(f"evaluation_duration_ms={int((datetime.now()-t0).total_seconds()*1000)} category={category} is_objection={is_objection}")
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        evaluation = {
            'accuracy': None, 'completeness': None, 'clarity': None,
            'tone': None, 'technique': None, 'closing': None,
            'overall_score': 0, 'feedback': 'Evaluation failed', 'evidence_from_training': '',
        }
    evaluation['user_answer'] = user_answer
    # Ensure objection_score exists for objection questions
    if is_objection and 'objection_score' not in evaluation:
        try:
            evaluation['objection_score'] = float(evaluation.get('overall_score') or 0)
        except Exception:
            evaluation['objection_score'] = 0
    # Add a lightweight feedback tier and speakable feedback
    try:
        score = float(evaluation.get('overall_score') or 0)
    except Exception:
        score = 0.0
    if score >= 8:
        tier = 'positive'
        fallback_speak = 'Excellent! That is correct and well-articulated.'
    elif score >= 5:
        tier = 'constructive'
        fallback_speak = 'Good effort. You covered the main points, but you missed a few details.'
    else:
        tier = 'corrective'
        fallback_speak = 'Not quite. Please review the training material.'
        
    evaluation['feedback_tier'] = tier
    # Use LLM generated spoken feedback if available, otherwise fallback
    evaluation['speak_feedback'] = evaluation.get('spoken_feedback') or fallback_speak
    return evaluation

@app.route('/api/training/evaluate-answer', methods=['POST'])
@login_required
def evaluate_answer():
    """Evaluate a user's answer and record the result"""
    data = request.json
    session_id = data.get('session_id')
    question_id = data.get('question_id')
    user_answer = data.get('user_answer', '')
    if not all([session_id, question_id, user_answer]):
        return jsonify({'error': 'missing_fields'}), 400
    sess = db.get_session(session_id)
    if not sess or sess['user_id'] != session['user_id']:
        return jsonify({'error': 'not_found'}), 404
    questions = db.get_session_questions(session_id)
    question = next((q for q in questions if q['id'] == question_id), None)
    if not question:
        return jsonify({'error': 'question_not_found'}), 404
    evaluation = evaluate_answer_internal(session_id, question, user_answer, sess['category'])
    try:
        db.save_answer_evaluation(session_id, question_id, evaluation)
    except Exception as e:
        logger.error(f"Saving evaluation failed: {e}")
    return jsonify({'evaluation': evaluation})

@app.route('/api/training/get-next-question', methods=['POST'])
@login_required
def get_next_question():
    """Get next unanswered question for a session"""
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'missing_session_id'}), 400
    sess = db.get_session(session_id)
    if not sess or sess['user_id'] != session['user_id']:
        return jsonify({'error': 'not_found'}), 404
    questions = db.get_session_questions(session_id)
    try:
        conn = db._get_connection()
        cur = conn.cursor()
        cur.execute('SELECT question_id, overall_score FROM answer_evaluations WHERE session_id = ?', (session_id,))
        evals = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        evals = []
    answered_ids = {e['question_id'] for e in evals}
    unanswered = [qq for qq in questions if qq['id'] not in answered_ids]
    if not unanswered:
        return jsonify({'done': True})
    scores = [e.get('overall_score') for e in evals if e.get('overall_score') is not None]
    avg = sum(scores) / len(scores) if scores else None
    weak_topics = set()
    if evals:
        low_ids = {e['question_id'] for e in evals if (e.get('overall_score') or 0) < 5}
        qp = {q['id']: json.loads(q.get('key_points_json') or '[]') for q in questions}
        for qid in low_ids:
            for kp in qp.get(qid, []):
                weak_topics.add(kp.strip().lower())

    def preference(qrow):
        is_obj = bool(qrow.get('is_objection'))
        kps = [s.strip().lower() for s in json.loads(qrow.get('key_points_json') or '[]')]
        match = any(k in weak_topics for k in kps) if weak_topics else False
        match_weight = 0 if match else 1
        base = qrow.get('position') or 9999
        if avg is None:
            return (match_weight, base)
        if avg >= 8:
            return (match_weight, (0 if is_obj else 1), base)
        if avg < 5:
            return (match_weight, (0 if not is_obj else 1), base)
        return (match_weight, base)
    unanswered.sort(key=preference)
    q = unanswered[0]
    return jsonify({'question': {
        'id': q['id'],
        'position': q['position'],
        'question_text': q['question_text'],
        'expected_answer': q['expected_answer'],
        'key_points': json.loads(q['key_points_json'] or '[]'),
        'source': q['source'],
        'difficulty': q['difficulty'],
        'is_objection': bool(q['is_objection'])
    }})

@app.route('/api/training/resume/<int:session_id>', methods=['POST'])
@login_required
def resume_training_session(session_id):
    """Resume an existing training session"""
    try:
        # Validate input
        resume_req = ResumeSessionRequest(session_id=session_id)
        resume_req.validate()
        
        # Get session
        session_obj = db.get_session(session_id)
        
        if not session_obj:
            return jsonify({'error': 'not_found', 'message': 'Session not found'}), 404
            
        # Verify ownership
        if session_obj['user_id'] != session['user_id']:
            return jsonify({'error': 'unauthorized', 'message': 'Not authorized'}), 403
            
        # Verify status
        if session_obj['status'] == 'completed':
            return jsonify({'error': 'completed', 'message': 'Session already completed'}), 400
            
        # Get conversation history
        messages = db.get_session_messages(session_id)
        
        # Calculate remaining time
        # Parse started_at (SQLite default format: YYYY-MM-DD HH:MM:SS)
        try:
            started_at = datetime.strptime(session_obj['started_at'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            # Fallback for robustness
            started_at = datetime.now(timezone.utc)
            
        elapsed_seconds = (datetime.now(timezone.utc) - started_at).total_seconds()
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
        
    except ValueError as e:
        return jsonify({
            'error': 'validation_error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error resuming session: {e}", exc_info=True)
        return jsonify({
            'error': 'resume_failed',
            'message': str(e)
        }), 500

@app.route('/api/training/message', methods=['POST'])
@login_required
def add_training_message():
    """Add a message to training session"""
    data = request.json
    session_id = data.get('session_id')
    role = data.get('role')
    content = data.get('content')
    context_source = data.get('context_source', 'unknown')
    evaluation_data = data.get('evaluation_data')
    
    if not all([session_id, role, content]):
        return jsonify({'error': 'missing_fields'}), 400
    
    db.add_message(session_id, role, content, context_source, evaluation_data)
    
    return jsonify({'success': True})

@app.route('/api/training/end', methods=['POST'])
@login_required
def end_training_session():
    """End a training session and generate report"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'missing_session_id'}), 400
    
    # Mark session as completed
    db.complete_session(session_id)
    
    # Log session completion
    audit_log(
        'session_completed',
        resource_type='session',
        resource_id=session_id
    )
    
    return jsonify({'success': True})

@app.route('/api/training/report/<int:session_id>', methods=['POST'])
@login_required
def save_report(session_id):
    """Save generated report for a session"""
    data = request.json
    report_html = data.get('report_html')
    overall_score = data.get('overall_score')
    
    if not report_html:
        return jsonify({'error': 'missing_report'}), 400
    
    db.save_report(session_id, report_html, overall_score)
    
    # Notify admins about completed session (if score is low or just general notification)
    try:
        sess_data = db.get_session(session_id)
        if sess_data and sess_data.get('overall_score'):
            # Fetch admin email(s) - for now just log it or send to a configured admin
            # In a real app, you might query users where role='admin'
            
            # Example notification logic
            if app.config.get('MAIL_USERNAME'):
                subject = f"Training Completed: {sess_data.get('username')} - Score: {sess_data.get('overall_score')}/10"
                body = f"""
                <h2>Session Completed</h2>
                <p><strong>Candidate:</strong> {sess_data.get('username')}</p>
                <p><strong>Category:</strong> {sess_data.get('category')}</p>
                <p><strong>Score:</strong> {sess_data.get('overall_score')}/10</p>
                <p><a href="http://localhost:8000/admin-dashboard.html">View Dashboard</a></p>
                """
                # Send to admin email (could be env var or first admin in db)
                admin_email = os.environ.get('ADMIN_EMAIL') 
                if admin_email:
                    send_email_notification(subject, [admin_email], body)
    except Exception as e:
        logger.error(f"Failed to send completion notification: {e}")

    return jsonify({'success': True})

# ============================================================================
# RAG & AI ENDPOINTS (Proxies to keep keys secure)
# ============================================================================

@app.route('/api/ai/embed', methods=['POST'])
@login_required
@limiter.limit("60 per minute")
def create_embedding():
    """Create embedding via OpenAI (proxy)"""
    data = request.json
    text = data.get('text')
    
    if not text:
        return jsonify({'error': 'missing_text'}), 400
    
    try:
        response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'text-embedding-3-small',
                'input': text
            },
            timeout=30
        )
        
        response.raise_for_status()
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/query', methods=['POST'])
@login_required
@limiter.limit("60 per minute")
def query_vectors():
    """Query Pinecone for relevant content (proxy)"""
    data = request.json
    embedding = data.get('embedding')
    category = data.get('category')
    top_k = data.get('top_k', 6)
    
    if not embedding or not category:
        return jsonify({'error': 'missing_fields'}), 400
    
    try:
        cache_key = f"pinecone_query:{category}:{hashlib.sha256(json.dumps(embedding).encode('utf-8')).hexdigest()}:{top_k}"
        cached = cache_get(cache_key)
        if cached:
            return jsonify({'matches': cached})
        # Get all namespaces for this category
        namespaces = get_namespaces_for_category(category)
        logger.info(f"Pinecone query: category={category}, namespaces={namespaces}, top_k={top_k}")
        
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(host=PINECONE_INDEX_HOST)
        
        all_matches = []
        
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
        
        if namespaces:
            max_workers = min(4, len(namespaces))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(run_query, ns): ns for ns in namespaces}
                for fut in as_completed(futures):
                    results = fut.result()
                    if results and 'matches' in results:
                        all_matches.extend(results['matches'])
        
        # Sort by score and take top_k
        all_matches.sort(key=lambda x: x.get('score', 0), reverse=True)
        all_matches = all_matches[:top_k]
        
        cache_set(cache_key, all_matches, ttl_seconds=20)
        
        try:
            preview = []
            for m in all_matches[:5]:
                meta = m.get('metadata', {}) or {}
                preview.append({
                    "score": round(m.get('score', 0), 4),
                    "namespace": meta.get('namespace'),
                    "category": meta.get('category'),
                    "video_name": meta.get('video_name'),
                    "chunk_index": meta.get('chunk_index')
                })
            logger.info(f"Pinecone matches: {preview}")
        except Exception:
            pass
        
        return jsonify({'matches': all_matches})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_namespaces_for_category(category: str) -> List[str]:
    """Get all Pinecone namespaces for a category"""
    uploads = db.get_uploads_by_category(category)
    
    namespaces = []
    for upload in uploads:
        video_name = upload['video_name']
        ns = f"{category.lower().replace(' ', '_')}_{video_name.lower().replace(' ', '_')}"
        namespaces.append(ns)
    
    return namespaces

@app.route('/api/ai/chat', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def chat_completion():
    """OpenRouter chat completion (proxy)"""
    data = request.json
    
    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'HTTP-Referer': request.headers.get('Referer', ''),
                'X-Title': 'AHL Sales Trainer'
            },
            json=data,
            timeout=60
        )
        
        response.raise_for_status()
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

@app.route('/api/admin/dashboard', methods=['GET'])
@admin_required
def get_dashboard_data():
    """Get dashboard data for admin"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    search = request.args.get('search', '')
    
    cache_key = f"admin_dashboard:{page}:{limit}:{search or ''}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    
    candidates, total_count = db.list_users(
        role='candidate', 
        page=page, 
        limit=limit, 
        search=search if search else None
    )
    
    # Get global stats
    global_stats = db.get_global_stats()
    
    dashboard_data = []
    for candidate in candidates:
        sessions = db.get_user_sessions(candidate['id'])
        
        category_scores = {}
        for sess in sessions:
            if sess['status'] == 'completed' and sess['overall_score'] is not None:
                cat = sess['category']
                if cat not in category_scores:
                    category_scores[cat] = []
                category_scores[cat].append(sess['overall_score'])
        
        # Calculate averages
        category_averages = {}
        for cat, scores in category_scores.items():
            category_averages[cat] = {
                'average': round(sum(scores) / len(scores), 1),
                'count': len(scores),
                'latest': scores[-1] if scores else None
            }
        
        # Overall average
        all_scores = [s for scores in category_scores.values() for s in scores]
        overall_avg = round(sum(all_scores) / len(all_scores), 1) if all_scores else None
        
        dashboard_data.append({
            'user_id': candidate['id'],
            'name': candidate['name'],
            'username': candidate['username'],
            'total_sessions': len(sessions),
            'completed_sessions': len([s for s in sessions if s['status'] == 'completed']),
            'category_performance': category_averages,
            'overall_average': overall_avg
        })
    
    response_data = {
        'candidates': dashboard_data,
        'stats': global_stats,
        'pagination': {
            'total': total_count,
            'page': page,
            'limit': limit,
            'pages': (total_count + limit - 1) // limit
        }
    }
    cache_set(cache_key, response_data, ttl_seconds=15)
    return jsonify(response_data)

@app.route('/api/sessions/user/<int:user_id>', methods=['GET'])
@login_required
def get_user_sessions(user_id):
    """Get all sessions for a user"""
    # Check permission
    if session['role'] != 'admin' and session['user_id'] != user_id:
        return jsonify({'error': 'permission_denied'}), 403
    
    sessions = db.get_user_sessions(user_id)
    return jsonify({'sessions': sessions})

@app.route('/api/training/report/<int:session_id>', methods=['GET'])
@login_required
def get_session_report(session_id):
    """Get report for a session"""
    session_data = db.get_session(session_id)
    if not session_data:
        return jsonify({'error': 'session_not_found'}), 404
    if session['role'] != 'admin' and session['user_id'] != session_data['user_id']:
        return jsonify({'error': 'permission_denied'}), 403
    report = db.get_report(session_id)
    if not report:
        try:
            t0 = datetime.now()
            html = build_enhanced_report_html(db, session_id)
            db.save_report(session_id, html, None)
            report_html = html
            logger.info(f"report_generation_duration_ms={int((datetime.now()-t0).total_seconds()*1000)} session_id={session_id}")
        except Exception as e:
            logger.error(f"Failed to build enhanced report: {e}")
            return jsonify({'error': 'report_not_found'}), 404
    else:
        report_html = report['report_html']
    # Role-aware response: candidates get minimal report without scores
    is_admin = (session.get('role') == 'admin')
    response_html = report_html if is_admin else build_candidate_report_html(db, session_id)
    return jsonify({
        'report_html': response_html,
        'session': session_data
    })

@app.route('/api/sessions/<int:session_id>/export/pdf', methods=['GET'])
@login_required
def export_session_pdf(session_id):
    """Export session report as PDF"""
    try:
        # Get session details
        session_data = db.get_session(session_id)
        if not session_data:
            return jsonify({'error': 'not_found', 'message': 'Session not found'}), 404
            
        # Check permissions
        if session['role'] != 'admin' and session['user_id'] != session_data['user_id']:
            return jsonify({'error': 'unauthorized', 'message': 'Not authorized'}), 403
            
        # Get report content (role-aware)
        is_admin = (session.get('role') == 'admin')
        report_row = db.get_report(session_id)
        if not report_row:
            return jsonify({'error': 'no_report', 'message': 'Report not generated yet'}), 404
        if is_admin:
            report_data = report_row
        else:
            # Build candidate-only HTML and hide scores in PDF metadata
            candidate_html = build_candidate_report_html(db, session_id)
            report_data = {'report_html': candidate_html}
            session_data['overall_score'] = None
            session_data['hide_scores'] = True
            
        # Generate PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp:
            output_path = temp.name
            
        generate_session_pdf(session_data, report_data, output_path)
        
        # Log export
        audit_log(
            'export_pdf',
            resource_type='session',
            resource_id=session_id
        )
        
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"session_report_{session_id}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"PDF export failed: {e}")
        return jsonify({'error': 'export_failed', 'message': str(e)}), 500

@app.route('/api/admin/sessions/<int:session_id>/notes', methods=['PUT'])
@admin_required
def update_session_notes(session_id):
    """Update notes for a session"""
    try:
        data = request.json
        notes = data.get('notes', '')
        
        # Verify session exists
        session_data = db.get_session(session_id)
        if not session_data:
            return jsonify({'error': 'not_found'}), 404
            
        db.update_session_notes(session_id, notes)
        
        # Log action
        audit_log(
            'session_notes_updated',
            resource_type='session',
            resource_id=session_id,
            details=f"Notes updated"
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Failed to update notes: {e}")
        return jsonify({'error': 'update_failed'}), 500

# ============================================================================
# INITIALIZATION (Runs on import)
# ============================================================================

# Ensure data directory exists (handle both local and Render paths)
db_dir = os.path.dirname(DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

# Initialize database
db.initialize()

# Create default admin if doesn't exist
try:
    admin = db.get_user_by_username('admin')
    if not admin:
        db.create_user('admin', 'admin123', 'System Admin', role='admin')
        logger.info("✅ Default admin created (admin/admin123)")
except Exception as e:
    logger.warning(f"Could not check/create admin on startup: {e}")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    logger.info(f"🚀 AHL Sales Trainer Backend Running on http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
