import os
import re
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from html import unescape

def clean_html_for_reportlab(html_content):
    if not html_content:
        return ""
    src = html_content
    m = re.search(r"<body[^>]*>([\s\S]*?)</body>", src, flags=re.IGNORECASE)
    if m:
        src = m.group(1)
    src = re.sub(r"<head[^>]*>[\s\S]*?</head>", "", src, flags=re.IGNORECASE)
    src = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", src, flags=re.IGNORECASE)
    src = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", src, flags=re.IGNORECASE)
    src = re.sub(r"<link[^>]*>", "", src, flags=re.IGNORECASE)
    src = src.replace("<br>", "<br/>").replace("<br />", "<br/>")
    src = re.sub(r"</h1\s*>", "</h1><br/><br/>", src, flags=re.IGNORECASE)
    src = re.sub(r"</h2\s*>", "</h2><br/><br/>", src, flags=re.IGNORECASE)
    src = re.sub(r"</h3\s*>", "</h3><br/><br/>", src, flags=re.IGNORECASE)
    src = re.sub(r"</p\s*>", "</p><br/><br/>", src, flags=re.IGNORECASE)
    src = re.sub(r"</div\s*>", "</div><br/>", src, flags=re.IGNORECASE)
    src = re.sub(r"<ul[^>]*>", "<br/>", src, flags=re.IGNORECASE)
    src = re.sub(r"</ul\s*>", "<br/>", src, flags=re.IGNORECASE)
    src = re.sub(r"<li[^>]*>", "&bull; ", src, flags=re.IGNORECASE)
    src = re.sub(r"</li\s*>", "<br/>", src, flags=re.IGNORECASE)
    src = re.sub(r"</?(?!br/?)[^>]+>", "", src, flags=re.IGNORECASE)
    src = unescape(src)
    return src

def generate_session_pdf(session_data, report_data, output_path):
    """
    Generate a PDF report for a training session.
    
    Args:
        session_data (dict): Session details (user, date, score, etc.)
        report_data (dict): Report content (html, feedback)
        output_path (str): Path to save the PDF
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    # Custom Styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=24,
        spaceAfter=30
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor('#1a56db') # Blue
    )
    
    normal_style = styles['Normal']
    
    # Title
    story.append(Paragraph("Sales Training Session Report", title_style))
    story.append(Spacer(1, 12))
    
    # Session Metadata Table
    # Format dates and scores
    try:
        date_str = session_data.get('started_at', 'Unknown Date')
        if isinstance(date_str, str):
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                date_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                pass
    except:
        date_str = 'Unknown'
        
    score = session_data.get('overall_score')
    score_str = f"{score}/10" if score is not None else "N/A"
    hide_scores = bool(session_data.get('hide_scores'))
    data = [
        ['Candidate:', session_data.get('username', 'Unknown')],
        ['Date:', date_str],
        ['Category:', session_data.get('category', 'Unknown')],
        ['Difficulty:', session_data.get('difficulty', 'Normal')],
        ['Duration:', f"{session_data.get('duration_minutes', 0)} minutes"],
    ]
    if not hide_scores:
        data.append(['Overall Score:', score_str])
    
    t = Table(data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('BOX', (0, 0), (-1, -1), 1, colors.lightgrey),
    ]))
    story.append(t)
    story.append(Spacer(1, 30))
    
    # Detailed Report Section
    story.append(Paragraph("Performance Analysis & Feedback", heading_style))
    
    report_html = report_data.get('report_html', '')
    if report_html:
        # Simple cleanup to make it paragraph-friendly
        # We replace block tags with line breaks to keep flow
        clean_text = clean_html_for_reportlab(report_html)
        
        # Split by double newlines to create separate paragraphs
        # This is a heuristic to break down the large HTML blob
        parts = clean_text.split('<br/><br/>')
        
        for part in parts:
            if part.strip():
                try:
                    p = Paragraph(part, normal_style)
                    story.append(p)
                    story.append(Spacer(1, 6))
                except Exception as e:
                    # Fallback for very messy HTML
                    story.append(Paragraph(part.replace('<', '&lt;').replace('>', '&gt;'), normal_style))
    else:
        story.append(Paragraph("No detailed report available.", normal_style))
        
    # Footer logic can be added here or via canvas builder
    
    doc.build(story)
    return output_path
