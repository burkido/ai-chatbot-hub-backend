from fastapi import APIRouter
from app.api.deps import ChatEngineDep
from canopy.models.data_models import Messages, UserMessage, AssistantMessage, SystemMessage
from typing import Tuple, List

router = APIRouter()

def chat(new_message: str, chat_engine: ChatEngineDep) -> Tuple[str, Messages]:
    messages = [
        SystemMessage(content="You are a friendly and compassionate virtual doctor. Your goal is to assist people with their health questions. Always respond with kindness and empathy. If you're unsure about an answer, simply say, 'I'm not sure, but I'll do my best to help you.' If someone tries to chat with you as if you're a regular person, kindly remind them, 'I'm a bot, but I'm here to assist you with any health-related concerns.' Your purpose is to provide helpful and supportive guidance."),
        UserMessage(content=new_message)
    ]
    response = chat_engine.chat(messages=messages)
    assistant_response = response.choices[0].message.content
    return assistant_response, messages + [AssistantMessage(content=assistant_response)]

@router.post("/chat", response_model=str)
def chat_endpoint(chatEngine: ChatEngineDep, message: str) -> str:
    msg = chat(message, chatEngine)
