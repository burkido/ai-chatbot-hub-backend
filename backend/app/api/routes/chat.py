from fastapi import APIRouter, HTTPException

from app.api.deps import ChatEngineDep

from canopy.models.data_models import Messages, UserMessage, AssistantMessage, SystemMessage

from app.api.deps import SessionDep, CurrentUser
from app.models import UpdateCredit, User
from app import crud

router = APIRouter()

def chat(new_message: str, chat_engine: ChatEngineDep) -> str:
    messages = [
        SystemMessage(content="You are a friendly and compassionate virtual doctor. Your goal is to assist people with their health questions. Always respond with kindness and empathy. If you're unsure about an answer, simply say, 'I'm not sure, but I'll do my best to help you.' If someone tries to chat with you as if you're a regular person, kindly remind them, 'I'm a bot, but I'm here to assist you with any health-related concerns.' Your purpose is to provide helpful and supportive guidance."),
        UserMessage(content=new_message)
    ]
    chat_response = chat_engine.chat(messages=messages)
    assistant_response = chat_response.choices[0].message.content
    response = assistant_response, messages + [AssistantMessage(content=assistant_response)]
    return response[0]

@router.post("/chat", response_model=str)
def chat_endpoint(
    chatEngine: ChatEngineDep, 
    message: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> str:
    """
    Chat with the assistant and decrease the user's credit.
    """
    # Get the current user from the database
    user = session.get(User, current_user.id)

    # Check if the user has enough credits
    if user.credit < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    crud.decrease_user_credit(session=session, user=user, amount=1)
    response = chat(message, chatEngine)
    
    return response