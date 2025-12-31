import pytest
from database import Database

def test_user_creation(db):
    """Test user creation and retrieval"""
    user_id = db.create_user("testuser", "password", "Test User", "candidate")
    assert user_id is not None
    
    user = db.get_user_by_username("testuser")
    assert user['username'] == "testuser"
    assert user['role'] == "candidate"

def test_session_lifecycle(db):
    """Test session creation, update, and completion"""
    user_id = db.create_user("sessionuser", "pass", "Session User", "candidate")
    
    # Create session
    session_id = db.create_session(user_id, "Sales", "Hard", 45)
    assert session_id is not None
    
    # Get session
    session = db.get_session(session_id)
    assert session['status'] == 'active'
    assert session['category'] == 'Sales'
    
    # Complete session
    db.complete_session(session_id, overall_score=8.5)
    
    session = db.get_session(session_id)
    assert session['status'] == 'completed'
    assert session['overall_score'] == 8.5
    assert session['ended_at'] is not None

def test_search_sessions(db):
    """Test advanced search functionality"""
    u1 = db.create_user("u1", "p", "User 1", "candidate")
    u2 = db.create_user("u2", "p", "User 2", "candidate")
    
    # Create some sessions
    s1 = db.create_session(u1, "Category A", "Easy", 30) # Active
    db.complete_session(s1, overall_score=9.0) # Completed, score 9.0
    
    s2 = db.create_session(u2, "Category B", "Hard", 30)
    db.complete_session(s2, overall_score=5.0) # Completed, score 5.0
    
    s3 = db.create_session(u1, "Category A", "Medium", 30) # Active
    
    # Search by category
    results, count = db.search_sessions(category="Category A")
    assert count == 2
    assert len(results) == 2
    
    # Search by score
    results, count = db.search_sessions(min_score=8.0)
    assert count == 1
    assert results[0]['id'] == s1
    
    # Search by user (search_term)
    results, count = db.search_sessions(search_term="User 2")
    assert count == 1
    assert results[0]['id'] == s2
    
    # Search by combined filters
    results, count = db.search_sessions(category="Category A", min_score=8.0)
    assert count == 1
    assert results[0]['id'] == s1

def test_session_notes(db):
    """Test adding and retrieving session notes"""
    user_id = db.create_user("noteuser", "p", "Note User", "candidate")
    session_id = db.create_session(user_id, "Notes", "Easy", 15)
    
    # Initially empty
    session = db.get_session(session_id)
    assert session['notes'] is None
    
    # Add notes
    db.update_session_notes(session_id, "These are some admin notes.")
    
    session = db.get_session(session_id)
    assert session['notes'] == "These are some admin notes."

def test_dashboard_stats(db):
    """Test dashboard statistics calculation"""
    u1 = db.create_user("u1", "p", "U1", "candidate")
    u2 = db.create_user("u2", "p", "U2", "candidate")
    
    # 2 active candidates
    
    s1 = db.create_session(u1, "Sales", "Easy", 30)
    db.complete_session(s1, overall_score=8.0)
    
    s2 = db.create_session(u2, "Negotiation", "Hard", 30)
    db.complete_session(s2, overall_score=6.0)
    
    s3 = db.create_session(u1, "Sales", "Medium", 30) # Active
    
    stats = db.get_dashboard_stats()
    
    # Assuming get_dashboard_stats implementation counts candidates correctly
    # Depending on implementation, it might count all users with role 'candidate'
    assert stats['total_candidates'] == 2
    assert stats['total_sessions'] == 3
    # Average score might be across all completed sessions
    assert stats['avg_score'] == 7.0 # (8+6)/2

def test_user_stats(db):
    """Test individual user stats"""
    u1 = db.create_user("statuser", "p", "Stat User", "candidate")
    
    s1 = db.create_session(u1, "Sales", "Easy", 30)
    db.complete_session(s1, overall_score=10.0)
    
    s2 = db.create_session(u1, "Sales", "Hard", 30)
    db.complete_session(s2, overall_score=8.0)
    
    stats = db.get_user_stats(u1)
    
    assert stats['total_sessions'] == 2
    assert stats['avg_score'] == 9.0
    assert stats['sessions_by_difficulty']['Easy'] == 1
    assert stats['sessions_by_difficulty']['Hard'] == 1
