import asyncio

import pytest

from app.modules.notifications import service as notifications_service_module
from app.modules.notifications.disk import DiskUsage, classify_usage
from app.modules.notifications.service import NotificationsService
from app.modules.settings.enums import DiskAlertLevelEnum as Level
from app.modules.settings.schemas.internal import (
    DiskAlertSettings,
    DiskAlertState,
    NotificationSettings,
    TelegramNotificationSettings,
)

GIB = 1024**3


def usage(percent: float, total: int = 1000 * GIB) -> DiskUsage:
    used = int(total * percent / 100)
    return DiskUsage(path="/data", total=total, used=used, free=total - used)


SETTINGS = DiskAlertSettings(warning_percent=85, critical_percent=95)


@pytest.mark.parametrize(
    ("percent", "previous", "expected"),
    [
        (50, Level.OK, Level.OK),
        (86, Level.OK, Level.WARNING),
        (96, Level.OK, Level.CRITICAL),
        (99.5, Level.OK, Level.FULL),
        # Holtsáv: a küszöb alá esés után is marad a szint, amíg 2%-nál többet nem javul
        (84, Level.WARNING, Level.WARNING),
        (82, Level.WARNING, Level.OK),
        (94, Level.CRITICAL, Level.CRITICAL),
        (90, Level.CRITICAL, Level.WARNING),
    ],
)
def test_classify_usage(percent, previous, expected):
    assert classify_usage(usage(percent), SETTINGS, previous) == expected


def test_classify_usage_full_when_less_than_1gib_free():
    assert classify_usage(usage(50, total=GIB), SETTINGS) == Level.FULL


def test_thresholds_must_be_ordered():
    with pytest.raises(ValueError):
        DiskAlertSettings(warning_percent=95, critical_percent=90)


class FakeSettingsService:
    def __init__(self):
        self.notifications = NotificationSettings(
            server_name="Teszt",
            telegram=TelegramNotificationSettings(
                enabled=True, bot_token="token", chat_id="1"
            ),
        )
        self.state = DiskAlertState()

    def get_notifications(self):
        return self.notifications

    def get_disk_alert_state(self):
        return self.state

    def save_disk_alert_state(self, state):
        self.state = state

    def get_app_url(self):
        return "https://stremhu.example.hu"


def test_check_disk_space_notification_flow(monkeypatch):
    sent = []
    current = {"percent": 50.0}

    async def fake_send_telegram(_settings, message):
        sent.append(message)

    monkeypatch.setattr(
        notifications_service_module, "send_telegram", fake_send_telegram
    )
    monkeypatch.setattr(
        notifications_service_module,
        "collect_disk_usages",
        lambda: [usage(current["percent"])],
    )

    settings_service = FakeSettingsService()
    service = NotificationsService(settings_service)  # type: ignore[arg-type]

    def run(percent: float):
        current["percent"] = percent
        asyncio.run(service.check_disk_space())
        return len(sent), settings_service.state.level

    assert run(50) == (0, Level.OK)
    assert run(87) == (1, Level.WARNING)
    assert run(88) == (1, Level.WARNING)  # ugyanaz a szint, nincs ismétlés
    assert run(96) == (2, Level.CRITICAL)
    assert run(99.6) == (3, Level.FULL)

    # Emlékeztető a beállított idő elteltével
    settings_service.state.notified_at -= 25 * 3600
    assert run(99.6) == (4, Level.FULL)
    assert "emlékeztető" in sent[-1].title

    # Javulás: csendes visszaminősítés, majd helyreállási üzenet
    assert run(90) == (4, Level.WARNING)
    assert run(60) == (5, Level.OK)
    assert "Rendben" in sent[-1].title
    assert sent[-1].link == "https://stremhu.example.hu/dashboard/system"


def test_check_disk_space_retries_when_sending_fails(monkeypatch):
    from app.modules.notifications.channels import NotificationChannelError

    async def failing_send(_settings, _message):
        raise NotificationChannelError("hiba")

    monkeypatch.setattr(notifications_service_module, "send_telegram", failing_send)
    monkeypatch.setattr(
        notifications_service_module, "collect_disk_usages", lambda: [usage(97)]
    )

    settings_service = FakeSettingsService()
    service = NotificationsService(settings_service)  # type: ignore[arg-type]
    asyncio.run(service.check_disk_space())

    # Sikertelen küldés után az állapot nem változik, így a következő futás újrapróbálja.
    assert settings_service.state.level == Level.OK
