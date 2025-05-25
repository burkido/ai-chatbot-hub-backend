"""
Additional dependencies for the chat endpoints
"""
from fastapi import Depends, Query
from app.core.translation import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from typing import Optional

def validate_language(
    language: Optional[str] = Query(None, description="Language code for the response")
) -> Optional[str]:
    """
    Validates that the language code is supported
    
    Args:
        language: The language code to validate
        
    Returns:
        The validated language code or None
    """
    if language is None:
        return None
        
    # Normalize to lowercase and get primary language tag
    normalized_lang = language.lower().split('-')[0]
    
    # Check if the language is supported
    if normalized_lang in SUPPORTED_LANGUAGES:
        return normalized_lang
    
    # Return None if not supported (we'll fall back to default or user preference)
    return None
