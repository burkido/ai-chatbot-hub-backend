import pytest
from unittest.mock import Mock, patch
import httpx

from app.core.translation import TranslationService, TranslationError


class TestTranslationError:
    def test_translation_error_basic(self):
        """Test basic TranslationError creation"""
        error = TranslationError("Test error", "test_operation")
        
        assert str(error) == "Translation Error (test_operation): Test error"
        assert error.operation == "test_operation"
        assert error.details is None
    
    def test_translation_error_with_details(self):
        """Test TranslationError with details"""
        details = {"code": 400, "message": "Bad request"}
        error = TranslationError("Test error", "test_operation", details)
        
        assert error.details == details
        assert str(error) == "Translation Error (test_operation): Test error"


class TestTranslationService:
    def test_translation_service_singleton(self):
        """Test that TranslationService follows singleton pattern"""
        service1 = TranslationService()
        service2 = TranslationService()
        
        assert service1 is service2
    
    def test_validate_language_code_valid(self):
        """Test language code validation with valid codes"""
        service = TranslationService()
        
        # Test valid language codes
        valid_codes = ["en", "es", "fr", "de", "zh-CN", "pt-BR"]
        for code in valid_codes:
            normalized = service._validate_language_code(code)
            assert isinstance(normalized, str)
            assert len(normalized) >= 2
    
    def test_validate_language_code_invalid(self):
        """Test language code validation with invalid codes"""
        service = TranslationService()
        
        with pytest.raises(TranslationError):
            service._validate_language_code("")
        
        with pytest.raises(TranslationError):
            service._validate_language_code("invalid_lang_code")
        
        with pytest.raises(TranslationError):
            service._validate_language_code(None)
    
    def test_validate_text_empty(self):
        """Test text validation with empty text"""
        service = TranslationService()
        
        with pytest.raises(TranslationError):
            service._validate_text("")
        
        with pytest.raises(TranslationError):
            service._validate_text("   ")
        
        with pytest.raises(TranslationError):
            service._validate_text(None)
    
    def test_validate_text_too_long(self):
        """Test text validation with too long text"""
        service = TranslationService()
        
        # Text longer than MAX_TEXT_LENGTH
        long_text = "a" * 10001
        with pytest.raises(TranslationError):
            service._validate_text(long_text)
    
    @patch('httpx.AsyncClient.post')
    async def test_translate_success(self, mock_post):
        """Test successful translation"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "translations": [
                    {
                        "translatedText": "Hola mundo",
                        "detectedSourceLanguage": "en"
                    }
                ]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value.__aenter__.return_value = mock_response
        
        service = TranslationService()
        result = await service.translate("Hello world", "es")
        
        assert "translated_text" in result
        assert result["translated_text"] == "Hola mundo"
        assert result["detected_source_language"] == "en"
    
    @patch('httpx.AsyncClient.post')
    async def test_translate_api_error(self, mock_post):
        """Test translation with API error"""
        # Mock API error response
        mock_post.side_effect = httpx.HTTPError("API Error")
        
        service = TranslationService()
        with pytest.raises(TranslationError):
            await service.translate("Hello world", "es")
    
    def test_get_supported_languages_cache(self):
        """Test that supported languages are cached"""
        service = TranslationService()
        
        # Clear cache first
        service._supported_languages_cache = None
        
        # Mock the supported languages
        test_languages = ["en", "es", "fr", "de"]
        service._supported_languages_cache = test_languages
        
        languages = service.get_supported_languages()
        assert languages == test_languages
    
    async def test_batch_translate_empty_list(self):
        """Test batch translation with empty list"""
        service = TranslationService()
        
        with pytest.raises(TranslationError):
            await service.batch_translate([], "es")
    
    async def test_batch_translate_too_many_texts(self):
        """Test batch translation with too many texts"""
        service = TranslationService()
        
        # Create list with more than MAX_BATCH_SIZE texts
        many_texts = ["text"] * 101
        
        with pytest.raises(TranslationError):
            await service.batch_translate(many_texts, "es")
