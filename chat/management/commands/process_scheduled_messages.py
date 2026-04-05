from django.core.management.base import BaseCommand
from django.utils import timezone

from chat.models import MediaMessage, Message, ScheduledMessage, ScheduledMessageStatus
from chat.utils_broadcast import broadcast_room_event


class Command(BaseCommand):
    help = "Deliver scheduled chat messages whose time has passed."

    def handle(self, *args, **options):
        now = timezone.now()
        qs = ScheduledMessage.objects.filter(
            status=ScheduledMessageStatus.PENDING,
            scheduled_at__lte=now,
        ).select_related("room", "sender")
        for sm in qs:
            try:
                msg = Message.objects.create(room=sm.room, sender=sm.sender, body=sm.body or "")
                media_url = None
                media_name = None
                if sm.attachment:
                    mm = MediaMessage.objects.create(
                        message=msg,
                        file=sm.attachment,
                        original_name=sm.attachment.name.rsplit("/", 1)[-1],
                        content_type="",
                    )
                    media_url = mm.file.url
                    media_name = mm.original_name
                broadcast_room_event(
                    sm.room_id,
                    event="message",
                    message_id=msg.id,
                    sender_id=sm.sender_id,
                    sender_email=sm.sender.email,
                    sender_name=sm.sender.get_full_name() or sm.sender.email,
                    body=msg.body or "",
                    created_at=msg.created_at.isoformat(),
                    has_media=bool(media_url),
                    media_url=media_url or "",
                    media_name=media_name or "",
                )
                sm.status = ScheduledMessageStatus.SENT
                sm.sent_at = timezone.now()
                sm.save(update_fields=["status", "sent_at"])
            except Exception as ex:
                sm.status = ScheduledMessageStatus.FAILED
                sm.error_message = str(ex)[:2000]
                sm.save(update_fields=["status", "error_message"])
