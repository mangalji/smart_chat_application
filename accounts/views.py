import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import LoginRequestForm, LoginVerifyForm, SignupRequestForm, SignupVerifyForm
from .models import EmailOTP, OTPPurpose

User = get_user_model()
logger = logging.getLogger("accounts")


def _send_otp_email(email, code, purpose_label):
    """
    Sends OTP to the *user's* inbox (the address they typed on signup/login).
    Your Gmail account is only the SMTP login; recipients are always `email`.
    """
    subject = f"SmartChat {purpose_label} code"
    body = (
        f"Your SmartChat verification code is: {code}\n\n"
        f"It expires in {settings.OTP_EXPIRY_MINUTES} minutes."
    )
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        if settings.DEBUG:
            logger.info(
                "OTP email OK | to=%s | purpose=%s | code=%s",
                email,
                purpose_label,
                code,
            )
        return True
    except Exception:
        logger.exception("OTP email FAILED | to=%s | purpose=%s", email, purpose_label)
        return False


@require_http_methods(["GET", "POST"])
def signup_request(request):
    if request.user.is_authenticated:
        return redirect("chat:inbox")

    if request.method == "POST":
        form = SignupRequestForm(request.POST)
        if form.is_valid():
            otp = EmailOTP.create_for_email(form.cleaned_data["email"], OTPPurpose.SIGNUP)
            if not _send_otp_email(otp.email, otp.code, "signup"):
                otp.delete()
                messages.error(
                    request,
                    "Could not send the email. Check SMTP settings and the server logs.",
                )
            else:
                request.session["pending_signup"] = {
                    "email": form.cleaned_data["email"],
                    "password": form.cleaned_data["password1"],
                    "first_name": form.cleaned_data.get("first_name") or "",
                    "last_name": form.cleaned_data.get("last_name") or "",
                    "phone": form.cleaned_data.get("phone") or "",
                }
                messages.info(
                    request,
                    "We sent a verification code to that email address. "
                    "With DEBUG=True you can also see the code in the terminal.",
                )
                return redirect("accounts:signup_verify")
    else:
        form = SignupRequestForm()
    return render(request, "accounts/signup_request.html", {"form": form})


@require_http_methods(["GET", "POST"])
def signup_verify(request):
    if request.user.is_authenticated:
        return redirect("chat:inbox")
    pending = request.session.get("pending_signup")
    if not pending:
        messages.warning(request, "Start signup again to receive a code.")
        return redirect("accounts:signup")

    if request.method == "POST":
        form = SignupVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            otp = (
                EmailOTP.objects.filter(
                    email=pending["email"],
                    purpose=OTPPurpose.SIGNUP,
                    used=False,
                )
                .order_by("-created_at")
                .first()
            )
            if not otp or not otp.is_valid():
                form.add_error("code", "Invalid or expired code. Request a new one from signup.")
            elif otp.code != code:
                form.add_error("code", "Incorrect code.")
            else:
                otp.mark_used()
                user = User.objects.create_user(
                    email=pending["email"],
                    password=pending["password"],
                    first_name=pending.get("first_name", ""),
                    last_name=pending.get("last_name", ""),
                    phone=pending.get("phone", ""),
                )
                request.session.pop("pending_signup", None)
                login(request, user)
                request.session["chat_access_verified"] = True
                messages.success(request, "Account created. Welcome to SmartChat!")
                return redirect("chat:inbox")
    else:
        form = SignupVerifyForm()
    return render(request, "accounts/signup_verify.html", {"form": form, "email": pending["email"]})


@require_http_methods(["GET", "POST"])
def login_request(request):
    if request.user.is_authenticated:
        return redirect("chat:inbox")

    if request.method == "POST":
        form = LoginRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            otp = EmailOTP.create_for_email(email, OTPPurpose.LOGIN)
            if not _send_otp_email(otp.email, otp.code, "login"):
                otp.delete()
                messages.error(
                    request,
                    "Could not send the email. Check SMTP settings and the server logs.",
                )
            else:
                request.session["pending_login_email"] = email
                request.session.pop("chat_access_verified", None)
                messages.info(
                    request,
                    "We sent a login code to your email. "
                    "With DEBUG=True you can also see the code in the terminal.",
                )
                return redirect("accounts:login_verify")
    else:
        form = LoginRequestForm()
    return render(request, "accounts/login_request.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_verify(request):
    if request.user.is_authenticated:
        return redirect("chat:inbox")
    email = request.session.get("pending_login_email")
    if not email:
        messages.warning(request, "Enter your email to receive a login code.")
        return redirect("accounts:login")

    if request.method == "POST":
        form = LoginVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            otp = (
                EmailOTP.objects.filter(
                    email=email,
                    purpose=OTPPurpose.LOGIN,
                    used=False,
                )
                .order_by("-created_at")
                .first()
            )
            if not otp or not otp.is_valid():
                form.add_error("code", "Invalid or expired code. Request a new login code.")
            elif otp.code != code:
                form.add_error("code", "Incorrect code.")
            else:
                otp.mark_used()
                user = User.objects.get(email=email)
                login(request, user)
                request.session.pop("pending_login_email", None)
                request.session["chat_access_verified"] = True
                messages.success(request, "You are logged in.")
                return redirect("chat:inbox")
    else:
        form = LoginVerifyForm()
    return render(request, "accounts/login_verify.html", {"form": form, "email": email})


def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    request.session.pop("chat_access_verified", None)
    messages.info(request, "You have been logged out.")
    return redirect("accounts:login")
