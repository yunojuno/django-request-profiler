from unittest import skipIf

from django.conf import settings


def skipIfDefaultUser(test_func):
    """Skip a test if a default user model is in use."""
    return skipIf(settings.AUTH_USER_MODEL == "auth.User", "Default user model in use")(
        test_func
    )


def skipIfCustomUser(test_func):
    """Skip a test if a custom user model is in use."""
    return skipIf(settings.AUTH_USER_MODEL != "auth.User", "Custom user model in use")(
        test_func
    )
