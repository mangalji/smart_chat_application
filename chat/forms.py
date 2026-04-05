from django import forms

from .models import ScheduledEventType

_ctrl = {"class": "form-control"}


class CreateGroupForm(forms.Form):
    name = forms.CharField(max_length=128, widget=forms.TextInput(attrs=_ctrl))


class JoinGroupForm(forms.Form):
    room_id = forms.IntegerField(
        label="Group room ID",
        min_value=1,
        widget=forms.NumberInput(attrs=_ctrl),
    )


class ScheduleMessageForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(attrs={**_ctrl, "rows": 3}),
        required=False,
    )
    attachment = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={"class": "form-control"}))
    scheduled_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
        help_text="Enter time in the server timezone (UTC).",
    )
    event_type = forms.ChoiceField(choices=ScheduledEventType.choices, widget=forms.Select(attrs=_ctrl))

    def clean(self):
        data = super().clean()
        body = (data.get("body") or "").strip()
        file = data.get("attachment")
        if not body and not file:
            raise forms.ValidationError("Enter a message or attach a file.")
        return data
