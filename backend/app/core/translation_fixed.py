"""
Translation service utilities for multilingual support.
"""
from typing import Optional, Dict, Any, List
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings

# Configure logger
logger = logging.getLogger(__name__)

# Supported language codes - matches your requirements
SUPPORTED_LANGUAGES = {"ar", "de", "en", "es", "fr", "hi", "it", "ja", "ko", "pt", "ru", "tr", "zh"}

# Default language for the application
DEFAULT_LANGUAGE = "en"


class TranslationError(Exception):
    """Custom exception for translation-related errors"""
    pass


class TranslationService:
    """
    Service for translating text between languages using Google Cloud Translation API.
    """
    
    def __init__(self):
        """
        Initialize the translation service with Google Cloud Translation API v2
        """
        self.api_key = settings.GOOGLE_TRANSLATE_API_KEY
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
        if not self.api_key:
            raise TranslationError("Google Translate API key is not configured")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of the provided text
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary with detected language code and confidence
            
        Raises:
            TranslationError: If the API request fails
        """
        if not text or not text.strip():
            return {"language": DEFAULT_LANGUAGE, "confidence": 1.0}
        
        try:
            return await self._detect_language(text)
        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}")
            raise TranslationError(f"Failed to detect language: {str(e)}")
    
    async def _detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect language using Google Translate API v2
        """
        endpoint = "https://translation.googleapis.com/language/translate/v2/detect"
        
        params = {"key": self.api_key}
        data = {"q": text}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, params=params, data=data)
            
            if response.status_code != 200:
                logger.error(f"Language detection API error: {response.text}")
                
            response.raise_for_status()
            
            result = response.json()
            detections = result.get('data', {}).get('detections', [[]])
            
            if detections and detections[0]:
                detection = detections[0][0]
                return {
                    "language": detection.get('language', DEFAULT_LANGUAGE),
                    "confidence": detection.get('confidence', 0.0)
                }
            
            return {"language": DEFAULT_LANGUAGE, "confidence": 0.0}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def translate(
        self, 
        text: str, 
        target_language: str, 
        source_language: Optional[str] = None,
        mime_type: str = "text/plain",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate text to the target language
        
        Args:
            text: The text to translate
            target_language: The language code to translate to
            source_language: The language code to translate from (auto-detect if None)
            mime_type: The MIME type of the text (text/plain or text/html)
            model: Optional model name to use for translation
            
        Returns:
            Dictionary with translated text and detected source language
            
        Raises:
            TranslationError: If the translation fails
        """
        if not text or not text.strip():
            return {"translated_text": text, "detected_language": source_language or DEFAULT_LANGUAGE}
        
        # Validate target language
        target_clean = target_language.split("-")[0].lower()
        if target_clean not in SUPPORTED_LANGUAGES:
            raise TranslationError(f"Unsupported target language: {target_language}")
            
        # No translation needed if source and target are the same
        if source_language and source_language.split("-")[0].lower() == target_clean:
            return {"translated_text": text, "detected_language": source_language}
            
        try:
            return await self._translate(text, target_clean, source_language, mime_type, model)
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            raise TranslationError(f"Failed to translate text: {str(e)}")
    
    async def _translate(
        self,
        text: str,
        target: str,
        source_language: Optional[str] = None,
        mime_type: str = "text/plain",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate text using Google Cloud Translation API v2
        """
        params = {"key": self.api_key}
        
        body = {
            "q": text,
            "target": target,
            "format": "html" if "html" in mime_type else "text"
        }
        
        if source_language:
            body["source"] = source_language.split("-")[0].lower()
        
        if model:
            body["model"] = model
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, params=params, data=body)
            
            if response.status_code != 200:
                logger.error(f"Translation API error: {response.text}")
                
            response.raise_for_status()
            
            result = response.json()
            translations = result.get('data', {}).get('translations', [])
            
            if translations:
                translation = translations[0]
                return {
                    "translated_text": translation.get('translatedText', text),
                    "detected_language": translation.get('detectedSourceLanguage', source_language or DEFAULT_LANGUAGE)
                }
            
            return {
                "translated_text": text,
                "detected_language": source_language or DEFAULT_LANGUAGE
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def batch_translate(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        mime_type: str = "text/plain",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate multiple texts in a single request
        
        Args:
            texts: List of texts to translate
            target_language: The language code to translate to
            source_language: The language code to translate from (auto-detect if None)
            mime_type: The MIME type of the text (text/plain or text/html)
            model: Optional model name to use for translation
            
        Returns:
            Dictionary with translated texts and detected source languages
            
        Raises:
            TranslationError: If the batch translation fails
        """
        if not texts:
            return {"translations": [], "detected_language": DEFAULT_LANGUAGE}
        
        # Filter out empty texts
        filtered_texts = [text for text in texts if text and text.strip()]
        if not filtered_texts:
            return {"translations": texts, "detected_language": DEFAULT_LANGUAGE}
            
        target_clean = target_language.split("-")[0].lower()
        if target_clean not in SUPPORTED_LANGUAGES:
            raise TranslationError(f"Unsupported target language: {target_language}")
            
        try:
            return await self._batch_translate(filtered_texts, target_clean, source_language, mime_type, model)
        except Exception as e:
            logger.error(f"Batch translation failed: {str(e)}")
            raise TranslationError(f"Failed to batch translate texts: {str(e)}")
    
    async def _batch_translate(
        self,
        texts: List[str],
        target: str,
        source_language: Optional[str] = None,
        mime_type: str = "text/plain",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Batch translate using Google Cloud Translation API v2
        """
        params = {"key": self.api_key}
        
        data = {
            "target": target,
            "format": "html" if "html" in mime_type else "text"
        }
        
        # Add multiple q parameters for each text
        for text in texts:
            data.setdefault("q", []).append(text)
            
        if source_language:
            data["source"] = source_language.split("-")[0].lower()
        
        if model:
            data["model"] = model
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, params=params, data=data)
            
            if response.status_code != 200:
                logger.error(f"Batch translation API error: {response.text}")
                
            response.raise_for_status()
            
            result = response.json()
            translations = result.get('data', {}).get('translations', [])
            
            translated_texts = []
            detected_languages = set()
            
            for i, translation in enumerate(translations):
                translated_text = translation.get('translatedText', texts[i] if i < len(texts) else '')
                detected_language = translation.get('detectedSourceLanguage', source_language or DEFAULT_LANGUAGE)
                
                translated_texts.append(translated_text)
                if detected_language:
                    detected_languages.add(detected_language)
            
            main_language = next(iter(detected_languages)) if detected_languages else (source_language or DEFAULT_LANGUAGE)
            
            return {
                "translations": translated_texts,
                "detected_language": main_language
            }

    async def get_supported_languages(self, target_language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get a list of supported languages
        
        Args:
            target_language: Optional language code to get language names in
            
        Returns:
            List of language dictionaries with code and name
            
        Raises:
            TranslationError: If the API request fails
        """
        endpoint = "https://translation.googleapis.com/language/translate/v2/languages"
        params = {"key": self.api_key}
        
        if target_language:
            params["target"] = target_language.split("-")[0].lower()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                
                result = response.json()
                languages = result.get('data', {}).get('languages', [])
                
                return [
                    {
                        "language_code": lang.get('language', ''),
                        "display_name": lang.get('name', lang.get('language', ''))
                    }
                    for lang in languages
                ]
        except Exception as e:
            logger.error(f"Failed to fetch supported languages: {str(e)}")
            raise TranslationError(f"Failed to get supported languages: {str(e)}")


# Singleton instance for the application
_translation_service = None

def get_translation_service() -> TranslationService:
    """
    Get a singleton instance of TranslationService
    
    Returns:
        TranslationService singleton instance
    """
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
