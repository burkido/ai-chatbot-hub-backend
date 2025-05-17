from fastapi import APIRouter, Depends, Query

from app import crud
from app.api.deps import SessionDep, CurrentUser, LanguageDep
from app.models.database.user import User
from app.models.schemas.chat import ChatRequest, ChatResponse
from app.core.llm import get_chat_service_instance, ChatService
from app.core.llm.assistant_config import ASSISTANT_TYPE_DOCTOR

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
def chat_endpoint(
    chat_request: ChatRequest,
    session: SessionDep,
    current_user: CurrentUser,
    language: LanguageDep,
    chat_service: Annotated[ChatService, Depends(get_chat_service)]
) -> ChatResponse:
    """
    Chat endpoint for processing user messages
    
    Args:
        chat_request: The chat request data
        session: Database session
        current_user: Current authenticated user
        language: User language preference
        chat_service: Chat service dependency
        
    Returns:
        Chat response with content and metadata
    """
    # If chat_request specifies an assistant_type and it's different from the current one,
    # get a new chat service instance with that assistant type
    if chat_request.assistant_type and chat_request.assistant_type.lower() != chat_service.assistant_type:
        chat_service = get_chat_service_instance("openai", chat_request.assistant_type)
        
    user = session.get(User, current_user.id)
    
    # Initialize credit status flags
    remaining_credit = user.credit
    is_credit_sufficient = True
    
    # Get response from chat service
    response, sources = chat_service.chat(
        chat_request.message,
        chat_request.namespace,
        chat_request.topic,
        chat_request.history
    )
    
    # Handle credit deduction for non-premium users
    if not user.is_premium:
        # Calculate the credit cost based on whether sources were returned
        credit_cost = 2 if sources else 1
        
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
        title = chat_service.generate_title(chat_request.message)
        
    return ChatResponse(
        content=response, 
        title=title, 
        sources=sources,
        remaining_credit=remaining_credit,
        is_credit_sufficient=is_credit_sufficient
    )