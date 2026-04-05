import secrets
import string

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True, db_index=True)
    phone = models.CharField(max_length=32, blank=True, default="")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email


class OTPPurpose(models.TextChoices):
    SIGNUP = "signup", "Signup"
    LOGIN = "login", "Login"


class EmailOTP(models.Model):
    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=16, choices=OTPPurpose.choices, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "accounts_email_otp"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "purpose", "used"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.purpose})"

    @classmethod
    def generate_code(cls):
        return "".join(secrets.choice(string.digits) for _ in range(6))

    @classmethod
    def create_for_email(cls, email, purpose):
        minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 5)
        return cls.objects.create(
            email=email.lower().strip(),
            code=cls.generate_code(),
            purpose=purpose,
            expires_at=timezone.now() + timezone.timedelta(minutes=minutes),
        )

    def is_valid(self):
        if self.used:
            return False
        return timezone.now() <= self.expires_at

    def mark_used(self):
        self.used = True
        self.save(update_fields=["used"])
