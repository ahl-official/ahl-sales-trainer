import pytest
from unittest.mock import MagicMock, patch
import json
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db_session(mocker):
    mock = mocker.patch('app.db.get_session')
    mock.return_value = {
        'id': 1,
        'user_id': 1,
        'started_at': '2023-01-01 12:00:00',
        'overall_score': 8.5,
        'category': 'Sales',
        'difficulty': 'Hard',
        'duration_minutes': 30,
        'username': 'testuser'
    }
    return mock

@pytest.fixture
def mock_db_report(mocker):
    mock = mocker.patch('app.db.get_report')
    mock.return_value = {
        'session_id': 1,
        'report_html': '<html><body><h1>Report</h1></body></html>'
    }
    return mock

@pytest.fixture
def mock_generate_pdf(mocker):
    mock = mocker.patch('app.generate_session_pdf')
    # It writes to the output_path provided
    def side_effect(session_data, report_data, output_path):
        with open(output_path, 'w') as f:
            f.write('%PDF-1.4 mock content')
        return output_path
    mock.side_effect = side_effect
    return mock

def test_export_pdf_success(client, mock_db_session, mock_db_report, mock_generate_pdf):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'candidate'
        
    response = client.get('/api/sessions/1/export/pdf')
    
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert 'attachment' in response.headers['Content-Disposition']
    assert 'session_report_1.pdf' in response.headers['Content-Disposition']
    
    mock_generate_pdf.assert_called_once()

def test_export_pdf_not_found(client, mocker):
    mocker.patch('app.db.get_session', return_value=None)
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'candidate'
        
    response = client.get('/api/sessions/999/export/pdf')
    assert response.status_code == 404

def test_export_pdf_unauthorized(client, mock_db_session):
    # Session belongs to user 1, but we log in as user 2
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'candidate'
        
    response = client.get('/api/sessions/1/export/pdf')
    assert response.status_code == 403

def test_export_pdf_admin_access(client, mock_db_session, mock_db_report, mock_generate_pdf):
    # Admin can access any session
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'admin'
        
    response = client.get('/api/sessions/1/export/pdf')
    assert response.status_code == 200
