from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def chat_access_required(view_func):
    @wraps(view_func)
    @login_required(login_url="accounts:login")
    def _wrapped(request, *args, **kwargs):
        if not request.session.get("chat_access_verified"):
            from django.contrib.auth import logout

            logout(request)
            messages.warning(request, "Please sign in again with a one-time code.")
            return redirect("accounts:login")
        return view_func(request, *args, **kwargs)

    return _wrapped
