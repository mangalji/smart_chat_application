from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("direct/start/", views.start_direct, name="start_direct"),
    path("groups/new/", views.create_group, name="create_group"),
    path("groups/join/", views.join_group, name="join_group"),
    path("room/<int:room_id>/", views.room_chat, name="room"),
    path("room/<int:room_id>/upload/", views.upload_chat_media, name="upload_media"),
    path("room/<int:room_id>/schedule/", views.schedule_message_create, name="schedule_create"),
    path("api/suggest-reply/", views.api_suggest_reply, name="api_suggest_reply"),
    path("scheduled/", views.scheduled_list, name="scheduled_list"),
]
