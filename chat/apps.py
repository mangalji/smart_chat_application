import threading
import time

from django.apps import AppConfig
from django.conf import settings

_scheduler_started = False


def _run_scheduler_loop():
    from django import db

    time.sleep(3)
    while True:
        try:
            from django.core.management import call_command

            db.close_old_connections()
            call_command("process_scheduled_messages", verbosity=0)
        except Exception:
            pass
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
