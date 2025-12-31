import os
from backend.pdf_generator import generate_session_pdf
from datetime import datetime

# Mock Data
session_data = {
    'username': 'test_user',
    'started_at': '2023-10-27 10:00:00',
    'category': 'Sales Negotiation',
    'difficulty': 'Hard',
    'duration_minutes': 15,
    'overall_score': 8.5
}

report_data = {
    'report_html': """
    <h1>Feedback</h1>
    <p>Good job on the introduction.</p>
    <ul>
        <li>Point 1: Clear voice</li>
        <li>Point 2: Good empathy</li>
    </ul>
    <h3>Areas for Improvement</h3>
    <p>Try to close faster.</p>
    """
}

output_path = 'test_report.pdf'

try:
    generate_session_pdf(session_data, report_data, output_path)
    if os.path.exists(output_path):
        print(f"✅ PDF generated successfully at {output_path}")
        # Clean up
        os.remove(output_path)
    else:
        print("❌ PDF file not found after generation")
except Exception as e:
    print(f"❌ PDF generation failed: {e}")
