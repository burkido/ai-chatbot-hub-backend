from typing import List, Any
from uuid import UUID
import secrets

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app import crud
from app.api.deps import SessionDep, CurrentUser, get_current_active_superuser
from app.models.database.application import Application
from app.models.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate, 
    ApplicationPublic,
    ApplicationsPublic
)

router = APIRouter()


@router.post("/", response_model=ApplicationPublic)
def create_application(
    application_in: ApplicationCreate,
    session: SessionDep,
    current_user: Any = get_current_active_superuser,
) -> Any:
    """
    Create a new application (admin only).
    """
    # Generate a secure API key if not provided
    if not application_in.api_key:
        application_in.api_key = secrets.token_urlsafe(32)
        
    application = crud.create_application(
        session=session, 
        app_create=application_in
    )
    
    return application


@router.get("/", response_model=ApplicationsPublic)
def get_applications(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    current_user: Any = get_current_active_superuser,
) -> Any:
    """
    Retrieve all applications (admin only).
    """
    applications = crud.get_applications(
        session=session, 
        skip=skip, 
        limit=limit
    )
    
    return ApplicationsPublic(
        data=applications,
        count=len(applications)
    )


@router.get("/{application_id}", response_model=ApplicationPublic)
def get_application(
    application_id: UUID,
    session: SessionDep,
    current_user: Any = get_current_active_superuser,
) -> Any:
    """
    Get a specific application by ID (admin only).
    """
    application = crud.get_application(
        session=session, 
        application_id=application_id
    )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
        
    return application


@router.put("/{application_id}", response_model=ApplicationPublic)
def update_application(
    application_id: UUID,
    application_in: ApplicationUpdate,
    session: SessionDep,
    current_user: Any = get_current_active_superuser,
) -> Any:
    """
    Update a specific application (admin only).
    """
    application = crud.get_application(
        session=session, 
        application_id=application_id
    )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
        
    application = crud.update_application(
        session=session,
        db_obj=application,
        obj_in=application_in
    )
    
    return application


@router.post("/{application_id}/regenerate-api-key", response_model=ApplicationPublic)
def regenerate_api_key(
    application_id: UUID,
    session: SessionDep,
    current_user: Any = get_current_active_superuser,
) -> Any:
    """
    Regenerate the API key for an application (admin only).
    
    Warning: This will invalidate the existing API key and all clients will need to be updated.
    """
    application = crud.get_application(
        session=session, 
        application_id=application_id
    )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Generate a new secure API key
    new_api_key = secrets.token_urlsafe(32)
    
    application = crud.update_application(
        session=session,
        db_obj=application,
        obj_in={"api_key": new_api_key}
    )
    
    return application