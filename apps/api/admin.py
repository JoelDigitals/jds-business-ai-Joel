"""JDS API - Admin"""
from django.contrib import admin
from .authentication import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'key_display', 'requests_today', 'requests_total', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['user__email', 'name']
    readonly_fields = ['key_hash', 'key_prefix', 'requests_today', 'requests_total']

    def key_display(self, obj):
        return f"jds_{obj.key_prefix}..."
    key_display.short_description = 'API Key'
