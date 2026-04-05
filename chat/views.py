import json

from django.contrib.auth import get_user_model
from django.db.models import Max
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .ai_suggest import suggest_reply
from .decorators import chat_access_required
from .forms import CreateGroupForm, JoinGroupForm, ScheduleMessageForm
from .models import (
    ChatRoom,
    ChatRoomType,
    GroupMember,
    MediaMessage,
    Message,
    ScheduledMessage,
    ScheduledMessageStatus,
    get_or_create_direct_room,
)
from .utils_broadcast import broadcast_room_event

User = get_user_model()


def _member_queryset(user):
    return GroupMember.objects.filter(user=user).select_related("room")


@chat_access_required
@require_GET
def inbox(request):
    room_ids = _member_queryset(request.user).values_list("room_id", flat=True)
    rooms = (
        ChatRoom.objects.filter(id__in=room_ids)
        .annotate(last_msg=Max("messages__created_at"))
        .order_by("-last_msg", "-id")
    )
    others = User.objects.exclude(pk=request.user.pk).filter(is_active=True).order_by("email")
    return render(
        request,
        "chat/inbox.html",
        {"rooms": rooms, "other_users": others, "user": request.user},
    )


@chat_access_required
@require_POST
def start_direct(request):
    uid = request.POST.get("user_id")
    try:
        other = User.objects.get(pk=int(uid), is_active=True)
    except (ValueError, User.DoesNotExist):
        return redirect("chat:inbox")
    if other.id == request.user.id:
        return redirect("chat:inbox")
    room, _ = get_or_create_direct_room(request.user, other)
    return redirect("chat:room", room_id=room.id)


@chat_access_required
@require_http_methods(["GET", "POST"])
def create_group(request):
    if request.method == "POST":
        form = CreateGroupForm(request.POST)
        if form.is_valid():
            room = ChatRoom.objects.create(
                room_type=ChatRoomType.GROUP,
                name=form.cleaned_data["name"].strip(),
                created_by=request.user,
            )
            GroupMember.objects.create(room=room, user=request.user)
            return redirect("chat:room", room_id=room.id)
    else:
        form = CreateGroupForm()
    return render(request, "chat/create_group.html", {"form": form})


@chat_access_required
@require_http_methods(["GET", "POST"])
def join_group(request):
    if request.method == "POST":
        form = JoinGroupForm(request.POST)
        if form.is_valid():
            rid = form.cleaned_data["room_id"]
            room = ChatRoom.objects.filter(pk=rid, room_type=ChatRoomType.GROUP).first()
            if not room:
                form.add_error("room_id", "No group found with this ID.")
            elif GroupMember.objects.filter(room=room, user=request.user).exists():
                return redirect("chat:room", room_id=room.id)
            else:
                GroupMember.objects.create(room=room, user=request.user)
                return redirect("chat:room", room_id=room.id)
    else:
        form = JoinGroupForm()
    return render(request, "chat/join_group.html", {"form": form})


def _room_for_user(room_id, user):
    room = get_object_or_404(ChatRoom, pk=room_id)
    if not GroupMember.objects.filter(room=room, user=user).exists():
        return None, None
    return room, GroupMember.objects.filter(room=room).select_related("user")


@chat_access_required
@require_GET
def room_chat(request, room_id):
    room, member_qs = _room_for_user(room_id, request.user)
    if room is None:
        return HttpResponseForbidden("You are not a member of this room.")
    chat_messages = (
        Message.objects.filter(room=room)
        .select_related("sender", "media")
        .order_by("created_at")
    )
    members = list(member_qs)
    schedule_form = ScheduleMessageForm()
    return render(
        request,
        "chat/room.html",
        {
            "room": room,
            "chat_messages": chat_messages,
            "members": members,
            "user": request.user,
            "schedule_form": schedule_form,
        },
    )


@chat_access_required
@require_POST
def upload_chat_media(request, room_id):
    room, _ = _room_for_user(room_id, request.user)
    if room is None:
        return JsonResponse({"error": "forbidden"}, status=403)
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "No file uploaded."}, status=400)
    msg = Message.objects.create(room=room, sender=request.user, body="")
    media = MediaMessage.objects.create(
        message=msg,
        file=f,
        original_name=getattr(f, "name", "") or "attachment",
        content_type=getattr(f, "content_type", "") or "",
    )
    created_iso = msg.created_at.isoformat()
    broadcast_room_event(
        room_id,
        event="message",
        message_id=msg.id,
        sender_id=request.user.id,
        sender_email=request.user.email,
        sender_name=request.user.get_full_name() or request.user.email,
        body="",
        created_at=created_iso,
        has_media=True,
        media_url=media.file.url,
        media_name=media.original_name or media.file.name.split("/")[-1],
    )
    return JsonResponse(
        {
            "ok": True,
            "message_id": msg.id,
            "created_at": created_iso,
            "media_url": media.file.url,
            "media_name": media.original_name or "",
        }
    )


@chat_access_required
@require_POST
def api_suggest_reply(request):
    try:
        data = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    room_id = data.get("room_id")
    try:
        room_id = int(room_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "room_id required"}, status=400)
    room, _ = _room_for_user(room_id, request.user)
    if room is None:
        return JsonResponse({"error": "forbidden"}, status=403)
    recent = list(
        Message.objects.filter(room_id=room_id)
        .select_related("sender")
        .order_by("-created_at")[:50]
    )
    recent.reverse()
    language = data.get("language") or "en"
    tone = data.get("tone") or "professional"
    text = suggest_reply(
        messages=recent,
        current_user_id=request.user.id,
        language=language,
        tone=tone,
    )
    return JsonResponse({"suggestion": text})


@chat_access_required
@require_POST
def schedule_message_create(request, room_id):
    room, _ = _room_for_user(room_id, request.user)
    if room is None:
        return redirect("chat:inbox")
    form = ScheduleMessageForm(request.POST, request.FILES)
    if form.is_valid():
        sm = ScheduledMessage(
            room=room,
            sender=request.user,
            body=(form.cleaned_data.get("body") or "").strip(),
            scheduled_at=form.cleaned_data["scheduled_at"],
            event_type=form.cleaned_data["event_type"],
            status=ScheduledMessageStatus.PENDING,
        )
        if form.cleaned_data.get("attachment"):
            sm.attachment = form.cleaned_data["attachment"]
        if sm.scheduled_at.tzinfo is None:
            sm.scheduled_at = timezone.make_aware(sm.scheduled_at, timezone.get_current_timezone())
        sm.save()
        return redirect("chat:scheduled_list")
    chat_messages = (
        Message.objects.filter(room=room)
        .select_related("sender", "media")
        .order_by("created_at")
    )
    members = list(GroupMember.objects.filter(room=room).select_related("user"))
    return render(
        request,
        "chat/room.html",
        {
            "room": room,
            "chat_messages": chat_messages,
            "members": members,
            "user": request.user,
            "schedule_form": form,
        },
    )


@chat_access_required
@require_GET
def scheduled_list(request):
    items = ScheduledMessage.objects.filter(sender=request.user).select_related("room").order_by(
        "-scheduled_at"
    )[:200]
    return render(request, "chat/scheduled_list.html", {"items": items})
