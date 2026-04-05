from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

_widget = {"class": "form-control"}
_widget_pw = forms.PasswordInput(attrs={"class": "form-control"})


class SignupRequestForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs=_widget))
    password1 = forms.CharField(widget=_widget_pw, min_length=8)
    password2 = forms.CharField(widget=_widget_pw, min_length=8)
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs=_widget))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs=_widget))
    phone = forms.CharField(max_length=32, required=False, widget=forms.TextInput(attrs=_widget))

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("password1") and data.get("password2") and data["password1"] != data["password2"]:
            raise ValidationError("Passwords do not match.")
        return data


class SignupVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={**_widget, "autocomplete": "one-time-code"}),
    )


class LoginRequestForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs=_widget))

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if not User.objects.filter(email=email, is_active=True).exists():
            raise ValidationError("No active account found for this email.")
        return email


class LoginVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={**_widget, "autocomplete": "one-time-code"}),
    )
