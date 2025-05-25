import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlmodel import Session

from app.core.chat_business_logic import ChatBusinessLogic, ChatProcessingResult
from app.models.schemas.chat import ChatRequest, ChatMessage
from app.models.database.user import User
from app.core.translation import TranslationError


class TestChatProcessingResult:
    def test_chat_processing_result_creation(self):
        """Test ChatProcessingResult dataclass creation"""
        result = ChatProcessingResult(
            response="Test response",
            title="Test title",
            sources=[{"source": "test"}],
            remaining_credit=10,
            is_credit_sufficient=True
        )
        
        assert result.response == "Test response"
        assert result.title == "Test title"
        assert result.sources == [{"source": "test"}]
        assert result.remaining_credit == 10
        assert result.is_credit_sufficient is True


class TestChatBusinessLogic:
    @pytest.fixture
    def business_logic(self):
        """Create ChatBusinessLogic instance for testing"""
        return ChatBusinessLogic()
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.credits = 10
        user.is_premium = False
        return user
    
    @pytest.fixture
    def mock_chat_service(self):
        """Create mock chat service for testing"""
        service = Mock()
        service.chat.return_value = ("Test response", [{"source": "test"}])
        service.generate_title.return_value = "Test Title"
        return service
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session for testing"""
        session = Mock(spec=Session)
        session.add = Mock()
        session.commit = Mock()
        return session
    
    def test_validate_language_valid(self, business_logic):
        """Test language validation with valid languages"""
        # Test supported languages
        valid_languages = ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi", "tr"]
        
        for lang in valid_languages:
            normalized = business_logic.validate_language(lang)
            assert isinstance(normalized, str)
            assert len(normalized) >= 2
    
    def test_validate_language_invalid(self, business_logic):
        """Test language validation with invalid languages"""
        with pytest.raises(ValueError, match="Language cannot be empty"):
            business_logic.validate_language("")
        
        with pytest.raises(ValueError, match="Language cannot be empty"):
            business_logic.validate_language(None)
        
        # Invalid language should fall back to English
        result = business_logic.validate_language("invalid_lang")
        assert result == "en"
    
    def test_validate_language_case_insensitive(self, business_logic):
        """Test language validation is case insensitive"""
        result1 = business_logic.validate_language("EN")
        result2 = business_logic.validate_language("en")
        result3 = business_logic.validate_language("En")
        
        assert result1 == result2 == result3 == "en"
    
    def test_calculate_credit_cost_no_translation_no_sources(self, business_logic):
        """Test credit calculation without translation and sources"""
        user = Mock()
        user.is_premium = False
        
        cost = business_logic.calculate_credit_cost(user, False, [])
        assert cost == 1  # Base cost
    
    def test_calculate_credit_cost_with_translation(self, business_logic):
        """Test credit calculation with translation"""
        user = Mock()
        user.is_premium = False
        
        cost = business_logic.calculate_credit_cost(user, True, [])
        assert cost == 2  # Base cost + translation cost
    
    def test_calculate_credit_cost_with_sources(self, business_logic):
        """Test credit calculation with sources"""
        user = Mock()
        user.is_premium = False
        
        sources = [{"source": "test1"}, {"source": "test2"}]
        cost = business_logic.calculate_credit_cost(user, False, sources)
        assert cost == 2  # Base cost + sources cost
    
    def test_calculate_credit_cost_premium_user(self, business_logic):
        """Test credit calculation for premium user"""
        user = Mock()
        user.is_premium = True
        
        # Premium users don't pay for translation
        cost = business_logic.calculate_credit_cost(user, True, [{"source": "test"}])
        assert cost == 2  # Base cost + sources cost (no translation cost)
    
    def test_deduct_credits_sufficient(self, business_logic, mock_session):
        """Test credit deduction with sufficient credits"""
        user = Mock()
        user.credits = 10
        
        remaining = business_logic.deduct_credits(user, mock_session, 5)
        
        assert user.credits == 5
        assert remaining == 5
        mock_session.add.assert_called_once_with(user)
        mock_session.commit.assert_called_once()
    
    def test_deduct_credits_insufficient(self, business_logic, mock_session):
        """Test credit deduction with insufficient credits"""
        user = Mock()
        user.credits = 3
        
        with pytest.raises(ValueError, match="Insufficient credits"):
            business_logic.deduct_credits(user, mock_session, 5)
    
    def test_deduct_credits_zero_cost(self, business_logic, mock_session):
        """Test credit deduction with zero cost"""
        user = Mock()
        user.credits = 10
        
        remaining = business_logic.deduct_credits(user, mock_session, 0)
        
        assert user.credits == 10  # No change
        assert remaining == 10
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
    
    @patch('app.core.chat_business_logic.TranslationService')
    async def test_handle_translation_needed(self, mock_translation_service, business_logic):
        """Test translation handling when translation is needed"""
        # Mock translation service
        mock_service_instance = Mock()
        mock_service_instance.translate = AsyncMock(return_value={
            "translated_text": "Hello world",
            "detected_source_language": "es"
        })
        mock_translation_service.return_value = mock_service_instance
        
        result = await business_logic.handle_translation("Hola mundo", "en", "es")
        
        assert result == "Hello world"
        mock_service_instance.translate.assert_called_once_with("Hola mundo", "en")
    
    @patch('app.core.chat_business_logic.TranslationService')
    async def test_handle_translation_not_needed(self, mock_translation_service, business_logic):
        """Test translation handling when translation is not needed"""
        result = await business_logic.handle_translation("Hello world", "en", "en")
        
        assert result == "Hello world"
        mock_translation_service.assert_not_called()
    
    @patch('app.core.chat_business_logic.TranslationService')
    async def test_handle_translation_error(self, mock_translation_service, business_logic):
        """Test translation handling with translation error"""
        # Mock translation service to raise error
        mock_service_instance = Mock()
        mock_service_instance.translate = AsyncMock(side_effect=TranslationError("Translation failed", "translate"))
        mock_translation_service.return_value = mock_service_instance
        
        with pytest.raises(TranslationError):
            await business_logic.handle_translation("Hola mundo", "en", "es")
    
    async def test_process_chat_request_success(self, business_logic, mock_user, mock_chat_service, mock_session):
        """Test successful chat request processing"""
        chat_request = ChatRequest(
            message="Hello",
            language="en",
            history=[],
            namespace="test",
            topic="general"
        )
        
        with patch.object(business_logic, 'handle_translation', return_value="Hello"):
            result = await business_logic.process_chat_request(
                chat_request, mock_chat_service, mock_session, mock_user
            )
        
        assert isinstance(result, ChatProcessingResult)
        assert result.response == "Test response"
        assert result.title == "Test Title"
        assert result.sources == [{"source": "test"}]
        assert result.is_credit_sufficient is True
        assert isinstance(result.remaining_credit, int)
    
    async def test_process_chat_request_insufficient_credits(self, business_logic, mock_chat_service, mock_session):
        """Test chat request processing with insufficient credits"""
        # User with insufficient credits
        poor_user = Mock(spec=User)
        poor_user.id = "poor-user"
        poor_user.credits = 0
        poor_user.is_premium = False
        
        chat_request = ChatRequest(
            message="Hello",
            language="en",
            history=[],
            namespace="test",
            topic="general"
        )
        
        with patch.object(business_logic, 'handle_translation', return_value="Hello"):
            with pytest.raises(ValueError, match="Insufficient credits"):
                await business_logic.process_chat_request(
                    chat_request, mock_chat_service, mock_session, poor_user
                )
    
    async def test_process_chat_request_with_translation(self, business_logic, mock_user, mock_chat_service, mock_session):
        """Test chat request processing with translation"""
        chat_request = ChatRequest(
            message="Hola",
            language="en",
            history=[],
            namespace="test",
            topic="general"
        )
        
        with patch.object(business_logic, 'validate_language', return_value="es"):
            with patch.object(business_logic, 'handle_translation', return_value="Hello"):
                result = await business_logic.process_chat_request(
                    chat_request, mock_chat_service, mock_session, mock_user
                )
        
        assert isinstance(result, ChatProcessingResult)
        assert result.response == "Test response"
        # Credits should be deducted for translation
        assert mock_user.credits < 10
