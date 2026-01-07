import re
from typing import List

def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    """Chunk text into smaller pieces with overlap"""
    
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
