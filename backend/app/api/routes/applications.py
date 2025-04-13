from typing import List, Any
from uuid import UUID
import secrets

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app import crud
from app.api.deps import SessionDep, CurrentUser, get_current_active_superuser, ApplicationDep
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
    # Generate a secure package name if not provided
    if not application_in.package_name:
        application_in.package_name = secrets.token_urlsafe(32)
        
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


@router.get("/current", response_model=ApplicationPublic)
def get_current_application(
    session: SessionDep,
    application: ApplicationDep,
) -> Any:
    """
    Get the current application based on X-Application-Key header.
    """
    return application


@router.put("/", response_model=ApplicationPublic)
def update_application(
    application_in: ApplicationUpdate,
    session: SessionDep,
    application: ApplicationDep,
    current_user: Any = get_current_active_superuser,
) -> Any:
    """
    Update the current application (admin only).
    """
    application = crud.update_application(
        session=session,
        db_obj=application,
        obj_in=application_in
    )
    
    return application


@router.post("/regenerate-package-name", response_model=ApplicationPublic)
def regenerate_package_name(
    session: SessionDep,
    application: ApplicationDep,
    current_user: Any = get_current_active_superuser,
) -> Any:
    """
    Regenerate the package name for the current application (admin only).
    
    Warning: This will invalidate the existing package name and all clients will need to be updated.
    """
    # Generate a new secure package name
    new_package_name = secrets.token_urlsafe(32)
    
    application = crud.update_application(
        session=session,
        db_obj=application,
        obj_in={"package_name": new_package_name}
    )
    
    return application