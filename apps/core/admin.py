"""JDS Business AI - Admin Configuration"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Subscription, GDPRLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'company_name', 'get_plan', 'is_active', 'created_at']
    list_filter = ['is_active', 'subscription__plan', 'country']
    search_fields = ['email', 'username', 'company_name']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Business', {'fields': ('company_name', 'industry', 'country')}),
        ('DSGVO', {'fields': ('gdpr_consent', 'gdpr_consent_date', 'data_deletion_requested')}),
    )

    def get_plan(self, obj):
        try:
            return obj.subscription.plan
        except:
            return '-'
    get_plan.short_description = 'Plan'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'messages_today', 'total_messages', 'is_active', 'started_at']
    list_filter = ['plan', 'is_active']
    search_fields = ['user__email']

    actions = ['reset_daily_usage']

    def reset_daily_usage(self, request, queryset):
        for sub in queryset:
            sub.messages_today = 0
            sub.images_today = 0
            sub.save()
        self.message_user(request, f'{queryset.count()} Abonnements zurückgesetzt.')
    reset_daily_usage.short_description = "Tägliche Nutzung zurücksetzen"


@admin.register(GDPRLog)
class GDPRLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'timestamp']
    list_filter = ['action']
    search_fields = ['user__email']
    readonly_fields = ['id', 'user', 'action', 'ip_address', 'timestamp', 'details']

    def has_add_permission(self, request):
        return False  # GDPR-Logs nur lesen, nicht manuell erstellen

    def has_change_permission(self, request, obj=None):
        return False  # Unveränderlich
