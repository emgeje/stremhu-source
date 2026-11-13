import socket
import time
from datetime import datetime
from urllib.parse import urlparse

from fastapi import HTTPException

from app.common.logger import logger
from app.config import config
from app.modules.notifications.channels import (
    NotificationChannelError,
    send_email,
    send_telegram,
)
from app.modules.notifications.disk import (
    DiskUsage,
    classify_usage,
    collect_disk_usages,
    worst_usage,
)
from app.modules.notifications.messages import (
    NotificationMessage,
    build_disk_message,
)
from app.modules.notifications.schemas.api import (
    DiskStatusResponse,
    DiskUsageResponse,
    NotificationChannelEnum,
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
)
from app.modules.settings.enums import DiskAlertLevelEnum
from app.modules.settings.schemas.internal import (
    DiskAlertSettings,
    DiskAlertState,
    EmailNotificationSettings,
    NotificationSettings,
    TelegramNotificationSettings,
)
from app.modules.settings.service import SettingsService
from app.modules.storage.service import StorageService


class NotificationsService:
    def __init__(
        self,
        settings_service: SettingsService,
        storage_service: StorageService | None = None,
    ):
        self._settings_service = settings_service
        self._storage_service = storage_service

    def _collect_usages(self) -> list[DiskUsage]:
        """Lemezhasználat a riasztáshoz.

        Kézi tárhelykorlát vagy „seed amíg nem kell a hely” mód esetén a letöltési
        könyvtárnál a StremHU saját tárhely-számítását használja: a korlát a
        kapacitás, seed módban pedig a törölhető torrentek helye szabadnak számít,
        hiszen új letöltésnél automatikusan felszabadul.
        """
        usages = collect_disk_usages()
        if self._storage_service is None:
            return usages

        system_settings = self._settings_service.find_system()
        if not system_settings or not (
            system_settings.seed_until_space_needed
            or system_settings.storage_limit_bytes
        ):
            return usages

        try:
            status = self._storage_service.get_status()
        except Exception:
            logger.exception("⚠️ A tárhely állapota nem kérdezhető le.")
            return usages

        reclaimable = (
            status.evictable_bytes if system_settings.seed_until_space_needed else 0
        )
        free = min(status.capacity_bytes, status.free_bytes + reclaimable)
        downloads_path = str(config.downloads_dir)
        storage_usage = DiskUsage(
            path=downloads_path,
            total=status.capacity_bytes,
            used=max(0, status.capacity_bytes - free),
            free=free,
            reclaimable=reclaimable,
        )

        return [storage_usage] + [u for u in usages if u.path != downloads_path]

    # Beállítások

    def get_settings(self) -> NotificationSettings:
        return self._settings_service.get_notifications()

    def to_response(
        self, settings: NotificationSettings
    ) -> NotificationSettingsResponse:
        email = settings.email
        telegram = settings.telegram
        return NotificationSettingsResponse.model_validate(
            {
                "server_name": settings.server_name,
                "disk_alert": settings.disk_alert.model_dump(),
                "email": {
                    **email.model_dump(exclude={"password"}),
                    "password_set": bool(email.password),
                },
                "telegram": {
                    "enabled": telegram.enabled,
                    "bot_token_set": bool(telegram.bot_token),
                    "chat_id": telegram.chat_id,
                },
            }
        )

    def update_settings(
        self, payload: NotificationSettingsUpdateRequest
    ) -> NotificationSettings:
        current = self.get_settings()

        email_data = payload.email.model_dump(exclude={"password"})
        email_data["recipients"] = [str(r) for r in payload.email.recipients]
        email_data["password"] = (
            current.email.password
            if payload.email.password is None
            else payload.email.password
        )

        telegram_data = payload.telegram.model_dump(exclude={"bot_token"})
        telegram_data["bot_token"] = (
            current.telegram.bot_token
            if payload.telegram.bot_token is None
            else payload.telegram.bot_token.strip()
        )
        telegram_data["chat_id"] = telegram_data["chat_id"].strip()

        settings = NotificationSettings(
            server_name=payload.server_name.strip(),
            disk_alert=DiskAlertSettings.model_validate(
                payload.disk_alert.model_dump()
            ),
            email=EmailNotificationSettings.model_validate(email_data),
            telegram=TelegramNotificationSettings.model_validate(telegram_data),
        )

        self._validate_channels(settings)
        return self._settings_service.save_notifications(settings)

    @staticmethod
    def _validate_channels(settings: NotificationSettings) -> None:
        errors: list[str] = []

        if settings.email.enabled:
            if not settings.email.smtp_host:
                errors.append("Az SMTP szerver megadása kötelező.")
            if not settings.email.sender:
                errors.append("A feladó e-mail cím megadása kötelező.")
            if not settings.email.recipients:
                errors.append("Legalább egy címzett megadása kötelező.")

        if settings.telegram.enabled:
            if not settings.telegram.bot_token:
                errors.append("A Telegram bot token megadása kötelező.")
            if not settings.telegram.chat_id:
                errors.append("A Telegram chat ID megadása kötelező.")

        if errors:
            raise HTTPException(status_code=400, detail="\n".join(errors))

    # Tárhely állapot

    def get_disk_status(self) -> DiskStatusResponse:
        settings = self.get_settings()
        state = self._settings_service.get_disk_alert_state()
        usages = self._collect_usages()
        usage = worst_usage(usages)

        level = (
            classify_usage(usage, settings.disk_alert, state.level)
            if usage
            else DiskAlertLevelEnum.OK
        )

        return DiskStatusResponse(
            level=level,
            usages=[
                DiskUsageResponse(
                    path=u.path,
                    total=u.total,
                    used=u.used,
                    free=u.free,
                    reclaimable=u.reclaimable,
                    percent=u.percent,
                )
                for u in usages
            ],
            notified_level=state.level,
            notified_at=(
                datetime.fromtimestamp(state.notified_at).astimezone()
                if state.notified_at
                else None
            ),
        )

    # Küldés

    def _server_name(self, settings: NotificationSettings) -> str:
        if settings.server_name:
            return settings.server_name
        app_url = self._app_url()
        if app_url:
            host = urlparse(app_url).hostname
            if host:
                return host
        return socket.gethostname()

    def _app_url(self) -> str | None:
        try:
            return self._settings_service.get_app_url()
        except Exception:
            return None

    def _link(self) -> str | None:
        app_url = self._app_url()
        return f"{app_url}/dashboard/system" if app_url else None

    async def _dispatch(
        self, settings: NotificationSettings, message: NotificationMessage
    ) -> int:
        """Elküldi az üzenetet minden engedélyezett csatornán. A sikeres küldések számát adja vissza."""
        sent = 0

        if settings.email.enabled:
            try:
                await send_email(settings.email, message)
                sent += 1
            except NotificationChannelError as e:
                logger.error(f"‼️ E-mail értesítés sikertelen: {e}")

        if settings.telegram.enabled:
            try:
                await send_telegram(settings.telegram, message)
                sent += 1
            except NotificationChannelError as e:
                logger.error(f"‼️ Telegram értesítés sikertelen: {e}")

        return sent

    async def send_test(self, channel: NotificationChannelEnum) -> None:
        settings = self.get_settings()
        usage = worst_usage(self._collect_usages()) or DiskUsage(
            path="-", total=0, used=0, free=0
        )
        state = self._settings_service.get_disk_alert_state()
        message = build_disk_message(
            level=classify_usage(usage, settings.disk_alert, state.level),
            usage=usage,
            server_name=self._server_name(settings),
            link=self._link(),
            is_test=True,
        )

        try:
            if channel == NotificationChannelEnum.EMAIL:
                if not settings.email.smtp_host or not settings.email.recipients:
                    raise NotificationChannelError(
                        "Előbb mentsd el az e-mail beállításokat."
                    )
                await send_email(settings.email, message)
            else:
                if not settings.telegram.bot_token or not settings.telegram.chat_id:
                    raise NotificationChannelError(
                        "Előbb mentsd el a Telegram beállításokat."
                    )
                await send_telegram(settings.telegram, message)
        except NotificationChannelError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def check_disk_space(self) -> None:
        settings = self.get_settings()
        alert = settings.disk_alert

        if not alert.enabled:
            return
        if not settings.email.enabled and not settings.telegram.enabled:
            return

        usage = worst_usage(self._collect_usages())
        if not usage:
            logger.warning("⚠️ A tárhely telítettsége nem kérdezhető le.")
            return

        state = self._settings_service.get_disk_alert_state()
        level = classify_usage(usage, alert, state.level)
        now = int(time.time())

        should_send = False
        is_reminder = False

        if level.severity > state.level.severity:
            should_send = True
        elif level == state.level:
            if (
                level != DiskAlertLevelEnum.OK
                and alert.repeat_hours > 0
                and now - state.notified_at >= alert.repeat_hours * 3600
            ):
                should_send = True
                is_reminder = True
        elif level == DiskAlertLevelEnum.OK and alert.notify_recovery:
            should_send = True

        if not should_send:
            if level != state.level:
                self._settings_service.save_disk_alert_state(
                    DiskAlertState(level=level, notified_at=state.notified_at)
                )
            return

        message = build_disk_message(
            level=level,
            usage=usage,
            server_name=self._server_name(settings),
            link=self._link(),
            is_reminder=is_reminder,
        )

        logger.info(
            f"📣 Tárhely értesítés küldése: {level.value} ({usage.percent:.1f}%, {usage.path})"
        )
        sent = await self._dispatch(settings, message)
        if sent == 0:
            # Egyik csatorna sem sikerült: az állapotot nem mentjük, a következő futás újrapróbálja.
            return

        self._settings_service.save_disk_alert_state(
            DiskAlertState(level=level, notified_at=now)
        )
