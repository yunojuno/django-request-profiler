
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from models import RuleSet, ProfilingRecord


class RuleSetAdmin(ModelAdmin):

    list_display = (
        'catch_all',
        'uri_regex',
        'user_id',
        'user_group_name',
        'user_function_name',
    )

admin.site.register(
    RuleSet,
    RuleSetAdmin
)


class ProfilingRecordAdmin(ModelAdmin):

    list_display = (
        'start_ts',
        'end_ts',
        'duration',
        'user_id',
        'uri',
    )

admin.site.register(
    ProfilingRecord,
    ProfilingRecordAdmin
)
