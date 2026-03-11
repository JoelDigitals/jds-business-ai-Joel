"""
JDS Business AI - AI Engine Models
Konversationen, Nachrichten, KI-Analyse
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import User


class Conversation(models.Model):
    """
    Eine Konversation / Chat-Session
    """
    TOPIC_CHOICES = [
        ('general', 'Allgemein'),
        ('founding', 'Unternehmensgründung'),
        ('business_plan', 'Businessplan'),
        ('legal', 'Rechtsfragen'),
        ('finance', 'Finanzplanung'),
        ('marketing', 'Marketing & Vertrieb'),
        ('hr', 'Personal & HR'),
        ('tax', 'Steuern'),
        ('contracts', 'Verträge'),
        ('strategy', 'Strategie'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, default='Neue Konversation')
    topic = models.CharField(max_length=50, choices=TOPIC_CHOICES, default='general')
    is_active = models.BooleanField(default=True)

    # Metadaten
    message_count = models.IntegerField(default=0)
    summary = models.TextField(blank=True)  # KI-generierte Zusammenfassung

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Konversation')
        verbose_name_plural = _('Konversationen')
        db_table = 'jds_conversations'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"

    def get_context_messages(self, limit: int = 10) -> list:
        """Gibt die letzten N Nachrichten als Kontext zurück"""
        messages = self.messages.order_by('-created_at')[:limit]
        return list(reversed(messages))


class Message(models.Model):
    """
    Einzelne Nachricht in einer Konversation
    """
    ROLE_CHOICES = [
        ('user', 'Benutzer'),
        ('assistant', 'JDS AI'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()

    # KI-Metadaten
    reasoning_steps = models.JSONField(default=list)  # "Gedankenkette" der KI
    business_category = models.CharField(max_length=50, blank=True)  # Automatisch erkannte Kategorie
    confidence_score = models.FloatField(default=1.0)  # Konfidenz der Antwort
    sources_used = models.JSONField(default=list)  # Verwendete Wissensbases

    # Bild-Upload (für Pro/Business)
    image = models.ImageField(upload_to='chat_images/%Y/%m/', null=True, blank=True)
    image_analysis = models.TextField(blank=True)  # KI-Analyse des Bildes

    # Tokens/Zeichen
    char_count = models.IntegerField(default=0)
    processing_time_ms = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Nachricht')
        verbose_name_plural = _('Nachrichten')
        db_table = 'jds_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}..."

    def save(self, *args, **kwargs):
        self.char_count = len(self.content)
        super().save(*args, **kwargs)


class BusinessDocument(models.Model):
    """
    Von der KI generierte Businessdokumente
    (Businessplan, Pitch Deck, Vertragsvorlage, etc.)
    """
    DOC_TYPES = [
        ('business_plan', 'Businessplan'),
        ('pitch_deck_outline', 'Pitch Deck Gliederung'),
        ('executive_summary', 'Executive Summary'),
        ('market_analysis', 'Marktanalyse'),
        ('financial_plan', 'Finanzplan'),
        ('legal_checklist', 'Rechtliche Checkliste'),
        ('contract_template', 'Vertragsvorlage'),
        ('founding_checklist', 'Gründungs-Checkliste'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, related_name='documents')

    doc_type = models.CharField(max_length=50, choices=DOC_TYPES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    version = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Business-Dokument')
        db_table = 'jds_documents'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.get_doc_type_display()})"
