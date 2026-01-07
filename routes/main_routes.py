from flask import Blueprint, send_file
import os

main_bp = Blueprint('main', __name__)

# Assuming project root is parent directory of routes/
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@main_bp.route('/', methods=['GET'])
def root_page():
    return send_file(os.path.join(FRONTEND_DIR, 'login.html'))

@main_bp.route('/login.html', methods=['GET'])
def login_page():
    return send_file(os.path.join(FRONTEND_DIR, 'login.html'))

@main_bp.route('/admin-dashboard.html', methods=['GET'])
def admin_dashboard_page():
    return send_file(os.path.join(FRONTEND_DIR, 'admin-dashboard.html'))

@main_bp.route('/admin-dashboard.js', methods=['GET'])
def admin_dashboard_js():
    return send_file(os.path.join(FRONTEND_DIR, 'admin-dashboard.js'))

@main_bp.route('/trainer.html', methods=['GET'])
def trainer_page():
    return send_file(os.path.join(FRONTEND_DIR, 'trainer.html'))
