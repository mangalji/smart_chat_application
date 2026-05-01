import logging
import threading
import time

from django.apps import AppConfig
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)
_scheduler_started = False
_missing_tables_logged = False


def _run_scheduler_loop():
    from django import db

    global _missing_tables_logged
    time.sleep(3)
    while True:
        try:
            from django.core.management import call_command

            db.close_old_connections()
            call_command("process_scheduled_messages", verbosity=0)
        except (ProgrammingError, OperationalError) as exc:
            err = str(exc)
            if "1146" in err or "doesn't exist" in err.lower():
                if not _missing_tables_logged:
                    _missing_tables_logged = True
                    logger.warning(
                        "Skipping scheduled messages: database tables are missing. "
                        "Run: python manage.py migrate"
                    )
            else:
                logger.exception("Scheduled message runner failed")
        except Exception:
            logger.exception("Scheduled message runner failed")
        time.sleep(30)


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chat"
    verbose_name = "Chat"

    def ready(self):
        global _scheduler_started
        if not settings.DEBUG:
            return
        if _scheduler_started:
            return
        _scheduler_started = True
        t = threading.Thread(target=_run_scheduler_loop, daemon=True)
        t.start()
