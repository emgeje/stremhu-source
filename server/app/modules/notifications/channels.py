import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

import httpx

from app.modules.notifications.messages import NotificationMessage
from app.modules.settings.enums import SmtpSecurityEnum
from app.modules.settings.schemas.internal import (
    EmailNotificationSettings,
    TelegramNotificationSettings,
)

SEND_TIMEOUT_SECONDS = 20


class NotificationChannelError(Exception):
    """Egy értesítési csatorna küldési hibája, felhasználónak megjeleníthető üzenettel."""


def _send_email_sync(settings: EmailNotificationSettings, message: NotificationMessage):
    email = EmailMessage()
    email["Subject"] = message.title
    email["From"] = settings.sender
    email["To"] = ", ".join(settings.recipients)
    email["Date"] = formatdate(localtime=True)
    email["Message-ID"] = make_msgid(domain="stremhu.source")
    email.set_content(message.to_text())
    email.add_alternative(message.to_email_html(), subtype="html")

    context = ssl.create_default_context()

    if settings.security == SmtpSecurityEnum.SSL:
        smtp: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=SEND_TIMEOUT_SECONDS,
            context=context,
        )
    else:
        smtp = smtplib.SMTP(
            settings.smtp_host, settings.smtp_port, timeout=SEND_TIMEOUT_SECONDS
        )

    with smtp:
        smtp.ehlo()
        if settings.security == SmtpSecurityEnum.STARTTLS:
            smtp.starttls(context=context)
            smtp.ehlo()
        if settings.username:
            smtp.login(settings.username, settings.password)
        smtp.send_message(email)


async def send_email(
    settings: EmailNotificationSettings, message: NotificationMessage
) -> None:
    try:
        await asyncio.to_thread(_send_email_sync, settings, message)
    except smtplib.SMTPAuthenticationError:
        raise NotificationChannelError(
            "Az SMTP szerver elutasította a bejelentkezést. Ellenőrizd a felhasználónevet és a jelszót."
        )
    except (smtplib.SMTPException, OSError) as e:
        raise NotificationChannelError(f"Az e-mail küldése sikertelen: {e}")


async def send_telegram(
    settings: TelegramNotificationSettings, message: NotificationMessage
) -> None:
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    payload = {
        "chat_id": settings.chat_id,
        "text": message.to_telegram_html(),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=SEND_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError as e:
        # A kivétel szövege tartalmazhatja az URL-t (és benne a tokent), ezért nem adjuk tovább.
        raise NotificationChannelError(
            f"A Telegram API nem érhető el ({type(e).__name__})."
        )

    if response.status_code != 200:
        try:
            description = response.json().get("description", "")
        except ValueError:
            description = response.text[:200]
        raise NotificationChannelError(
            f"A Telegram elutasította az üzenetet: {description or response.status_code}"
        )
