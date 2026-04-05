from django.contrib import admin

from .models import ChatRoom, GroupMember, MediaMessage, Message, ScheduledMessage


class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 0


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "room_type", "name", "created_by", "created_at")
    list_filter = ("room_type",)
    inlines = [GroupMemberInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "sender", "body_preview", "created_at")
    list_filter = ("room",)
    search_fields = ("body",)

    @admin.display(description="Body")
    def body_preview(self, obj):
        return (obj.body or "")[:60]


@admin.register(MediaMessage)
class MediaMessageAdmin(admin.ModelAdmin):
    list_display = ("message_id", "original_name", "content_type")


@admin.register(ScheduledMessage)
class ScheduledMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "sender", "scheduled_at", "status", "event_type")
    list_filter = ("status", "event_type")
