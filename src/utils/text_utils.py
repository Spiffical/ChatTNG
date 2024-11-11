import re
import nltk
from typing import List

# Download required NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def clean_dialog_text(text: str) -> str:
    """Clean dialog text by removing HTML tags, brackets, and standardizing format"""
    # Remove HTML tags while preserving their content
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove text in square brackets
    text = re.sub(r'\[.*?\]', '', text)
    
    # Remove stage directions in parentheses
    text = re.sub(r'\([^)]*\)', '', text)
    
    # Remove character names (all caps followed by colon, with or without space)
    text = re.sub(r'^[A-Z]+\s*:', '', text)
    
    # Standardize whitespace
    text = ' '.join(text.split())
    
    return text.strip()

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using NLTK's sentence tokenizer"""
    # Clean the text first
    text = clean_dialog_text(text)
    
    # Handle ellipsis properly
    text = text.replace('...', '<ELLIPSIS>')
    
    # Split into sentences
    sentences = nltk.sent_tokenize(text)
    
    # Restore ellipsis and clean up
    sentences = [s.replace('<ELLIPSIS>', '...').strip() for s in sentences]
    
    # Filter out empty sentences
    return [s for s in sentences if s]

def extract_character_name(text: str) -> str:
    """Extract character name from query if it starts with a name and comma"""
    # Common character names in TNG
    character_names = {
        'PICARD', 'DATA', 'RIKER', 'WORF', 'TROI', 'CRUSHER', 'BEVERLY',
        'GEORDI', 'LA FORGE', 'WESLEY', 'GUINAN', 'Q', 'TASHA', 'YAR'
    }
    
    # Check for name followed by comma pattern
    match = re.match(r'^([A-Za-z\s]+),\s*', text)
    if match:
        name = match.group(1).upper()
        # Check if it's a known character name
        for char_name in character_names:
            if char_name in name:
                return char_name
    return ""
