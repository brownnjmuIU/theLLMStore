import re


def clean_text(text: str)->str:
    """
    Light cleaning of extracted text.
    Preserves meaningful strcuure while removing noise
    """

    # Fixing hyphenation artifacts (word-\n continuation)
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    
    # Normalizing line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Removing non-printable characters (except newlines and tabs)
    text = re.sub(r'[^\S\n\t]+', ' ', text)  # normalize whitespace to single space
    text = re.sub(r'[^\x20-\x7E\n\t\u00A0-\uFFFF]', '', text)  # keep printable + unicode
    
    # Collapsing 3+ newlines into 2 (preserve paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Removing leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Removing leading/trailing whitespace from entire text
    text = text.strip()
    
    return text