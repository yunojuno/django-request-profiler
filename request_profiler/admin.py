from django.contrib import admin

from .models import ProfilingRecord, RuleSet


class RuleSetAdmin(admin.ModelAdmin):

    list_display = ("enabled", "uri_regex", "user_filter_type", "user_group_filter")


class ProfilingRecordAdmin(admin.ModelAdmin):

    list_display = (
        "start_ts",
        "user",
        "http_method",
        "request_uri",
        "view_func_name",
        "query_count",
        "response_status_code",
        "duration",
    )
    readonly_fields = (
        "user",
        "session_key",
        "start_ts",
        "end_ts",
        "remote_addr",
        "request_uri",
        "query_string",
        "view_func_name",
        "http_method",
        "http_user_agent",
        "http_referer",
        "response_status_code",
        "response_content_length",
        "query_count",
        "duration",
    )


admin.site.register(RuleSet, RuleSetAdmin)
admin.site.register(ProfilingRecord, ProfilingRecordAdmin)
