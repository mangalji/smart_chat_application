"""Print DB connection info and whether chat tables exist vs recorded migrations."""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = "Show database target and chat app table/migration consistency."

    def handle(self, *args, **options):
        cfg = connection.settings_dict
        self.stdout.write(f"ENGINE: {cfg.get('ENGINE')}")
        self.stdout.write(f"NAME:   {cfg.get('NAME')}")
        self.stdout.write(f"HOST:   {cfg.get('HOST')}")
        self.stdout.write("")

        chat_tables = []
        with connection.cursor() as c:
            if connection.vendor == "mysql":
                c.execute("SHOW TABLES")
                chat_tables = [r[0] for r in c.fetchall() if str(r[0]).startswith("chat_")]
            elif connection.vendor == "postgresql":
                c.execute(
                    """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = current_schema() AND tablename LIKE 'chat\\_%'
                    """
                )
                chat_tables = [row[0] for row in c.fetchall()]
            elif connection.vendor == "sqlite":
                c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'chat_%'"
                )
                chat_tables = [row[0] for row in c.fetchall()]

        self.stdout.write(f"Tables matching chat_*: {len(chat_tables)}")
        for t in sorted(chat_tables):
            self.stdout.write(f"  - {t}")

        rec = MigrationRecorder.Migration.objects.filter(app="chat").values_list(
            "name", flat=True
        )
        self.stdout.write("")
        self.stdout.write(f"Recorded in django_migrations for app 'chat': {list(rec)}")

        if list(rec) and not chat_tables:
            self.stdout.write(
                self.style.WARNING(
                    "\nMismatch: migrations are recorded but no chat_* tables exist.\n"
                    "Fix (MySQL dev DB):\n"
                    "  mysql -u YOUR_USER -p smartchat_db -e \"DELETE FROM django_migrations WHERE app='chat';\"\n"
                    "  python manage.py migrate chat\n"
                )
            )
        elif not list(rec) and chat_tables:
            self.stdout.write(
                self.style.WARNING(
                    "\nMismatch: tables exist but no migration rows for chat. Ask for help before deleting data."
                )
            )
