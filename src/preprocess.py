"""
preprocess.py - Text Cleaning and Intelligent Chunking

This module handles the critical first step: converting raw novel text into 
semantically meaningful chunks that preserve narrative flow and context.

Key Design Decisions:
- We use sentence-aware chunking to avoid breaking mid-thought
- Overlap between chunks ensures continuity for cross-boundary events
- Metadata tracking helps maintain document structure
"""

import re
from typing import List, Dict
import nltk
from nltk.tokenize import sent_tokenize

# Download required NLTK data on first run
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


class NovelPreprocessor:
    """
    Handles preprocessing of long-form narrative texts.
    
    The challenge here is that novels aren't just bags of sentences - they have
    structure, flow, and dependencies that span pages. Our chunking strategy
    needs to respect this while still creating manageable pieces for retrieval.
    """
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize the preprocessor.
        
        Args:
            chunk_size: Target number of words per chunk. We chose 1000 as a 
                       balance between context richness and retrieval precision.
            overlap: Number of words to overlap between chunks. This ensures
                    that events or descriptions spanning chunk boundaries are
                    still captured in at least one complete chunk.
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def clean_text(self, text: str) -> str:
        """
        Clean raw text while preserving narrative structure.
        
        We're careful here - we want to remove noise but keep things like
        em-dashes, ellipses, and paragraph breaks that carry meaning in fiction.
        """
        # Remove excessive whitespace but preserve paragraph breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove page numbers and headers that might appear in digitized texts
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # Normalize quotes and apostrophes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Remove extra spaces
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def create_chunks(self, text: str, novel_id: str) -> List[Dict]:
        """
        Split text into overlapping chunks while respecting sentence boundaries.
        
        This is where the magic happens. We need chunks that are:
        1. Large enough to contain meaningful narrative context
        2. Small enough for efficient retrieval and processing
        3. Overlapping enough to catch cross-boundary dependencies
        
        Returns a list of dictionaries, each containing the chunk text and metadata.
        """
        # First, clean the text
        text = self.clean_text(text)
        
        # Split into sentences using NLTK's trained tokenizer
        # This handles tricky cases like "Mr. Smith said" or "She arrived at 3 p.m."
        sentences = sent_tokenize(text)
        
        chunks = []
        current_chunk = []
        current_word_count = 0
        chunk_id = 0
        
        for i, sentence in enumerate(sentences):
            sentence_words = len(sentence.split())
            
            # If adding this sentence would exceed our target size, save the current chunk
            if current_word_count + sentence_words > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'novel_id': novel_id,
                    'chunk_id': chunk_id,
                    'text': chunk_text,
                    'word_count': current_word_count,
                    'sentence_range': (i - len(current_chunk), i)
                })
                
                # Create overlap by keeping the last few sentences
                # We calculate how many sentences to keep based on overlap size
                overlap_word_count = 0
                overlap_sentences = []
                
                for sent in reversed(current_chunk):
                    sent_words = len(sent.split())
                    if overlap_word_count + sent_words <= self.overlap:
                        overlap_sentences.insert(0, sent)
                        overlap_word_count += sent_words
                    else:
                        break
                
                # Start new chunk with overlap
                current_chunk = overlap_sentences
                current_word_count = overlap_word_count
                chunk_id += 1
            
            current_chunk.append(sentence)
            current_word_count += sentence_words
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'novel_id': novel_id,
                'chunk_id': chunk_id,
                'text': chunk_text,
                'word_count': current_word_count,
                'sentence_range': (len(sentences) - len(current_chunk), len(sentences))
            })
        
        return chunks
    
    def preprocess_novel(self, filepath: str, novel_id: str) -> List[Dict]:
        """
        Load and preprocess a complete novel from file.
        
        This is the main entry point for processing a novel.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return self.create_chunks(text, novel_id)


def preprocess_backstory(backstory_text: str) -> str:
    """
    Clean backstory text for comparison.
    
    Backstories are shorter and more structured than novels, so we apply
    lighter preprocessing here.
    """
    # Basic cleaning
    backstory_text = re.sub(r'\s+', ' ', backstory_text)
    backstory_text = backstory_text.strip()
    
    return backstory_text


if __name__ == "__main__":
    # Simple test to verify the chunking logic works as expected
    preprocessor = NovelPreprocessor(chunk_size=100, overlap=20)
    
    test_text = """
    This is a test sentence. Here is another one. 
    And a third sentence to build context. 
    We need enough text to create multiple chunks.
    This will help us verify the overlap mechanism.
    """
    
    chunks = preprocessor.create_chunks(test_text, "test")
    print(f"Created {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i}: {chunk['word_count']} words")
        print(chunk['text'][:100] + "...")