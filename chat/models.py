from django.conf import settings
from django.db import models
from django.db.models import Count


class ChatRoomType(models.TextChoices):
    DIRECT = "direct", "Direct"
    GROUP = "group", "Group"


class ChatRoom(models.Model):
    room_type = models.CharField(max_length=16, choices=ChatRoomType.choices, db_index=True)
    name = models.CharField(max_length=128, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rooms_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_room"
        ordering = ["-created_at"]

    def __str__(self):
        if self.room_type == ChatRoomType.GROUP and self.name:
            return self.name
        return f"Room {self.pk} ({self.room_type})"

    def display_name_for(self, user):
        if self.room_type == ChatRoomType.GROUP:
            return self.name or f"Group #{self.pk}"
        other = self.other_participant(user)
        if other:
            return other.get_full_name() or other.email
        return "Direct chat"

    def other_participant(self, user):
        if self.room_type != ChatRoomType.DIRECT:
            return None
        members = list(self.members.select_related("user").all())
        for m in members:
            if m.user_id != user.id:
                return m.user
        return None


class GroupMember(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_group_member"
        unique_together = [["room", "user"]]
        indexes = [
            models.Index(fields=["room", "user"]),
        ]

    def __str__(self):
        return f"{self.user.email} in {self.room_id}"


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages_sent",
    )
    body = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "created_at"]),
        ]

    def __str__(self):
        return f"Message {self.pk} in room {self.room_id}"


class MediaMessage(models.Model):
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name="media", primary_key=True)
    file = models.FileField(upload_to="chat_media/%Y/%m/%d/")
    original_name = models.CharField(max_length=255, blank=True, default="")
    content_type = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "chat_media_message"

    def __str__(self):
        return f"Media for message {self.message_id}"

    def is_probably_image(self):
        ct = (self.content_type or "").lower()
        if ct.startswith("image/"):
            return True
        n = (self.original_name or self.file.name or "").lower()
        return n.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))


class ScheduledMessageStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class ScheduledEventType(models.TextChoices):
    CUSTOM = "custom", "Custom date & time"
    BIRTHDAY = "birthday", "Birthday"
    NEW_YEAR = "new_year", "New Year"
    FESTIVAL = "festival", "Festival / holiday"


class ScheduledMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="scheduled_messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheduled_messages",
    )
    body = models.TextField(blank=True, default="")
    attachment = models.FileField(upload_to="scheduled_attachments/%Y/%m/%d/", blank=True, null=True)
    scheduled_at = models.DateTimeField(db_index=True)
    event_type = models.CharField(
        max_length=32,
        choices=ScheduledEventType.choices,
        default=ScheduledEventType.CUSTOM,
    )
    status = models.CharField(
        max_length=16,
        choices=ScheduledMessageStatus.choices,
        default=ScheduledMessageStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        db_table = "chat_scheduled_message"
        ordering = ["scheduled_at"]
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
        ]

    def __str__(self):
        return f"Scheduled {self.pk} → room {self.room_id}"


def get_or_create_direct_room(user_a, user_b):
    if user_a.id == user_b.id:
        raise ValueError("Cannot create direct room with self")
    a_id, b_id = sorted([user_a.id, user_b.id])
    candidates = (
        ChatRoom.objects.filter(room_type=ChatRoomType.DIRECT, members__user_id__in=[a_id, b_id])
        .annotate(member_count=Count("members", distinct=True))
        .filter(member_count=2)
        .distinct()
    )
    for room in candidates:
        uids = set(room.members.values_list("user_id", flat=True))
        if uids == {a_id, b_id}:
            return room, False
    room = ChatRoom.objects.create(room_type=ChatRoomType.DIRECT, created_by=user_a)
    GroupMember.objects.bulk_create(
        [
            GroupMember(room=room, user_id=a_id),
            GroupMember(room=room, user_id=b_id),
        ]
    )
    return room, True
