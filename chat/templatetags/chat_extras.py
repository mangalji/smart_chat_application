from django import template

register = template.Library()


@register.filter
def room_label(room, user):
    return room.display_name_for(user)
