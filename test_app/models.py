# Required to prevent coverage runner complaining
# models definitions for testing
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Group, Permission
from django.core import validators
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class CustomPermissionsMixin(models.Model):
    """
    A mixin class that adds the fields and methods necessary to support
    Django's Group and Permission model using the ModelBackend.
    """
    is_superuser = models.BooleanField(
        _('superuser status'),
        default=False,
        help_text=_(
            'Designates that this user has all permissions without '
            'explicitly assigning them.'
        ),
    )
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )

    class Meta:
        abstract = True

    def get_group_permissions(self, obj=None):
        """
        Returns a list of permission strings that this user has through their
        groups. This method queries all available auth backends. If an object
        is passed in, only permissions matching this object are returned.
        """
        permissions = set()
        for backend in auth.get_backends():
            if hasattr(backend, "get_group_permissions"):
                permissions.update(backend.get_group_permissions(self, obj))
        return permissions

    def get_all_permissions(self, obj=None):
        return _user_get_all_permissions(self, obj)

    def has_perm(self, perm, obj=None):
        """
        Returns True if the user has the specified permission. This method
        queries all available auth backends, but returns immediately if any
        backend returns True. Thus, a user who has permission from a single
        auth backend is assumed to have permission in general. If an object is
        provided, permissions for this specific object are checked.
        """

        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        """
        Returns True if the user has each of the specified permissions. If
        object is passed, it checks if the user has all required perms for this
        object.
        """
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, app_label):
        """
        Returns True if the user has any permissions in the given app label.
        Uses pretty much the same logic as has_perm, above.
        """
        # Active superusers have all permissions.
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)

class CustomUserManager(BaseUserManager):

    # override this method
    def _create_user(self, mobile_number, password,
                     is_staff=False, is_superuser=False, **extra_fields):
        date_joined = timezone.now()
        if not mobile_number:
            raise ValueError('The given mobile number must be set')

        user = self.model(
            mobile_number=mobile_number,
            is_staff=is_staff, is_active=True, is_superuser=is_superuser,
            date_joined=date_joined, **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, mobile_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(mobile_number, password, **extra_fields)

    def create_superuser(self, mobile_number, password, **extra_fields):
        return self._create_user(mobile_number, password, True, True,
                                 **extra_fields)

class CustomUser(AbstractBaseUser, CustomPermissionsMixin):
    mobile_number = models.CharField(unique=True, max_length=32,
                        validators=[
                            validators.RegexValidator(r'^\+\d+-\d+$',
                                ('Enter a valid mobile number. '
                                 'mobile number format is +<country_code>-<phone number>'),
                                'invalid'),
                        ]
                    )

    name = models.CharField(max_length=32, blank=True, default='')
    email = models.EmailField(unique=True, null=True)

    is_active = models.BooleanField('active', default=True)
    is_staff = models.BooleanField('staff status', default=False)
    date_joined = models.DateTimeField('date joined', default=timezone.now)

    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = ['date_joined']

    objects = CustomUserManager()

    class Meta:
        app_label = 'test_app'

    def get_full_name(self):
        return self.mobile_number

    def get_short_name(self):
        return self.mobile_number
