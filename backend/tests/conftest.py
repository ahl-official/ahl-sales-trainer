import pytest
import os
import sys
import tempfile
import sqlite3

# Disable rate limiting for tests
os.environ['DISABLE_RATE_LIMITING'] = 'true'

# Add backend to path so we can import app and database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import Database
from app import app as flask_app

@pytest.fixture
def db_path():
    """Create a temporary database file"""
    fd, path = tempfile.mkstemp()
    yield path
    os.close(fd)
    os.remove(path)

@pytest.fixture
def db(db_path):
    """Initialize database"""
    database = Database(db_path)
    database.initialize()
    return database

@pytest.fixture
def client(db_path):
    """Create test client"""
    flask_app.config['TESTING'] = True
    flask_app.secret_key = 'test_secret_key'
    
    # Patch the global db object in app
    from app import db as app_db
    original_path = app_db.db_path
    app_db.db_path = db_path
    app_db.initialize()
    
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client
            
    # Restore original path (though not strictly necessary for one-off test runs)
    app_db.db_path = original_path
