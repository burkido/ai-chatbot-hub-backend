from fastapi import APIRouter, Depends, Query

from app import crud
from app.api.deps import (
    SessionDep, CurrentUser
)
from app.models.database.user import User
from app.models.schemas.chat import ChatRequest, ChatResponse, ChatMessage
from app.core.llm import get_chat_service_instance, ChatService
from app.core.llm.assistant_config import ASSISTANT_TYPE_DOCTOR
from app.core.translation import get_translation_service, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

from typing import Annotated, Optional

router = APIRouter()

def get_chat_service(
    assistant_type: Optional[str] = Query(None, description="Type of assistant to use")
) -> ChatService:
    """
    Dependency for getting ChatService with the specified assistant type
    
    This function returns a singleton instance of ChatService for the specified assistant type,
    ensuring that only one instance exists throughout the application's lifetime for each type.
    
    Args:
        assistant_type: The type of assistant to use (defaults to None, which will use DOCTOR)
    
    Returns:
        ChatService singleton instance
    """
    # Use the doctor assistant type as default if none specified
    actual_type = assistant_type or ASSISTANT_TYPE_DOCTOR
    return get_chat_service_instance("openai", actual_type)


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(
    chat_request: ChatRequest,
    session: SessionDep,
    current_user: CurrentUser,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """
    Chat endpoint for processing user messages
    
    Args:
        chat_request: The chat request data
        session: Database session
        current_user: Current authenticated user
        chat_service: Chat service dependency
        
    Returns:
        Chat response with content and metadata
    """
    # Get the language from chat_request
    original_user_language = chat_request.language or DEFAULT_LANGUAGE
    user_language = original_user_language
    
    # Validate language code is supported
    if user_language not in SUPPORTED_LANGUAGES:
        user_language = DEFAULT_LANGUAGE
    
    # If chat_request specifies an assistant_type and it's different from the current one,
    # get a new chat service instance with that assistant type
    if chat_request.assistant_type and chat_request.assistant_type.lower() != chat_service.assistant_type:
        chat_service = get_chat_service_instance("openai", chat_request.assistant_type)
        
    user = session.get(User, current_user.id)
    
    # Initialize credit status flags
    remaining_credit = user.credit
    is_credit_sufficient = True
    
    # Store original message
    original_message = chat_request.message
    translation_service = None
    
    # Translate user message to English if the original language is not English
    # This ensures we always translate unsupported languages to English
    if original_user_language != DEFAULT_LANGUAGE:
        print(f"Translating user message from {original_user_language} to {DEFAULT_LANGUAGE}")
        translation_service = get_translation_service()
        translation_result = await translation_service.translate(
            chat_request.message, 
            target_language=DEFAULT_LANGUAGE,
            source_language=original_user_language if original_user_language in SUPPORTED_LANGUAGES else None
        )
        print(f"Translated message: {translation_result['translated_text']}")
        translated_message = translation_result["translated_text"]
    else:
        translated_message = original_message
    
    # Print the query that will be sent to Pinecone
    print(f"Query to Pinecone - Text (in English): {translated_message}")
    print(f"Query to Pinecone - Namespace: {chat_request.namespace}")
    print(f"Query to Pinecone - Topic: {chat_request.topic}")
    print(f"Query to Pinecone - Search Language: {DEFAULT_LANGUAGE}")  # Always English for search
    print(f"Query to Pinecone - User's Original Language: {original_user_language}")  # Original user language
    print(f"Query to Pinecone - User's Validated Language: {user_language}")     # Validated user language
    
    # Get response from chat service using original message for LLM and translated message for search
    response, sources = chat_service.chat(
        original_message,  # Original message in user's language for LLM
        chat_request.namespace,
        chat_request.topic,
        chat_request.history,
        language=user_language,
        search_message=translated_message  # Translated message for Pinecone search
    )
    
    # No need to translate the response back - LLM naturally responds in user's language
    translated_response = response
    
    # Handle credit deduction for non-premium users
    if not user.is_premium:
        # Calculate the credit cost based on whether sources were returned and translation
        # Add extra credit for translation of the latest message only
        base_cost = 2 if sources else 1
        translation_cost = 1 if original_user_language != DEFAULT_LANGUAGE else 0
        credit_cost = base_cost + translation_cost
        
        if user.credit < credit_cost:
            # Mark as insufficient credit
            is_credit_sufficient = False
            
            # Decrease whatever credit is available if not already 0
            if user.credit > 0:
                crud.decrease_user_credit(session=session, user=user, amount=user.credit)
                remaining_credit = 0
        else:
            # User has sufficient credit, decrease the full amount
            crud.decrease_user_credit(session=session, user=user, amount=credit_cost)
            remaining_credit = user.credit
    
    # Generate title for new conversations
    title = None
    if len(chat_request.history) == 0:
        # Generate title using original message in user's language
        title = chat_service.generate_title(original_message)
        
    return ChatResponse(
        content=translated_response, 
        title=title, 
        sources=sources,
        remaining_credit=remaining_credit,
        is_credit_sufficient=is_credit_sufficient
    )