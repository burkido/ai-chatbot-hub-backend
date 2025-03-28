import json
from pathlib import Path
from typing import Dict, Any, Optional, Set
from functools import lru_cache
import re

from fastapi import Request

# Convert to a set for faster lookups
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES: Set[str] = {"en", "fr", "es", "de", "tr"}
SUPPORTED_LANGUAGES_MAP = {lang: lang for lang in SUPPORTED_LANGUAGES}

class Translator:
    """Handles loading and providing translations for the application."""
    
    def __init__(self):
        self.translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()
    
    def _load_translations(self) -> None:
        """Load all translation files from the translations directory."""
        translations_dir = Path(__file__).parent.parent / "translations"
        
        if not translations_dir.exists():
            raise FileNotFoundError(f"Translations directory not found: {translations_dir}")
        
        for lang in SUPPORTED_LANGUAGES:
            lang_file = translations_dir / f"{lang}.json"
            if lang_file.exists():
                with open(lang_file, "r", encoding="utf-8") as f:
                    self.translations[lang] = json.load(f)
            else:
                print(f"Warning: Translation file not found for language: {lang}")
                # Create empty dict for missing languages to avoid errors
                self.translations[lang] = {}
    
    def get(self, key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
        """
        Get a translation for a key in the specified language.
        
        Args:
            key: The translation key to look up
            language: The language code (defaults to DEFAULT_LANGUAGE)
            **kwargs: Format parameters for the translation string
            
        Returns:
            The translated string, or the key itself if no translation is found
        """
        # If language is not supported, fall back to default
        if language not in SUPPORTED_LANGUAGES:
            language = DEFAULT_LANGUAGE
        
        # Get translation from language dict, fall back to default language if not found
        translation = self.translations.get(language, {}).get(key)
        if translation is None:
            # Try to get from default language
            translation = self.translations.get(DEFAULT_LANGUAGE, {}).get(key, key)
        
        # Apply format parameters if available
        if kwargs and isinstance(translation, str):
            return translation.format(**kwargs)
        
        return translation


@lru_cache()
def get_translator() -> Translator:
    """Get or create a cached translator instance."""
    return Translator()


def get_language_from_request(request: Request) -> str:
    """
    Extract the preferred language from the request efficiently.
    """
    # Check Accept-Language header
    accept_language = request.headers.get("Accept-Language")
    if accept_language:
        for lang in re.split(r",\s*", accept_language):  # Split by "," and strip spaces
            lang_code = lang.split(";")[0].strip().lower()
            short_lang = lang_code.split("-")[0]  # Extract primary language (e.g., "en" from "en-US")
            if short_lang in SUPPORTED_LANGUAGES_MAP:
                return short_lang

    # Fall back to default language
    return DEFAULT_LANGUAGE


def get_translation(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Convenience function to get a translation by key.
    
    Args:
        key: The translation key
        language: The language code
        **kwargs: Format parameters for the translation string
        
    Returns:
        The translated string
    """
    translator = get_translator()
    return translator.get(key, language, **kwargs)
