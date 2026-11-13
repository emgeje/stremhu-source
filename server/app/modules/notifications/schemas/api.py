from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from app.modules.settings.enums import DiskAlertLevelEnum, SmtpSecurityEnum
from app.modules.settings.schemas.internal import DiskAlertSettings


class NotificationChannelEnum(str, Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class DiskAlertSettingsUpdate(DiskAlertSettings):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class DiskAlertSettingsResponse(_CamelModel):
    enabled: bool
    warning_percent: int
    critical_percent: int
    repeat_hours: int
    notify_recovery: bool


class EmailNotificationSettingsResponse(_CamelModel):
    enabled: bool
    smtp_host: str
    smtp_port: int
    security: SmtpSecurityEnum
    username: str
    password_set: bool
    sender: str
    recipients: list[str]


class TelegramNotificationSettingsResponse(_CamelModel):
    enabled: bool
    bot_token_set: bool
    chat_id: str


class NotificationSettingsResponse(_CamelModel):
    server_name: str
    disk_alert: DiskAlertSettingsResponse
    email: EmailNotificationSettingsResponse
    telegram: TelegramNotificationSettingsResponse


class EmailNotificationSettingsUpdate(_CamelModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    security: SmtpSecurityEnum = SmtpSecurityEnum.STARTTLS
    username: str = ""
    password: str | None = Field(
        default=None,
        description="`null` esetén a korábban mentett jelszó megmarad.",
    )
    sender: str = ""
    recipients: list[EmailStr] = Field(default_factory=list)


class TelegramNotificationSettingsUpdate(_CamelModel):
    enabled: bool = False
    bot_token: str | None = Field(
        default=None,
        description="`null` esetén a korábban mentett token megmarad.",
    )
    chat_id: str = ""


class NotificationSettingsUpdateRequest(_CamelModel):
    server_name: str = Field(default="", max_length=100)
    disk_alert: DiskAlertSettingsUpdate
    email: EmailNotificationSettingsUpdate
    telegram: TelegramNotificationSettingsUpdate


class NotificationTestRequest(_CamelModel):
    channel: NotificationChannelEnum


class DiskUsageResponse(_CamelModel):
    path: str
    total: int
    used: int
    free: int
    percent: float


class DiskStatusResponse(_CamelModel):
    level: DiskAlertLevelEnum
    usages: list[DiskUsageResponse]
    notified_level: DiskAlertLevelEnum
    notified_at: datetime | None
