"""
JDS Business AI - Core Serializers
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import User, Subscription, GDPRLog


class SubscriptionSerializer(serializers.ModelSerializer):
    limits = serializers.SerializerMethodField()
    remaining_messages = serializers.SerializerMethodField()
    plan_display = serializers.CharField(source='get_plan_display', read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'plan', 'plan_display', 'started_at', 'expires_at', 'is_active',
            'messages_today', 'images_today', 'total_messages', 'total_images',
            'limits', 'remaining_messages'
        ]
        read_only_fields = ['started_at', 'messages_today', 'images_today']

    def get_limits(self, obj):
        return obj.get_limits()

    def get_remaining_messages(self, obj):
        return obj.get_remaining_messages()


class UserSerializer(serializers.ModelSerializer):
    subscription = SubscriptionSerializer(read_only=True)
    has_api_access = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'company_name', 'industry', 'country',
            'gdpr_consent', 'gdpr_consent_date',
            'created_at', 'subscription', 'has_api_access'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'gdpr_consent_date']

    def get_has_api_access(self, obj):
        return obj.get_subscription().has_api_access()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    gdpr_consent = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password2',
                  'first_name', 'last_name', 'company_name', 'gdpr_consent']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwörter stimmen nicht überein."})
        if not attrs.get('gdpr_consent'):
            raise serializers.ValidationError({"gdpr_consent": "DSGVO-Einwilligung ist erforderlich."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        validated_data['gdpr_consent_date'] = timezone.now()

        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data.get('username', validated_data['email'].split('@')[0]),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            company_name=validated_data.get('company_name', ''),
            gdpr_consent=True,
            gdpr_consent_date=validated_data['gdpr_consent_date'],
        )

        # Free Subscription automatisch erstellen
        Subscription.objects.create(user=user, plan='free')

        return user


class GDPRExportSerializer(serializers.ModelSerializer):
    """Datenexport gemäß DSGVO Art. 20"""
    subscription = SubscriptionSerializer(read_only=True)
    gdpr_logs = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'company_name', 'industry', 'country',
            'gdpr_consent', 'gdpr_consent_date', 'created_at',
            'subscription', 'gdpr_logs'
        ]

    def get_gdpr_logs(self, obj):
        logs = obj.gdpr_logs.all()[:100]
        return [{'action': l.action, 'timestamp': l.timestamp} for l in logs]
