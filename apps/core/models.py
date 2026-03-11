"""
JDS Business AI - Core Models
Benutzerverwaltung, Abonnements, Zugangscodes, DSGVO-Compliance
"""
import uuid
import secrets
import string
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('E-Mail-Adresse'), unique=True)
    company_name = models.CharField(_('Firmenname'), max_length=200, blank=True)
    industry = models.CharField(_('Branche'), max_length=100, blank=True)
    country = models.CharField(_('Land'), max_length=2, default='DE')
    gdpr_consent = models.BooleanField(_('DSGVO-Einwilligung'), default=False)
    gdpr_consent_date = models.DateTimeField(_('Einwilligungsdatum'), null=True, blank=True)
    data_export_requested = models.BooleanField(default=False)
    data_deletion_requested = models.BooleanField(default=False)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('Benutzer')
        verbose_name_plural = _('Benutzer')
        db_table = 'jds_users'

    def __str__(self):
        return self.email

    def get_plan_display(self):
        try:
            return self.subscription.get_plan_display()
        except Exception:
            return 'Free'

    def get_subscription(self):
        try:
            return self.subscription
        except Subscription.DoesNotExist:
            return Subscription.objects.create(user=self, plan='free')

    def request_data_deletion(self):
        self.data_deletion_requested = True
        self.deletion_requested_at = timezone.now()
        self.save()

    def anonymize(self):
        self.email = f"deleted_{self.id}@anonymized.jds"
        self.username = f"deleted_{self.id}"
        self.first_name = "Gelöscht"
        self.last_name = "Nutzer"
        self.company_name = ""
        self.industry = ""
        self.is_active = False
        self.save()


class Subscription(models.Model):
    PLAN_CHOICES = [
        ('free',     'Free – Kostenlos'),
        ('pro',      'Pro – Einzelunternehmer'),
        ('business', 'Business – Unternehmen'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')

    # Billing
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    billing_period = models.CharField(
        max_length=10,
        choices=[('monthly', 'Monatlich'), ('yearly', 'Jährlich')],
        default='monthly',
    )

    # Tägliche Nutzung
    messages_today = models.IntegerField(default=0)
    images_today = models.IntegerField(default=0)
    last_reset_date = models.DateField(default=timezone.now)

    # Gesamt
    total_messages = models.IntegerField(default=0)
    total_images = models.IntegerField(default=0)

    class Meta:
        verbose_name = _('Abonnement')
        verbose_name_plural = _('Abonnements')
        db_table = 'jds_subscriptions'

    def __str__(self):
        return f"{self.user.email} – {self.plan}"

    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    def check_expiry(self):
        """Downgrade auf Free wenn abgelaufen"""
        if self.is_expired() and self.plan != 'free':
            self.plan = 'free'
            self.expires_at = None
            self.billing_period = 'monthly'
            self.save(update_fields=['plan', 'expires_at', 'billing_period'])

    def reset_daily_limits_if_needed(self):
        self.check_expiry()
        today = timezone.now().date()
        if self.last_reset_date < today:
            self.messages_today = 0
            self.images_today = 0
            self.last_reset_date = today
            self.save(update_fields=['messages_today', 'images_today', 'last_reset_date'])

    def get_limits(self):
        from django.conf import settings
        return settings.PLAN_LIMITS.get(self.plan, settings.PLAN_LIMITS['free'])

    def can_send_message(self, char_count: int = 0):
        self.reset_daily_limits_if_needed()
        limits = self.get_limits()
        if self.messages_today >= limits['messages_per_day']:
            return False, f"Tageslimit erreicht ({limits['messages_per_day']}/Tag). Upgrade für mehr!"
        if char_count > limits['chars_per_message']:
            return False, f"Nachricht zu lang. Max. {limits['chars_per_message']} Zeichen."
        return True, "ok"

    def can_upload_image(self):
        self.reset_daily_limits_if_needed()
        limits = self.get_limits()
        if self.images_today >= limits['image_uploads_per_day']:
            return False, f"Bild-Limit erreicht ({limits['image_uploads_per_day']}/Tag)."
        return True, "ok"

    def increment_usage(self, message=True, image=False):
        if message:
            self.messages_today += 1
            self.total_messages += 1
        if image:
            self.images_today += 1
            self.total_images += 1
        self.save(update_fields=['messages_today', 'total_messages', 'images_today', 'total_images'])

    def has_api_access(self):
        return self.plan in ('pro', 'business')

    def get_remaining_messages(self):
        limits = self.get_limits()
        return max(0, limits['messages_per_day'] - self.messages_today)


# ─────────────────────────────────────────────────────────────
# ZUGANGSCODES
# ─────────────────────────────────────────────────────────────

def _generate_code():
    """Erzeugt einen lesbaren 16-Zeichen Code: JDS-XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(secrets.choice(chars) for _ in range(4)) for _ in range(3)]
    return 'JDS-' + '-'.join(parts)


class AccessCode(models.Model):
    PLAN_CHOICES = [
        ('pro',      'Pro'),
        ('business', 'Business'),
    ]
    PERIOD_CHOICES = [
        ('monthly', '1 Monat'),
        ('yearly',  '1 Jahr'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, default=_generate_code)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='monthly')

    # Status
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='redeemed_codes')
    used_at = models.DateTimeField(null=True, blank=True)

    # Meta
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_codes')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Wann läuft der Code selbst ab (nicht der Plan)")
    note = models.CharField(max_length=200, blank=True, help_text="Interne Notiz")

    class Meta:
        verbose_name = 'Zugangscode'
        verbose_name_plural = 'Zugangscodes'
        db_table = 'jds_access_codes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.plan}/{self.period}) – {'genutzt' if self.is_used else 'offen'}"

    def is_valid(self):
        if self.is_used:
            return False, "Code wurde bereits eingelöst."
        if self.expires_at and timezone.now() > self.expires_at:
            return False, "Code ist abgelaufen."
        return True, "ok"

    def redeem(self, user):
        """Löst den Code ein und updatet das Abonnement des Users."""
        valid, msg = self.is_valid()
        if not valid:
            return False, msg

        sub, _ = Subscription.objects.get_or_create(user=user)

        # Laufzeit berechnen
        now = timezone.now()
        if self.period == 'yearly':
            delta = timedelta(days=365)
        else:
            delta = timedelta(days=30)

        # Wenn noch aktiver Plan → Laufzeit addieren, sonst neu starten
        if sub.expires_at and sub.expires_at > now and sub.plan == self.plan:
            sub.expires_at = sub.expires_at + delta
        else:
            sub.expires_at = now + delta

        sub.plan = self.plan
        sub.billing_period = self.period
        sub.is_active = True
        sub.save()

        self.is_used = True
        self.used_by = user
        self.used_at = now
        self.save()

        return True, f"✅ {self.get_plan_display()} ({self.get_period_display()}) aktiviert bis {sub.expires_at.strftime('%d.%m.%Y')}!"


class GDPRLog(models.Model):
    ACTION_CHOICES = [
        ('consent_given', 'Einwilligung erteilt'),
        ('consent_withdrawn', 'Einwilligung widerrufen'),
        ('data_export', 'Datenexport'),
        ('data_deletion', 'Datenlöschung'),
        ('data_deleted', 'Daten gelöscht'),
        ('login', 'Anmeldung'),
        ('logout', 'Abmeldung'),
        ('profile_updated', 'Profil aktualisiert'),
        ('code_redeemed', 'Code eingelöst'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='gdpr_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'DSGVO-Log'
        verbose_name_plural = 'DSGVO-Logs'
        db_table = 'jds_gdpr_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} – {self.action} – {self.timestamp}"
