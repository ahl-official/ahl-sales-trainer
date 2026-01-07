"""
AHL Sales Trainer - Main Backend Server
Handles authentication, data upload, training sessions, and reporting
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import requests
from deepgram import DeepgramClient
from extensions import db, limiter, mail
from pdf_generator import generate_session_pdf
from config_logging import setup_logging
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.admin_routes import viewer_bp
from routes.training_routes import training_bp
from routes.session_routes import session_bp
from routes.main_routes import main_bp
from utils.decorators import login_required

# Setup logging
logger = setup_logging()

def validate_environment():
    """
    Validate all required environment variables are set
    Fails fast on startup if anything is missing
    """
    required_vars = {
        'SECRET_KEY': {
            'description': 'Secret key for session encryption',
            'min_length': 32
        },
        'OPENROUTER_API_KEY': {'description': 'OpenRouter API key'},
        'OPENAI_API_KEY': {'description': 'OpenAI API key'},
        'PINECONE_API_KEY': {'description': 'Pinecone API key'},
        'PINECONE_INDEX_HOST': {'description': 'Pinecone index host URL'}
    }
    
    missing = []
    for var, config in required_vars.items():
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
    logger.info("✅ Environment validated")

def test_api_connections():
    """Optional: Test API keys"""
    if os.environ.get('VALIDATE_API_KEYS', 'false').lower() != 'true':
        return

    logger.info("Testing API connectivity...")
    try:
        # Test OpenAI
        requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={'Authorization': f'Bearer {os.environ.get("OPENAI_API_KEY")}'},
            json={'model': 'text-embedding-3-small', 'input': 'test'},
            timeout=10
        )
        logger.info("✓ OpenAI API key valid")
    except Exception as e:
        logger.error(f"✗ OpenAI connection failed: {e}")

# Initialize Flask
app = Flask(__name__)

# Load environment
load_dotenv()
validate_environment()
test_api_connections()

# Configuration
app.secret_key = os.environ.get('SECRET_KEY')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False

# Mail Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

# Initialize Extensions
allowed_origins = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')
CORS(
    app,
    origins=allowed_origins,
    supports_credentials=True,
    allow_headers=['Content-Type', 'Authorization'],
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    max_age=3600
)

# Configure Limiter
app.config['RATELIMIT_STORAGE_URI'] = "memory://"
app.config['RATELIMIT_DEFAULT'] = "1000 per day; 100 per hour"
if os.environ.get('DISABLE_RATE_LIMITING', 'false').lower() == 'true':
    limiter.enabled = False

limiter.init_app(app)
mail.init_app(app)

db_dir = os.path.dirname(db.db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)
db.initialize()

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(viewer_bp, url_prefix='/api/viewer')
app.register_blueprint(training_bp, url_prefix='/api/training')
app.register_blueprint(session_bp, url_prefix='/api/sessions')
app.register_blueprint(main_bp, url_prefix='/')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    db_ok = True
    try:
        conn = db._get_connection()
        conn.execute('SELECT 1')
        conn.close()
    except Exception:
        db_ok = False
    
    return jsonify({
        'status': 'healthy',
        'db_ok': db_ok,
        'rate_limiting': limiter.enabled,
        'timestamp': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
        'db': {'ok': db_ok},
        'mail_configured': bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'))
    })

@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded: {request.remote_addr}")
    return jsonify({
        'error': 'rate_limit_exceeded',
        'message': 'Too many requests. Please slow down.',
        'retry_after': str(e.description)
    }), 429

@app.route('/api/deepgram-token', methods=['GET'])
@login_required
def deepgram_token():
    try:
        api_key = os.environ.get('DEEPGRAM_API_KEY')
        if not api_key:
            return jsonify({'error': 'missing_deepgram_key'}), 400

        # Return the key directly for now (temporary workaround)
        # TODO: Implement secure temporary key generation when Deepgram API issues are resolved
        return jsonify({'key': api_key})

        # The following code is disabled due to Deepgram API issues with temporary key generation
        """
        # Create a temporary key using Deepgram API
        client = DeepgramClient(api_key)
        
        # Get the first project
        projects_result = client.manage.v("1").projects.list()
        if not projects_result.projects:
             return jsonify({'error': 'no_deepgram_projects'}), 500
             
        project_id = projects_result.projects[0].project_id
        
        # Create a temporary key (valid for 60 seconds)
        new_key_result = client.manage.v("1").keys.create(
            project_id, 
            {
                "comment": "temp_session_key", 
                "scopes": ["usage:write"], 
                "time_to_live_in_seconds": 60
            }
        )
        
        return jsonify({'key': new_key_result.key})
        """
    except Exception as e:
        logger.error(f"Deepgram token error: {e}")
        return jsonify({'error': 'server_error'}), 500

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run the AHL Sales Trainer Server')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 5000)), help='Port to run on')
    args = parser.parse_args()
    
    app.run(host='0.0.0.0', port=args.port, debug=True)
