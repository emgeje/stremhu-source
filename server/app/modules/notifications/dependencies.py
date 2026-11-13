from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.modules.notifications.service import NotificationsService
from app.modules.settings.dependencies import create_settings_service
from app.modules.storage.dependencies import create_storage_service


def create_notifications_service(db: Session) -> NotificationsService:
    settings_service = create_settings_service(db)
    return NotificationsService(
        settings_service=settings_service,
        storage_service=create_storage_service(db),
    )


def get_notifications_service(
    db: Annotated[Session, Depends(get_db)],
) -> NotificationsService:
    return create_notifications_service(db)
