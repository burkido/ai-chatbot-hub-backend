from fastapi import APIRouter, Depends
from sqlmodel import select
from app.models.database.assistant import Assistant
from app.api.deps import SessionDep, get_current_active_superuser, CurrentUser

router = APIRouter()

@router.get("/assistants", response_model=list[Assistant])
def get_assistants(
    session: SessionDep,
    current_user: CurrentUser,
    dependencies=[Depends(get_current_active_superuser)]
):
    statement = select(Assistant)
    results = session.exec(statement).all()
    return results

@router.post("/assistants", response_model=Assistant)
def add_assistant(
    assistant: Assistant,
    session: SessionDep,
    current_user: CurrentUser, 
    dependencies=[Depends(get_current_active_superuser)]
):
    session.add(assistant)
    session.commit()
    session.refresh(assistant)
    return assistant