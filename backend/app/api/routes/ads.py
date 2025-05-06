from typing import Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query

from sqlmodel import select
from app.models.database.ad import Ad
from app.models.schemas.ad import AdResponse
from app.api.deps import SessionDep, ApplicationDep, LanguageDep, CurrentUser
from app.core.i18n import get_translation

router = APIRouter()


@router.get("/unit-id", response_model=AdResponse)
def get_ad_unit_id(
    ad_name: str = Query(..., description="The name of the ad"),
    session: SessionDep = None,
    application: ApplicationDep = None,
    language: LanguageDep = None,
    current_user: CurrentUser = None,
) -> Any:
    """
    Get the ad unit ID for a specific ad name in the current application.
    """
    # Query for an ad with matching application_id and name that is active
    statement = (
        select(Ad)
        .where(Ad.application_id == application.id)
        .where(Ad.name == ad_name)
        .where(Ad.is_active == True)
    )
    
    ad = session.exec(statement).first()
    
    if not ad:
        raise HTTPException(
            status_code=404,
            detail=get_translation("ad_not_found", language)
        )
    
    return AdResponse(ad_unit_id=ad.unit_id)