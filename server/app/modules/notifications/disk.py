import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import config
from app.modules.settings.enums import DiskAlertLevelEnum
from app.modules.settings.schemas.internal import DiskAlertSettings

# Ennél kevesebb szabad hely esetén a tárhelyet teljesen beteltnek tekintjük,
# mert a libtorrent már nem tud érdemben írni a lemezre.
FULL_FREE_BYTES = 1024 * 1024 * 1024
FULL_PERCENT = 99.0

# Visszaminősítéskor ennyi százalékpontnyi „holtsávot” várunk, hogy egy
# küszöb körül ingadozó telítettség ne generáljon üzenet-áradatot.
HYSTERESIS_PERCENT = 2.0


@dataclass(frozen=True)
class DiskUsage:
    path: str
    total: int
    used: int
    free: int

    @property
    def percent(self) -> float:
        if self.total <= 0:
            return 0.0
        return round(self.used / self.total * 100, 1)


def _existing_parent(path: Path) -> Path:
    current = path
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def monitored_paths() -> list[Path]:
    """A figyelt könyvtárak: letöltések és rendszeradatok (adatbázis)."""
    return [config.downloads_dir, config.system_dir]


def collect_disk_usages(paths: list[Path] | None = None) -> list[DiskUsage]:
    """Fájlrendszerenként (eszközönként) egy bejegyzést ad vissza."""
    usages: list[DiskUsage] = []
    seen_devices: set[int] = set()

    for path in paths or monitored_paths():
        target = _existing_parent(path)
        try:
            device = os.stat(target).st_dev
            if device in seen_devices:
                continue
            seen_devices.add(device)

            usage = shutil.disk_usage(target)
        except OSError:
            continue

        usages.append(
            DiskUsage(
                path=str(path),
                total=usage.total,
                # A `free` a nem root felhasználónak elérhető hely, ezt tekintjük valósnak.
                used=usage.total - usage.free,
                free=usage.free,
            )
        )

    return usages


def worst_usage(usages: list[DiskUsage]) -> DiskUsage | None:
    if not usages:
        return None
    return max(usages, key=lambda usage: (usage.percent, -usage.free))


def _raw_level(
    percent: float, free: int, settings: DiskAlertSettings, offset: float = 0.0
) -> DiskAlertLevelEnum:
    if free < FULL_FREE_BYTES or percent >= FULL_PERCENT - offset:
        return DiskAlertLevelEnum.FULL
    if percent >= settings.critical_percent - offset:
        return DiskAlertLevelEnum.CRITICAL
    if percent >= settings.warning_percent - offset:
        return DiskAlertLevelEnum.WARNING
    return DiskAlertLevelEnum.OK


def classify_usage(
    usage: DiskUsage,
    settings: DiskAlertSettings,
    previous_level: DiskAlertLevelEnum = DiskAlertLevelEnum.OK,
) -> DiskAlertLevelEnum:
    """Meghatározza a riasztási szintet holtsávval (hiszterézissel).

    Felfelé azonnal lép, lefelé csak akkor, ha a telítettség a küszöb alá
    csökkent legalább `HYSTERESIS_PERCENT` százalékponttal.
    """
    level = _raw_level(usage.percent, usage.free, settings)
    if level.severity >= previous_level.severity:
        return level

    sticky_level = _raw_level(
        usage.percent, usage.free, settings, offset=HYSTERESIS_PERCENT
    )
    if sticky_level.severity >= previous_level.severity:
        return previous_level
    return sticky_level
