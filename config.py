import os
from typing import Tuple
from flask import Flask, session
from flask_cors import CORS
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config_logging import get_logger

logger = get_logger('config')

def init_mail(app: Flask) -> Mail:
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    return Mail(app)

def init_cors(app: Flask) -> None:
    allowed_origins = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')
    CORS(
        app,
        origins=allowed_origins,
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization'],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        max_age=3600
    )

def init_limiter(app: Flask) -> Limiter:
    limiter = Limiter(
        key_func=lambda: session.get('user_id', get_remote_address()),
        app=app,
        default_limits=["1000 per day", "100 per hour"],
        storage_uri="memory://"
    )
    if os.environ.get('DISABLE_RATE_LIMITING', 'false').lower() == 'true':
        limiter.enabled = False
        logger.warning("⚠️  Rate limiting DISABLED (DISABLE_RATE_LIMITING=true)")
    return limiter
