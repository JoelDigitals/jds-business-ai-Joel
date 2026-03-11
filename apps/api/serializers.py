"""JDS Business AI - API Serializers"""
from rest_framework import serializers
from .authentication import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    key_display = serializers.SerializerMethodField()
    daily_limit = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'key_display', 'is_active',
            'can_chat', 'can_generate_documents', 'can_read_conversations',
            'requests_today', 'requests_total', 'daily_limit',
            'last_used', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'created_at', 'requests_today', 'requests_total']

    def get_key_display(self, obj):
        return f"jds_{obj.key_prefix}..."

    def get_daily_limit(self, obj):
        return obj.get_daily_limit()


class APIKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, min_length=3)

    def validate_name(self, value):
        return value.strip()
