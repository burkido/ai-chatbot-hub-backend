from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, func

from app.api.deps import SessionDep, CurrentUser, get_current_active_superuser, ApplicationDep
from app.models.database.feedback import Feedback
from app.models.schemas.feedback import FeedbackCreate, FeedbackResponse, FeedbacksResponse, FeedbackDelete, FeedbackUpdate

router = APIRouter()


@router.post("/", response_model=FeedbackResponse)
async def create_feedback(
    feedback_in: FeedbackCreate,
    session: SessionDep,
    current_user: CurrentUser,
    application: ApplicationDep,
) -> Any:
    """
    Create new feedback.
    Any authenticated user can submit feedback.
    """
    # Create new feedback object
    db_feedback = Feedback(
        user_id=current_user.id,
        application_id=application.id,
        content=feedback_in.content
    )
    
    # Add to database
    session.add(db_feedback)
    session.commit()
    session.refresh(db_feedback)
    
    return db_feedback


@router.post("/public/delete-account", response_model=FeedbackResponse)
async def create_delete_account_request(
    feedback_in: FeedbackCreate,
    session: SessionDep,
    application: ApplicationDep,
) -> Any:
    """
    Create a public delete account request.
    No authentication required - for anonymous users to request account deletion.
    """
    # Create new feedback object for delete account request without user_id
    db_feedback = Feedback(
        user_id=None,  # Anonymous request, no user ID
        application_id=application.id,
        content=feedback_in.content
    )
    
    # Add to database
    session.add(db_feedback)
    session.commit()
    session.refresh(db_feedback)
    
    return db_feedback


@router.get("/", response_model=FeedbacksResponse, dependencies=[Depends(get_current_active_superuser)])
async def read_feedbacks(
    session: SessionDep,
    application: ApplicationDep = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve feedbacks.
    Only superusers can see all feedback.
    If application is provided, only feedback for that application is returned.
    """
    # Base query
    base_query = select(Feedback)
    
    # Filter by application if provided
    if application:
        base_query = base_query.where(Feedback.application_id == application.id)
    
    # Get total count
    count_statement = select(func.count(Feedback.id))
    if application:
        count_statement = count_statement.where(Feedback.application_id == application.id)
    total_count = session.exec(count_statement).one()
    
    # Get paginated feedbacks
    statement = base_query.offset(skip).limit(limit).order_by(Feedback.created_at.desc())
    feedbacks = session.exec(statement).all()
    
    return FeedbacksResponse(data=feedbacks, count=total_count)


@router.patch("/{feedback_id}", response_model=FeedbackResponse, dependencies=[Depends(get_current_active_superuser)])
async def update_feedback(
    feedback_id: UUID,
    feedback_in: FeedbackUpdate,
    session: SessionDep,
    application: ApplicationDep = None,
) -> Any:
    """
    Update feedback status.
    Only superusers can update feedback status.
    If application is provided, only feedback for that application can be updated.
    """
    # Find the feedback by ID
    db_feedback = session.get(Feedback, feedback_id)
    
    # Check if feedback exists
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Validate application if provided
    if application and db_feedback.application_id != application.id:
        raise HTTPException(status_code=404, detail="Feedback not found for this application")
    
    # Update fields if provided
    feedback_data = feedback_in.dict(exclude_unset=True)
    for field, value in feedback_data.items():
        setattr(db_feedback, field, value)
    
    session.add(db_feedback)
    session.commit()
    session.refresh(db_feedback)
    
    return db_feedback


@router.delete("/{feedback_id}", response_model=FeedbackDelete, dependencies=[Depends(get_current_active_superuser)])
async def delete_feedback(
    feedback_id: UUID,
    session: SessionDep,
    application: ApplicationDep = None,
) -> Any:
    """
    Delete a feedback by ID.
    Only superusers can delete feedback.
    If application is provided, only feedback for that application can be deleted.
    """
    # Find the feedback by ID
    feedback = session.get(Feedback, feedback_id)
    
    # Check if feedback exists
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Validate application if provided
    if application and feedback.application_id != application.id:
        raise HTTPException(status_code=404, detail="Feedback not found for this application")
    
    # Delete the feedback
    session.delete(feedback)
    session.commit()
    
    return FeedbackDelete(message="Feedback successfully deleted")