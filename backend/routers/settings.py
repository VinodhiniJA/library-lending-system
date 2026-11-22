from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from core.dependencies import get_current_user, require_librarian
from models.user import User
from models.library_setting import LibrarySetting
from schemas.settings_schema import SettingsUpdate, SettingsResponse


router = APIRouter(
    prefix="/settings",
    tags=["Librarian Settings"]
)


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    settings = db.get(LibrarySetting, 1)

    if settings is None:
        raise HTTPException(
            status_code=404,
            detail="Library settings not found"
        )

    return settings


@router.put("", response_model=SettingsResponse)
def update_settings(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    try:
        settings = db.get(LibrarySetting, 1)

        if settings is None:
            raise HTTPException(
                status_code=404,
                detail="Library settings not found"
            )

        updates = data.model_dump(exclude_unset=True)

        for field, value in updates.items():
            if value is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"{field} cannot be null"
                )

            setattr(settings, field, value)

        settings.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(settings)

        return settings

    except Exception:
        db.rollback()
        raise