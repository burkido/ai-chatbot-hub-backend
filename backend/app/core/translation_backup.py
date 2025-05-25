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
        """
        if not text:
            return {"language": DEFAULT_LANGUAGE, "confidence": 1.0}
        
        return await self._detect_language(text)
    
    async def _detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect language using Google Translate API v2
        """
        endpoint = "https://translation.googleapis.com/language/translate/v2/detect"
        
        # For API v2, the key should be in the URL parameters
        params = {
            "key": self.api_key
        }
        
        # Set up request body as form data
        data = {
            "q": text
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    params=params,
                    data=data  # Send as form data instead of JSON
                )
                # Log status code for debugging
                logger.debug(f"Language detection API response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"Language detection API error: {response.text}")
                    
                response.raise_for_status()
                
                data = response.json()
                detections = data.get('data', {}).get('detections', [[]])
                
                if detections and detections[0]:
                    detection = detections[0][0]
                    return {
                        "language": detection.get('language', DEFAULT_LANGUAGE),
                        "confidence": detection.get('confidence', 0.0)
                    }
                else:
                    return {"language": DEFAULT_LANGUAGE, "confidence": 0.0}
                    
        except (httpx.HTTPError, KeyError) as e:
            logger.error(f"Language detection error: {str(e)}")
            raise
    
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
        """
        # If text is empty, no translation needed
        if not text:
            return {"translated_text": text, "detected_language": source_language or DEFAULT_LANGUAGE}
            
        # If target is default language and source isn't specified or is already default,
        # no translation needed
        if source_language == DEFAULT_LANGUAGE:
            return {"translated_text": text, "detected_language": source_language or DEFAULT_LANGUAGE}
            
        # Clean up language codes to match Google's format
        target = target_language.split("-")[0].lower()
        
        # Simply translate from source to target language directly
        return await self._translate(text, target, source_language, mime_type, model)
    
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
        
        Args:
            text: The text to translate
            target: The target language code
            source_language: The source language code (optional)
            mime_type: The MIME type of the text
            model: The translation model to use (optional)
            
        Returns:
            Dictionary with translated text and detected source language
        """
        # For API v2, the key should be in the URL parameters
        params = {
            "key": self.api_key
        }
        
        # Create proper request body as documented in Google Translate API docs
        body = {
            "q": text,
            "target": target
        }
        
        # Handle format correctly - API only accepts 'text' or 'html', not 'plain'
        if "html" in mime_type:
            body["format"] = "html"
        else:
            body["format"] = "text"  # Use 'text' instead of 'plain'
        
        if source_language:
            body["source"] = source_language.split("-")[0].lower()
        
        # NMT is now the default model, but we can still specify if needed
        if model:
            body["model"] = model
            
        # Log request details for debugging (excluding API key)
        logger.debug(f"Translation request to {self.base_url} with target={target}, format={body['format']}")
        
        try:
            async with httpx.AsyncClient() as client:
                # According to Google API docs, for v2 API we should send form data, not JSON
                logger.debug(f"Sending translation request with body: {body}")
                response = await client.post(
                    self.base_url,
                    params=params,
                    data=body  # Send as form data instead of JSON
                )
                # Log status code for debugging
                logger.debug(f"Translation API response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"Translation API error: {response.text}")
                    logger.error(f"Request body was: {body}")
                    
                response.raise_for_status()
                
                data = response.json()
                translations = data.get('data', {}).get('translations', [])
                
                if translations:
                    translation = translations[0]
                    translated_text = translation.get('translatedText', text)
                    detected_language = translation.get('detectedSourceLanguage', source_language or DEFAULT_LANGUAGE)
                    
                    return {
                        "translated_text": translated_text,
                        "detected_language": detected_language
                    }
                else:
                    return {
                        "translated_text": text,
                        "detected_language": source_language or DEFAULT_LANGUAGE
                    }
                    
        except (httpx.HTTPError, KeyError) as e:
            logger.error(f"Translation error: {str(e)}")
            raise

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
        """
        if not texts:
            return {"translations": [], "detected_language": DEFAULT_LANGUAGE}
            
        # Skip translation if target is default language
        if target_language == DEFAULT_LANGUAGE and all(not text for text in texts):
            return {
                "translations": texts,
                "detected_language": DEFAULT_LANGUAGE
            }
            
        # Clean up language codes to match Google's format
        target = target_language.split("-")[0].lower()
        
        return await self._batch_translate(texts, target, source_language, mime_type, model)
    
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
        
        Args:
            texts: List of texts to translate
            target: The target language code
            source_language: The source language code (optional)
            mime_type: The MIME type of the text
            model: The translation model to use (optional)
            
        Returns:
            Dictionary with translated texts and detected source languages
        """
        # For API v2, the key should be in the URL parameters
        params = {
            "key": self.api_key
        }
        
        # For multiple texts in v2 API, we need to create multiple q parameters
        # Rather than sending as JSON array
        data = {
            "target": target
        }
        
        # Handle format correctly - API only accepts 'text' or 'html', not 'plain'
        if "html" in mime_type:
            data["format"] = "html"
        else:
            data["format"] = "text"  # Use 'text' instead of 'plain'
        
        # Add multiple q parameters for each text
        for text in texts:
            data.setdefault("q", []).append(text)
            
        if source_language:
            data["source"] = source_language.split("-")[0].lower()
        
        # NMT is now the default model, but we can still specify if needed
        if model:
            data["model"] = model
            
        # Log request details for debugging (excluding API key)
        logger.debug(f"Batch translation request to {self.base_url} with target={target}, format={data['format']}, {len(texts)} texts")
        
        try:
            async with httpx.AsyncClient() as client:
                # According to Google API docs, for v2 API we should send form data, not JSON
                logger.debug(f"Sending batch translation request with body: {data}")
                response = await client.post(
                    self.base_url,
                    params=params,
                    data=data  # Send as form data instead of JSON
                )
                # Log status code for debugging
                logger.debug(f"Translation API response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"Translation API error: {response.text}")
                    logger.error(f"Request body was: {data}")
                    
                response.raise_for_status()
                
                data = response.json()
                translations = data.get('data', {}).get('translations', [])
                
                translated_texts = []
                detected_languages = set()
                
                for i, translation in enumerate(translations):
                    translated_text = translation.get('translatedText', texts[i] if i < len(texts) else '')
                    detected_language = translation.get('detectedSourceLanguage', source_language or DEFAULT_LANGUAGE)
                    
                    translated_texts.append(translated_text)
                    if detected_language:
                        detected_languages.add(detected_language)
                
                # Most common detected language, or the provided source language, or default
                main_language = next(iter(detected_languages)) if detected_languages else (source_language or DEFAULT_LANGUAGE)
                
                return {
                    "translations": translated_texts,
                    "detected_language": main_language
                }
                    
        except (httpx.HTTPError, KeyError) as e:
            logger.error(f"Batch translation error: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def get_supported_languages(self, target_language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get a list of supported languages
        
        Args:
            target_language: Optional language code to get language names in
            
        Returns:
            List of language dictionaries with code and name
        """
        endpoint = "https://translation.googleapis.com/language/translate/v2/languages"
        
        # Set up query parameters (GET request, so all parameters go in URL)
        params = {"key": self.api_key}
        
        if target_language:
            params["target"] = target_language.split("-")[0].lower()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    params=params
                )
                response.raise_for_status()
                
                data = response.json()
                languages = data.get('data', {}).get('languages', [])
                
                return [
                    {
                        "language_code": lang.get('language', ''),
                        "display_name": lang.get('name', lang.get('language', ''))
                    }
                    for lang in languages
                ]
                
        except (httpx.HTTPError, KeyError) as e:
            logger.error(f"Error fetching supported languages: {str(e)}")
            raise


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
