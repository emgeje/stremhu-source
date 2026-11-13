from app.common.database import db_session
from app.common.logger import logger
from app.modules.notifications.dependencies import create_notifications_service


async def run_disk_space_check() -> None:
    try:
        with db_session() as db:
            notifications_service = create_notifications_service(db)
            await notifications_service.check_disk_space()
    except Exception:
        logger.exception("‼️ Hiba történt a tárhely ellenőrzése során.")
