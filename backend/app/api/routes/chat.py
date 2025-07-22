from fastapi import APIRouter, Depends, Query, HTTPException, status
import logging
from datetime import datetime, timezone
from functools import lru_cache

from app import crud
from app.api.deps import (
    SessionDep, CurrentUser
)
from app.models.database.user import User
from app.models.schemas.chat import ChatRequest, ChatResponse, ChatMessage
from app.core.llm import get_chat_service_instance, ChatService
from app.core.llm.assistant_config import ASSISTANT_TYPE_DOCTOR
from app.core.translation import TranslationError
from app.core.chat_business_logic import ChatBusinessLogic

from typing import Annotated, Optional

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize business logic
chat_business_logic = ChatBusinessLogic()

@lru_cache(maxsize=10)
def get_chat_service_cached(
    provider_name: str = "openai",
    assistant_type: str = ASSISTANT_TYPE_DOCTOR
) -> ChatService:
    """
    Cached factory for ChatService instances
    
    This function creates and caches ChatService instances using FastAPI's built-in
    lru_cache decorator. This provides better performance than a singleton while
    avoiding the pitfalls of global state.
    
    Args:
        provider_name: The LLM provider to use
        assistant_type: The type of assistant to use
    
    Returns:
        Cached ChatService instance
    """
    return get_chat_service_instance(provider_name, assistant_type)

def get_chat_service(
    assistant_type: Optional[str] = Query(None, description="Type of assistant to use")
) -> ChatService:
    """
    Dependency for getting ChatService with the specified assistant type
    
    This function returns a cached instance of ChatService for the specified assistant type,
    using FastAPI's dependency injection system with lru_cache for efficient caching.
    
    Args:
        assistant_type: The type of assistant to use (defaults to None, which will use DOCTOR)
    
    Returns:
        ChatService cached instance
    """
    # Use the doctor assistant type as default if none specified
    actual_type = assistant_type or ASSISTANT_TYPE_DOCTOR
    return get_chat_service_cached("openai", actual_type)


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
    try:
        # If chat_request specifies an assistant_type and it's different from the current one,
        # get a new chat service instance with that assistant type
        if chat_request.assistant_type and chat_request.assistant_type.lower() != chat_service.assistant_type:
            try:
                chat_service = get_chat_service_instance("openai", chat_request.assistant_type)
            except ValueError as e:
                logger.error(f"Invalid assistant type: {chat_request.assistant_type}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Invalid assistant type: {chat_request.assistant_type}"
                )
        
        # Get user from database
        user = session.get(User, current_user.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update the user's updated_at timestamp
        user.updated_at = datetime.now(timezone.utc)
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # Process chat request using business logic
        result = await chat_business_logic.process_chat_request(
            chat_request=chat_request,
            chat_service=chat_service,
            session=session,
            user=user
        )
        
        logger.info(f"Chat request processed successfully for user {user.id}")
        
        return ChatResponse(
            content=result.response, 
            title=result.title, 
            sources=result.sources,
            remaining_credit=result.remaining_credit,
            is_credit_sufficient=result.is_credit_sufficient
        )
        
    except TranslationError as e:
        logger.error(f"Translation error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Translation service error: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )