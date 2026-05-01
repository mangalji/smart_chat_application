from django.db import migrations


def _rename_table_forwards(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if connection.vendor == "mysql":
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = %s
                """,
                ["accounts_email_otp"],
            )
            has_old = cursor.fetchone()[0] > 0
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = %s
                """,
                ["accounts_otp"],
            )
            has_new = cursor.fetchone()[0] > 0
            if has_old and not has_new:
                cursor.execute("RENAME TABLE accounts_email_otp TO accounts_otp")
        elif connection.vendor == "postgresql":
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = current_schema() AND table_name = 'accounts_email_otp'
                )
                """
            )
            has_old = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = current_schema() AND table_name = 'accounts_otp'
                )
                """
            )
            has_new = cursor.fetchone()[0]
            if has_old and not has_new:
                cursor.execute('ALTER TABLE accounts_email_otp RENAME TO accounts_otp')
        elif connection.vendor == "sqlite":
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounts_email_otp'"
            )
            has_old = cursor.fetchone() is not None
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounts_otp'"
            )
            has_new = cursor.fetchone() is not None
            if has_old and not has_new:
                cursor.execute("ALTER TABLE accounts_email_otp RENAME TO accounts_otp")


def _rename_table_backwards(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if connection.vendor == "mysql":
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = %s
                """,
                ["accounts_otp"],
            )
            has_new = cursor.fetchone()[0] > 0
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = %s
                """,
                ["accounts_email_otp"],
            )
            has_old = cursor.fetchone()[0] > 0
            if has_new and not has_old:
                cursor.execute("RENAME TABLE accounts_otp TO accounts_email_otp")
        elif connection.vendor == "postgresql":
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = current_schema() AND table_name = 'accounts_otp'
                )
                """
            )
            has_new = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = current_schema() AND table_name = 'accounts_email_otp'
                )
                """
            )
            has_old = cursor.fetchone()[0]
            if has_new and not has_old:
                cursor.execute('ALTER TABLE accounts_otp RENAME TO accounts_email_otp')
        elif connection.vendor == "sqlite":
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounts_otp'"
            )
            has_new = cursor.fetchone() is not None
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounts_email_otp'"
            )
            has_old = cursor.fetchone() is not None
            if has_new and not has_old:
                cursor.execute("ALTER TABLE accounts_otp RENAME TO accounts_email_otp")


def _maybe_rename_otp_index_forwards(schema_editor):
    """Best-effort index rename; old name missing or MySQL < 8 is OK—ORM does not require a specific index name."""
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = DATABASE() AND table_name = 'accounts_otp'
            AND index_name = %s
            """,
            ["accounts_em_email_5cf481_idx"],
        )
        if cursor.fetchone()[0] == 0:
            return
        try:
            cursor.execute(
                "ALTER TABLE accounts_otp RENAME INDEX accounts_em_email_5cf481_idx "
                "TO accounts_ot_email_5134b2_idx"
            )
        except Exception:
            pass


def _maybe_rename_otp_index_backwards(schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = DATABASE() AND table_name = 'accounts_otp'
            AND index_name = %s
            """,
            ["accounts_ot_email_5134b2_idx"],
        )
        if cursor.fetchone()[0] == 0:
            return
        try:
            cursor.execute(
                "ALTER TABLE accounts_otp RENAME INDEX accounts_ot_email_5134b2_idx "
                "TO accounts_em_email_5cf481_idx"
            )
        except Exception:
            pass


def combined_forwards(apps, schema_editor):
    _rename_table_forwards(apps, schema_editor)
    _maybe_rename_otp_index_forwards(schema_editor)


def combined_backwards(apps, schema_editor):
    _maybe_rename_otp_index_backwards(schema_editor)
    _rename_table_backwards(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelTable(
                    name="emailotp",
                    table="accounts_otp",
                ),
                migrations.RenameIndex(
                    model_name="emailotp",
                    new_name="accounts_ot_email_5134b2_idx",
                    old_name="accounts_em_email_5cf481_idx",
                ),
            ],
            database_operations=[
                migrations.RunPython(combined_forwards, combined_backwards),
            ],
        ),
    ]
