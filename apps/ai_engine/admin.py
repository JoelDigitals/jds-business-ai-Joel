"""JDS AI Engine - Admin"""
from django.contrib import admin
from .models import Conversation, Message, BusinessDocument


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'topic', 'message_count', 'is_active', 'created_at']
    list_filter = ['topic', 'is_active']
    search_fields = ['user__email', 'title']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role', 'business_category', 'char_count', 'processing_time_ms', 'created_at']
    list_filter = ['role', 'business_category']


@admin.register(BusinessDocument)
class BusinessDocumentAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'doc_type', 'version', 'created_at']
    list_filter = ['doc_type']
