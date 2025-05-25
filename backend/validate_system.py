#!/usr/bin/env python3
"""
Simple validation script to test our refactored components
"""
import sys
import asyncio
from unittest.mock import Mock

# Add the backend app to the path
sys.path.append('/Users/burak/Developer/Backend/medicine-ai/full-stack-fastapi-template/backend')

def test_translation_service():
    """Test TranslationService and TranslationError"""
    print("Testing TranslationService...")
    
    from app.core.translation import TranslationService, TranslationError
    
    # Test TranslationError
    error = TranslationError("Test error", "test_operation")
    assert str(error) == "Translation Error (test_operation): Test error"
    print("✓ TranslationError works correctly")
    
    # Test TranslationService singleton
    service1 = TranslationService()
    service2 = TranslationService()
    assert service1 is service2
    print("✓ TranslationService singleton pattern works")
    
    # Test language validation
    assert service1.is_valid_language("en")
    assert service1.is_valid_language("tr")
    assert not service1.is_valid_language("invalid")
    print("✓ Language validation works")

def test_assistant_config():
    """Test AssistantConfigService"""
    print("\nTesting AssistantConfigService...")
    
    from app.core.llm.assistant_config import AssistantConfigService
    
    # Test singleton
    service1 = AssistantConfigService()
    service2 = AssistantConfigService()
    assert service1 is service2
    print("✓ AssistantConfigService singleton pattern works")
    
    # Test built-in configs
    configs = service1.get_all_configs()
    assert len(configs) > 0
    print(f"✓ Found {len(configs)} built-in assistant configurations")
    
    # Test getting specific config
    general_config = service1.get_config("general")
    assert general_config is not None
    print("✓ General assistant config retrieval works")

async def test_chat_business_logic():
    """Test ChatBusinessLogic"""
    print("\nTesting ChatBusinessLogic...")
    
    from app.core.chat_business_logic import ChatBusinessLogic, ChatProcessingResult
    from app.models.schemas.chat import ChatRequest, ChatMessage
    
    # Create a mock user
    mock_user = Mock()
    mock_user.credit = 10
    mock_user.id = "test-user-id"
    
    # Create a mock session
    mock_session = Mock()
    
    # Create a mock chat request
    chat_request = ChatRequest(
        history=[ChatMessage(role="user", content="Hello")],
        message="How are you?",
        topic="Test Chat",
        namespace="test",
        language="en"
    )
    
    # Test credit calculation
    business_logic = ChatBusinessLogic()
    required_credits = business_logic.calculate_required_credits(chat_request)
    assert required_credits == 1
    print("✓ Credit calculation works")
    
    # Test language validation
    assert business_logic.validate_language("en")
    assert business_logic.validate_language("tr")
    assert not business_logic.validate_language("invalid")
    print("✓ Language validation in business logic works")
    
    # Test ChatProcessingResult
    result = ChatProcessingResult(
        content="Test response",
        remaining_credit=9,
        is_credit_sufficient=True
    )
    assert result.content == "Test response"
    assert result.remaining_credit == 9
    assert result.is_credit_sufficient
    print("✓ ChatProcessingResult dataclass works")

def main():
    """Run all tests"""
    print("=" * 60)
    print("VALIDATING REFACTORED CHAT SYSTEM COMPONENTS")
    print("=" * 60)
    
    try:
        test_translation_service()
        test_assistant_config()
        asyncio.run(test_chat_business_logic())
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! The refactored system is working correctly.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
