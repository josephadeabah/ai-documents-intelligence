# =========================
# 6. app/services/chunking.py
# =========================
from typing import List, Dict, Any
import re
from app.core.config import settings
from app.core.logging import app_logger

class AdvancedChunker:
    """Advanced text chunking with semantic boundaries"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.sentence_endings = r'[.!?][\s\n]+'
        self.paragraph_endings = r'\n\s*\n'
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Chunk text with semantic boundaries"""
        if not text or not text.strip():
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        chunk_index = 0
        
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            
            # Try to find a good break point
            if end < text_length:
                # Look for paragraph break first
                paragraph_break = text.rfind('\n\n', start, end)
                if paragraph_break != -1 and paragraph_break > start:
                    end = paragraph_break + 2
                else:
                    # Look for sentence break
                    sentence_break = self._find_sentence_break(text, start, end)
                    if sentence_break != -1:
                        end = sentence_break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "index": chunk_index,
                    "char_count": len(chunk_text),
                    "token_count": self._estimate_tokens(chunk_text),
                    "metadata": metadata or {}
                })
                chunk_index += 1
            
            # Move start position with overlap
            start = end - self.overlap if end < text_length else text_length
        
        app_logger.info(f"Created {len(chunks)} chunks from text of length {text_length}")
        return chunks
    
    def _find_sentence_break(self, text: str, start: int, end: int) -> int:
        """Find a sentence boundary within the chunk"""
        # Look for sentence endings
        search_text = text[start:end]
        
        # Find last sentence ending
        pattern = re.compile(self.sentence_endings)
        matches = list(pattern.finditer(search_text))
        
        if matches:
            return start + matches[-1].end()
        
        return -1
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token for English)"""
        return len(text) // 4
    
    def chunk_with_overlap_simple(self, text: str) -> List[str]:
        """Simple overlapping chunking as fallback"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.overlap
        
        return chunks

# Singleton instance
chunker = AdvancedChunker(chunk_size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)
chunk_text = chunker.chunk_text