"""
Business logic services for chat functionality
"""
import logging
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass

from app import crud
from app.models.database.user import User
from app.models.schemas.chat import ChatRequest, ChatMessage
from app.core.llm import ChatService
from app.core.translation import get_translation_service, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, TranslationError

logger = logging.getLogger(__name__)


@dataclass
class ChatProcessingResult:
    """Result of chat processing"""
    response: str
    sources: List[Dict[str, Any]]
    title: Optional[str]
    remaining_credit: int
    is_credit_sufficient: bool
    translated_message: str
    user_language: str


class ChatBusinessLogic:
    """Business logic for chat operations"""
    
    def __init__(self):
        self.translation_service = get_translation_service()
    
    def validate_language(self, language: Optional[str]) -> str:
        """
        Validate and normalize language code
        
        Args:
            language: Language code to validate
            
        Returns:
            Validated language code
        """
        if not language:
            return DEFAULT_LANGUAGE
            
        normalized = language.lower().split('-')[0]
        if normalized not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language requested: {language}, falling back to {DEFAULT_LANGUAGE}")
            return DEFAULT_LANGUAGE
            
        return normalized
    
    async def translate_if_needed(
        self, 
        message: str, 
        original_language: str, 
        target_language: str = DEFAULT_LANGUAGE
    ) -> str:
        """
        Translate message if needed
        
        Args:
            message: Message to translate
            original_language: Original language of the message
            target_language: Target language for translation
            
        Returns:
            Translated message or original if no translation needed
            
        Raises:
            TranslationError: If translation fails
        """
        if original_language == target_language:
            return message
            
        try:
            translation_result = await self.translation_service.translate(
                message, 
                target_language=target_language,
                source_language=original_language if original_language in SUPPORTED_LANGUAGES else None
            )
            return translation_result["translated_text"]
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            raise TranslationError(f"Failed to translate message: {str(e)}")
    
    def calculate_credit_cost(
        self, 
        has_sources: bool, 
    ) -> int:
        """
        Calculate credit cost for a chat request
        
        Args:
            has_sources: Whether the response includes sources
            needs_translation: Whether translation was needed (not used for cost calculation)
            
        Returns:
            Credit cost
        """
        base_cost = 2 if has_sources else 1
        return base_cost
    
    def process_credit_deduction(
        self, 
        session, 
        user: User, 
        credit_cost: int
    ) -> Tuple[int, bool]:
        """
        Process credit deduction for non-premium users
        
        Args:
            session: Database session
            user: User object
            credit_cost: Required credit cost
            
        Returns:
            Tuple of (remaining_credit, is_credit_sufficient)
        """
        # Premium users have unlimited credits
        if user.is_premium:
            return user.credit, True
        
        # Determine how much credit to deduct (partial or full)
        deduction_amount = min(user.credit, credit_cost)
        is_credit_sufficient = user.credit >= credit_cost
        
        # Only deduct if user has any credits available
        if deduction_amount > 0:
            updated_user = crud.decrease_user_credit(
                session=session, 
                user=user, 
                amount=deduction_amount
            )
            remaining_credit = updated_user.credit
        else:
            remaining_credit = user.credit
        
        return remaining_credit, is_credit_sufficient
    
    async def process_chat_request(
        self,
        chat_request: ChatRequest,
        chat_service: ChatService,
        session,
        user: User
    ) -> ChatProcessingResult:
        """
        Process a complete chat request
        
        Args:
            chat_request: The chat request data
            chat_service: Chat service instance
            session: Database session
            user: Current user
            
        Returns:
            ChatProcessingResult with all response data
        """
        # Validate and normalize language
        original_user_language = chat_request.language or DEFAULT_LANGUAGE
        user_language = self.validate_language(original_user_language)
        
        # Store original message
        original_message = chat_request.message
        
        # Translate user message to English if needed for vector search
        try:
            translated_message = await self.translate_if_needed(
                original_message, 
                original_user_language, 
                DEFAULT_LANGUAGE
            )
        except TranslationError:
            # Fall back to original message if translation fails
            logger.warning("Translation failed, using original message for search")
            translated_message = original_message
        
        # Get response from chat service
        try:
            response, sources = chat_service.chat(
                original_message,  # Original message in user's language for LLM
                chat_request.namespace,
                chat_request.topic,
                chat_request.history,
                language=user_language,
                search_message=translated_message  # Translated message for search
            )
        except Exception as e:
            logger.error(f"Chat service error: {str(e)}")
            raise Exception(f"Chat processing failed: {str(e)}")
        
        # Calculate credit cost and process deduction
        credit_cost = self.calculate_credit_cost(bool(sources))
        remaining_credit, is_credit_sufficient = self.process_credit_deduction(session, user, credit_cost)
        
        # Generate title for new conversations
        title = None
        if len(chat_request.history) == 0:
            try:
                title = chat_service.generate_title(original_message)
            except Exception as e:
                logger.warning(f"Title generation failed: {str(e)}")
                title = "New Conversation"
        
        return ChatProcessingResult(
            response=response,
            sources=sources,
            title=title,
            remaining_credit=remaining_credit,
            is_credit_sufficient=is_credit_sufficient,
            translated_message=translated_message,
            user_language=user_language
        )
