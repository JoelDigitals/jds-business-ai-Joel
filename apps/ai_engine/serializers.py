"""JDS Business AI - AI Engine Serializers"""
from rest_framework import serializers
from .models import Conversation, Message, BusinessDocument


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id', 'role', 'content', 'business_category',
            'confidence_score', 'reasoning_steps', 'processing_time_ms',
            'image', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'processing_time_ms']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    topic_display = serializers.CharField(source='get_topic_display', read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'topic', 'topic_display', 'is_active',
            'message_count', 'summary', 'created_at', 'updated_at', 'messages'
        ]
        read_only_fields = ['id', 'message_count', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1, max_length=50000)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    image = serializers.ImageField(required=False, allow_null=True)

    def validate_message(self, value):
        return value.strip()


class BusinessDocumentSerializer(serializers.ModelSerializer):
    doc_type_display = serializers.CharField(source='get_doc_type_display', read_only=True)

    class Meta:
        model = BusinessDocument
        fields = [
            'id', 'doc_type', 'doc_type_display', 'title', 'content',
            'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
