from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core import validators
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):

    # override this method
    def _create_user(
        self,
        mobile_number,
        password,
        is_staff=False,
        is_superuser=False,
        **extra_fields
    ):
        date_joined = timezone.now()
        if not mobile_number:
            raise ValueError("The given mobile number must be set")

        user = self.model(
            mobile_number=mobile_number,
            is_staff=is_staff,
            is_active=True,
            is_superuser=is_superuser,
            date_joined=date_joined,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, mobile_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(mobile_number, password, **extra_fields)

    def create_superuser(self, mobile_number, password, **extra_fields):
        return self._create_user(mobile_number, password, True, True, **extra_fields)


class CustomUser(AbstractBaseUser):
    mobile_number = models.CharField(
        unique=True,
        max_length=32,
        validators=[
            validators.RegexValidator(
                r"^\+\d+-\d+$",
                (
                    "Enter a valid mobile number. "
                    "mobile number format is +<country_code>-<phone number>"
                ),
                "invalid",
            )
        ],
    )

    name = models.CharField(max_length=32, blank=True, default="")
    email = models.EmailField(unique=True, null=True)
    is_active = models.BooleanField("active", default=True)
    is_staff = models.BooleanField("staff status", default=False)
    date_joined = models.DateTimeField("date joined", default=timezone.now)

    USERNAME_FIELD = "mobile_number"
    REQUIRED_FIELDS = ["date_joined"]

    objects = CustomUserManager()

    class Meta:
        app_label = "test_app"

    def get_full_name(self):
        return self.mobile_number

    def get_short_name(self):
        return self.mobile_number
