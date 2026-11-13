from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.schemas.api import SuccessResponse
from app.modules.auth.dependencies import SessionGuard
from app.modules.notifications.dependencies import get_notifications_service
from app.modules.notifications.schemas.api import (
    DiskStatusResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
    NotificationTestRequest,
)
from app.modules.notifications.service import NotificationsService
from app.modules.roles.constants import UserRoleKey
from app.modules.users.models import UserModel

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
)
def get_settings(
    notifications_service: Annotated[
        NotificationsService, Depends(get_notifications_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return notifications_service.to_response(notifications_service.get_settings())


@router.put(
    "/settings",
    response_model=NotificationSettingsResponse,
)
def update_settings(
    payload: NotificationSettingsUpdateRequest,
    notifications_service: Annotated[
        NotificationsService, Depends(get_notifications_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    settings = notifications_service.update_settings(payload)
    return notifications_service.to_response(settings)


@router.post(
    "/test",
    response_model=SuccessResponse,
)
async def send_test(
    payload: NotificationTestRequest,
    notifications_service: Annotated[
        NotificationsService, Depends(get_notifications_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    await notifications_service.send_test(payload.channel)
    return SuccessResponse(success=True, message="A teszt értesítés elküldve.")


@router.get(
    "/disk",
    response_model=DiskStatusResponse,
)
def get_disk_status(
    notifications_service: Annotated[
        NotificationsService, Depends(get_notifications_service)
    ],
    _: Annotated[UserModel, Depends(SessionGuard([UserRoleKey.ADMIN]))],
):
    return notifications_service.get_disk_status()
