from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.config import config
from app.modules.settings.enums import (
    DiskAlertLevelEnum,
    NetworkConnectionEnum,
    NetworkModeEnum,
    RelayEncryptionEnum,
    SmtpSecurityEnum,
)


class NetworkLocalSettings(BaseModel):
    mode: Literal[NetworkModeEnum.LOCAL]
    host: str
    ip: str
    self_signed: bool
    fullchain: str
    privkey: str
    expires_at: int


class NetworkAutoSettings(BaseModel):
    mode: Literal[NetworkModeEnum.AUTO]
    host: str
    token: str
    email: str
    connection: NetworkConnectionEnum
    provider: str
    ip: str
    account_key: str
    fullchain: str
    privkey: str
    expires_at: int
    last_ip_sync_at: int = 0


class NetworkManualSettings(BaseModel):
    mode: Literal[NetworkModeEnum.MANUAL]
    host: str


NetworkSettings = Annotated[
    NetworkLocalSettings | NetworkAutoSettings | NetworkManualSettings,
    Field(discriminator="mode"),
]


class SystemSettings(BaseModel):
    hit_and_run: bool = True
    keep_seed_seconds: int = 0
    cache_retention_seconds: int = 14 * 24 * 60 * 60  # 14 nap másodpercekben


class SystemSettingsUpdate(BaseModel):
    hit_and_run: bool | None = None
    keep_seed_seconds: int | None = None
    cache_retention_seconds: int | None = None


class RelaySettings(BaseModel):
    port: int = Field(default_factory=lambda: config.libtorrent_port)
    download_limit: int = 0
    upload_limit: int = 0
    connections_limit: int = 200
    torrent_connections_limit: int = 20
    enable_upnp_and_natpmp: bool = False
    encryption: RelayEncryptionEnum = RelayEncryptionEnum.ENABLED
    enable_utp: bool = True


class RelaySettingsUpdate(BaseModel):
    port: int | None = None
    download_limit: int | None = None
    upload_limit: int | None = None
    connections_limit: int | None = None
    torrent_connections_limit: int | None = None
    enable_upnp_and_natpmp: bool | None = None
    encryption: RelayEncryptionEnum | None = None
    enable_utp: bool | None = None


# Notifications Settings


class EmailNotificationSettings(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    security: SmtpSecurityEnum = SmtpSecurityEnum.STARTTLS
    username: str = ""
    password: str = ""
    sender: str = ""
    recipients: list[str] = Field(default_factory=list)


class TelegramNotificationSettings(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class DiskAlertSettings(BaseModel):
    enabled: bool = True
    warning_percent: int = Field(default=85, ge=1, le=99)
    critical_percent: int = Field(default=95, ge=1, le=99)
    repeat_hours: int = Field(default=24, ge=0, le=24 * 30)
    notify_recovery: bool = True

    @model_validator(mode="after")
    def validate_thresholds(self) -> "DiskAlertSettings":
        if self.warning_percent >= self.critical_percent:
            raise ValueError(
                "A figyelmeztetési szintnek kisebbnek kell lennie a kritikus szintnél."
            )
        return self


class NotificationSettings(BaseModel):
    server_name: str = ""
    disk_alert: DiskAlertSettings = Field(default_factory=DiskAlertSettings)
    email: EmailNotificationSettings = Field(default_factory=EmailNotificationSettings)
    telegram: TelegramNotificationSettings = Field(
        default_factory=TelegramNotificationSettings
    )


class DiskAlertState(BaseModel):
    level: DiskAlertLevelEnum = DiskAlertLevelEnum.OK
    notified_at: int = 0
