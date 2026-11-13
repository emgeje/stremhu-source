from enum import Enum


class SettingsKeyEnum(str, Enum):
    SYSTEM = "system"
    RELAY = "relay"
    NETWORK = "network"
    NOTIFICATIONS = "notifications"
    DISK_ALERT_STATE = "disk_alert_state"


class NetworkModeEnum(str, Enum):
    LOCAL = "local"
    AUTO = "auto"
    MANUAL = "manual"


class RelayEncryptionEnum(str, Enum):
    ENABLED = "enabled"
    FORCED = "forced"
    DISABLED = "disabled"


class NetworkConnectionEnum(str, Enum):
    LOCAL = "local"
    PUBLIC = "public"


class SmtpSecurityEnum(str, Enum):
    NONE = "none"
    STARTTLS = "starttls"
    SSL = "ssl"


class DiskAlertLevelEnum(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    FULL = "full"

    @property
    def severity(self) -> int:
        return _DISK_ALERT_SEVERITY[self]


_DISK_ALERT_SEVERITY = {
    DiskAlertLevelEnum.OK: 0,
    DiskAlertLevelEnum.WARNING: 1,
    DiskAlertLevelEnum.CRITICAL: 2,
    DiskAlertLevelEnum.FULL: 3,
}
