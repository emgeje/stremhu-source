import html
from dataclasses import dataclass, field
from datetime import datetime

import humanize

from app.modules.notifications.disk import DiskUsage
from app.modules.settings.enums import DiskAlertLevelEnum


@dataclass
class NotificationMessage:
    """Csatorna-független üzenet, amelyből e-mail és Telegram formátum is készül."""

    title: str
    summary: str
    details: list[tuple[str, str]] = field(default_factory=list)
    link: str | None = None
    link_label: str = "StremHU Source megnyitása"

    def to_text(self) -> str:
        lines = [self.title, "", self.summary, ""]
        lines += [f"{label}: {value}" for label, value in self.details]
        if self.link:
            lines += ["", f"{self.link_label}: {self.link}"]
        return "\n".join(lines)

    def to_telegram_html(self) -> str:
        lines = [f"<b>{html.escape(self.title)}</b>", "", html.escape(self.summary), ""]
        lines += [
            f"<b>{html.escape(label)}:</b> {html.escape(value)}"
            for label, value in self.details
        ]
        if self.link:
            lines += [
                "",
                f'<a href="{html.escape(self.link, quote=True)}">'
                f"{html.escape(self.link_label)}</a>",
            ]
        return "\n".join(lines)

    def to_email_html(self) -> str:
        rows = "".join(
            "<tr>"
            f'<td style="padding:4px 12px 4px 0;color:#666;white-space:nowrap">{html.escape(label)}</td>'
            f'<td style="padding:4px 0;font-weight:600">{html.escape(value)}</td>'
            "</tr>"
            for label, value in self.details
        )
        button = ""
        if self.link:
            button = (
                f'<p style="margin-top:20px"><a href="{html.escape(self.link, quote=True)}" '
                'style="background:#111;color:#fff;padding:10px 16px;border-radius:6px;'
                f'text-decoration:none;display:inline-block">{html.escape(self.link_label)}</a></p>'
            )
        return (
            '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:14px;color:#111">'
            f'<h2 style="margin:0 0 8px">{html.escape(self.title)}</h2>'
            f'<p style="margin:0 0 16px">{html.escape(self.summary)}</p>'
            f'<table style="border-collapse:collapse">{rows}</table>'
            f"{button}"
            "</div>"
        )


LEVEL_TEXTS: dict[DiskAlertLevelEnum, tuple[str, str]] = {
    DiskAlertLevelEnum.WARNING: (
        "⚠️ Fogy a szabad tárhely",
        "A tárhely telítettsége elérte a figyelmeztetési szintet. "
        "Érdemes időben helyet felszabadítani.",
    ),
    DiskAlertLevelEnum.CRITICAL: (
        "🟠 Kritikusan kevés a szabad tárhely",
        "A tárhely hamarosan betelik, ezután a lejátszások nem fognak elindulni. "
        "Mielőbb szabadíts fel helyet!",
    ),
    DiskAlertLevelEnum.FULL: (
        "🔴 Betelt a tárhely",
        "Nincs elég szabad hely a lemezen, új lejátszás nem indul el, "
        "amíg nem szabadul fel hely.",
    ),
    DiskAlertLevelEnum.OK: (
        "✅ Rendben a tárhely",
        "A tárhely telítettsége visszaállt a normál tartományba.",
    ),
}


def _size(value: int) -> str:
    return humanize.naturalsize(value, binary=True)


def build_disk_message(
    *,
    level: DiskAlertLevelEnum,
    usage: DiskUsage,
    server_name: str,
    link: str | None,
    is_reminder: bool = False,
    is_test: bool = False,
) -> NotificationMessage:
    title, summary = LEVEL_TEXTS[level]

    if is_reminder:
        title = f"{title} (emlékeztető)"
    if is_test:
        title = "🧪 Teszt értesítés – StremHU Source"
        summary = "Ez egy próbaüzenet. Ha megkaptad, az értesítések ezen a csatornán működnek."

    details = [
        ("Szerver", server_name),
        ("Telítettség", f"{usage.percent:.1f}%"),
        ("Felhasznált", f"{_size(usage.used)} / {_size(usage.total)}"),
        ("Szabad hely", _size(usage.free)),
    ]
    if usage.reclaimable > 0:
        details.append(("Ebből seedben tartott, törölhető", _size(usage.reclaimable)))
    details += [
        ("Figyelt útvonal", usage.path),
        ("Időpont", datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")),
    ]

    return NotificationMessage(
        title=f"[{server_name}] {title}" if not is_test else title,
        summary=summary,
        details=details,
        link=link,
    )
