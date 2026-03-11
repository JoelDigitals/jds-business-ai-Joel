"""
JDS Business AI - API Key Authentication
Für externe Entwickler-API
"""
import hashlib
import secrets
import logging
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from apps.core.models import User

logger = logging.getLogger('apps.api')


class APIKey(models.Model):
    """
    API-Keys für Entwickler (Pro und Business Plan)
    """
    import uuid as _uuid

    id = models.UUIDField(primary_key=True, default=models.UUIDField.default if hasattr(models.UUIDField, 'default') else None, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100, help_text="Name des API-Keys (z.B. 'Mein App Backend')")

    # Der eigentliche Key (gehasht gespeichert)
    key_prefix = models.CharField(max_length=8, unique=True)  # Für Anzeige: jds_abc12345
    key_hash = models.CharField(max_length=64)  # SHA-256 Hash

    # Berechtigungen
    can_chat = models.BooleanField(default=True)
    can_generate_documents = models.BooleanField(default=False)
    can_read_conversations = models.BooleanField(default=False)

    # Rate Limiting
    requests_today = models.IntegerField(default=0)
    requests_total = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    last_reset_date = models.DateField(default=timezone.now)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('API-Key')
        verbose_name_plural = _('API-Keys')
        db_table = 'jds_api_keys'

    def __str__(self):
        return f"jds_{self.key_prefix}... ({self.user.email})"

    def save(self, *args, **kwargs):
        if not self.id:
            import uuid
            self.id = uuid.uuid4()
        super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls, user, name: str, **permissions) -> tuple:
        """
        Generiert einen neuen API-Key.
        Returns: (api_key_object, plain_key_string)
        """
        # Prüfe ob Nutzer API-Zugang hat
        subscription = user.get_subscription()
        if not subscription.has_api_access():
            raise PermissionError("API-Zugang erfordert Pro oder Business Plan.")

        # Generiere sicheren Key
        plain_key = f"jds_{secrets.token_hex(24)}"  # z.B.: jds_abc123...
        prefix = plain_key[4:12]  # Ersten 8 Chars nach 'jds_'
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()

        api_key = cls.objects.create(
            user=user,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            can_generate_documents=subscription.plan == 'business',
            can_read_conversations=True,
            **permissions
        )

        logger.info(f"Neuer API-Key erstellt für {user.email}: jds_{prefix}...")
        return api_key, plain_key

    def verify(self, plain_key: str) -> bool:
        """Verifiziert einen Plain-Text API-Key"""
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        return self.key_hash == key_hash

    def record_usage(self):
        """Zählt API-Nutzung"""
        today = timezone.now().date()
        if self.last_reset_date < today:
            self.requests_today = 0
            self.last_reset_date = today

        self.requests_today += 1
        self.requests_total += 1
        self.last_used = timezone.now()
        self.save(update_fields=['requests_today', 'requests_total', 'last_used', 'last_reset_date'])

    def get_daily_limit(self) -> int:
        subscription = self.user.get_subscription()
        limits = {
            'pro': 500,
            'business': 10000,
        }
        return limits.get(subscription.plan, 0)

    def is_within_rate_limit(self) -> bool:
        today = timezone.now().date()
        if self.last_reset_date < today:
            return True
        return self.requests_today < self.get_daily_limit()


class APIKeyAuthentication(BaseAuthentication):
    """
    Django REST Framework Authentication mit API-Key.
    Header: X-API-Key: jds_abc123...
    """

    def authenticate(self, request):
        api_key_str = request.META.get('HTTP_X_API_KEY') or request.GET.get('api_key')

        if not api_key_str:
            return None  # Nicht diese Auth-Methode

        if not api_key_str.startswith('jds_'):
            raise AuthenticationFailed('Ungültiges API-Key Format. Erwartet: jds_...')

        prefix = api_key_str[4:12]  # 8 Chars nach 'jds_'

        try:
            api_key = APIKey.objects.select_related('user').get(
                key_prefix=prefix,
                is_active=True,
            )
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('Ungültiger API-Key.')

        if not api_key.verify(api_key_str):
            raise AuthenticationFailed('Ungültiger API-Key.')

        if api_key.expires_at and api_key.expires_at < timezone.now():
            raise AuthenticationFailed('API-Key abgelaufen.')

        if not api_key.is_within_rate_limit():
            raise AuthenticationFailed(
                f'API Rate-Limit erreicht ({api_key.get_daily_limit()} Anfragen/Tag). '
                'Upgrade auf Business für mehr!'
            )

        # Nutzung zählen
        api_key.record_usage()

        logger.info(f"API-Auth: {api_key.user.email} via jds_{prefix}...")
        return (api_key.user, api_key)

    def authenticate_header(self, request):
        return 'X-API-Key'
