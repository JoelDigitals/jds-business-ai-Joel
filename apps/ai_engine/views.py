"""
JDS Business AI - AI Engine Views (Vollständig überarbeitet)
===============================================================
Haupt-Chat-Endpunkte und Konversationsverwaltung

Architektur des Chat-Flows:
    Request → Limit-Check → Konversation laden/erstellen
    → Reasoning Engine (Kategorie, Strategie)
    → Spezial-Handler (Legal / Business / Founding)
    → LLM (lokal, kostenlos) mit Rule-Based Fallback
    → Disclaimer → Speichern (atomar) → Response
===============================================================
"""
import logging
import time
import json
from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import StreamingHttpResponse, HttpResponse

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication


# Standard-Auth für alle Views: JWT zuerst, Session als Fallback
# Damit funktionieren sowohl API-Clients (JWT) als auch Browser (Session-Cookie)
_DEFAULT_AUTH = [JWTAuthentication, SessionAuthentication]
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone

from .models import Conversation, Message, BusinessDocument
from .serializers import (
    ConversationSerializer, MessageSerializer,
    ChatRequestSerializer, BusinessDocumentSerializer
)
from .reasoning_engine import ReasoningEngine
from .llm_service import generate_response
from .business_logic import BusinessLogic, get_rule_based_response
from .legal_assistant import LegalAssistant
from .permissions import PlanPermission

logger = logging.getLogger('ai_engine')

# ─────────────────────────────────────────────────────────────
# Module-Level Singletons — einmal laden, dauerhaft nutzen
# ─────────────────────────────────────────────────────────────
_reasoning_engine = None
_business_logic = None
_legal_assistant = None


def get_reasoning_engine() -> ReasoningEngine:
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = ReasoningEngine()
    return _reasoning_engine


def get_business_logic() -> BusinessLogic:
    global _business_logic
    if _business_logic is None:
        _business_logic = BusinessLogic()
    return _business_logic


def get_legal_assistant() -> LegalAssistant:
    global _legal_assistant
    if _legal_assistant is None:
        _legal_assistant = LegalAssistant()
    return _legal_assistant


# ─────────────────────────────────────────────────────────────
# PRIVATE HILFSFUNKTIONEN
# ─────────────────────────────────────────────────────────────

def _get_or_create_conversation(user, conversation_id, first_message: str):
    """
    Lädt eine bestehende Konversation oder erstellt eine neue.
    Returns: (conversation | None, is_new: bool)
    """
    if conversation_id:
        try:
            conv = Conversation.objects.get(
                id=conversation_id,
                user=user,
                is_active=True
            )
            return conv, False
        except Conversation.DoesNotExist:
            return None, False

    # Titel aus erster Nachricht ableiten
    title = first_message[:60].strip()
    if len(first_message) > 60:
        cut = first_message[:60].rfind(' ')
        title = first_message[:cut if cut > 20 else 60] + '…'

    conv = Conversation.objects.create(user=user, title=title)
    return conv, True


def _route_to_specialist(category: str, user_message: str):
    """
    Leitet bestimmte Kategorien an Spezial-Handler weiter.
    Schneller als LLM — nutzt die eingebaute Wissensdatenbank.
    Returns: str (Antworttext) | None (→ LLM nutzen)
    """
    msg = user_message.lower()

    # Direkte Keyword-Erkennung — unabhängig von Reasoning-Kategorie.
    # Fängt Tippfehler ("bussiness") und unerkannte Kombinationen ab.
    BUSINESSPLAN_KEYWORDS = [
        'businessplan', 'business plan', 'bussiness plan', 'bussinesplan',
        'geschäftsplan', 'unternehmensplan', 'plan erstellen', 'plan schreiben',
        'pitch deck', 'executive summary',
    ]
    if category == 'business_plan' or any(k in msg for k in BUSINESSPLAN_KEYWORDS):
        from .business_logic import _generate_personalized_businessplan
        import re
        # NUR erste Zeile für Namen nutzen — verhindert Newline-Bug
        first_line = user_message.split('\n')[0].strip()
        name_match = re.search(
            r'(?:fuer|für|for|von|meiner\s+firma|firma|unternehmen|startup|company)[ \t]+'
            r'([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9 \t\-\.&]{1,40}?)'
            r'(?:[ \t]+(?:fuer|für|im|in|ab|vom|bis|gmbh|ug|ag)|[,\.?!]|$)',
            first_line, re.IGNORECASE
        )
        if not name_match:
            name_match = re.search(
                r'(?:businessplan|business plan|bussiness plan)[ \t]+(?:für[ \t]+|fuer[ \t]+)?'
                r'([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 \-\.&]{1,40}?)(?:[,\.?!]|$)',
                first_line, re.IGNORECASE
            )
        company_name = name_match.group(1).strip() if name_match else ''
        company_name = re.sub(r'^(meine\s+firma\s*|mein\s+unternehmen\s*|mein\s+startup\s*)', '', company_name, flags=re.IGNORECASE).strip()
        company_name = re.sub(r'\s*(wurde\s+am|gegründet|seit|\d{2}\.\d{2}|\b202\d\b).*$', '', company_name, flags=re.IGNORECASE).strip()
        return _generate_personalized_businessplan(company_name, user_message)

    # ── Dokument-Generierung erkennen (Intent-Check vor Category-Routing) ──
    import re as _re
    GENERATE_VERBS = [
        'schreib', 'erstell', 'generier', 'mach mir', 'formulier',
        'entwirf', 'verfass', 'gib mir', 'brauch', 'noch einmal',
        'nochmal', 'nochmal ein', 'neue', 'aktualis', 'mit folgenden',
    ]
    DOC_TYPES = {
        'impressum': ['impressum'],
        'datenschutz': ['datenschutz', 'datenschutzerklärung', 'privacy policy'],
        'agb': ['agb', 'allgemeine geschäftsbedingungen', 'nutzungsbedingungen'],
        'nda': ['nda', 'geheimhaltungsvertrag', 'vertraulichkeitsvereinbarung'],
        'arbeitsvertrag': ['arbeitsvertrag', 'anstellungsvertrag'],
        'rechnung': ['rechnungsvorlage', 'rechnungstemplate', 'musterrechnung'],
        'mahnschreiben': ['mahnung', 'mahnschreiben'],
    }
    detected_doc = None
    for doc_key, doc_keywords in DOC_TYPES.items():
        if any(k in msg for k in doc_keywords):
            detected_doc = doc_key
            break

    if detected_doc:
        from .document_generator import extract_structured_data
        from .llm_service import generate_response as llm_generate

        # Strukturierte Daten extrahieren
        struct = extract_structured_data(user_message)
        company_name = struct.get('company', '').strip()
        if not company_name:
            cm = _re.search(
                r'(?:für|fuer|for|von|meiner\s+firma|firma|unternehmen|startup)'
                r'[ \t]+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9 \-\.&]+?)'
                r'(?:\s+(?:mit|und|für|in|ab|vom|an|als|ist|hat|wurde|seit|gmbh|ug|ag)|[,\.?!\n]|$)',
                user_message.split('\n')[0], _re.IGNORECASE
            )
            company_name = cm.group(1).strip() if cm else ''

        # Bekannte Daten als strukturierten Kontext für das LLM aufbereiten
        known = []
        if company_name:                       known.append(f"Firma: {company_name}")
        fn = struct.get('first_name','')
        ln = struct.get('last_name','')
        if fn or ln:                           known.append(f"Inhaber: {fn} {ln}".strip())
        if struct.get('address'):              known.append(f"Adresse: {struct['address']}")
        if struct.get('email'):                known.append(f"E-Mail: {struct['email']}")
        if struct.get('phone'):                known.append(f"Telefon: {struct['phone']}")
        if struct.get('url'):                  known.append(f"Website: {struct['url']}")
        if struct.get('vat_id'):               known.append(f"USt-IdNr.: {struct['vat_id']}")
        if struct.get('no_vat'):               known.append("Umsatzsteuer: Keine (Kleinunternehmerregelung § 19 UStG)")
        if struct.get('rechtsform'):           known.append(f"Rechtsform: {struct['rechtsform']}")

        known_block = "\n".join(known) if known else "(keine Daten angegeben – Platzhalter verwenden)"

        doc_labels = {
            'impressum':      'Impressum gemäß § 5 TMG',
            'datenschutz':    'Datenschutzerklärung gemäß DSGVO',
            'agb':            'Allgemeine Geschäftsbedingungen',
            'nda':            'Geheimhaltungsvereinbarung (NDA)',
            'arbeitsvertrag': 'Arbeitsvertrag',
            'rechnung':       'Rechnungsvorlage',
            'mahnschreiben':  'Mahnschreiben',
        }
        doc_label = doc_labels.get(detected_doc, detected_doc)

        llm_prompt = f"""Erstelle ein vollständiges, professionelles Dokument: **{doc_label}**

Folgende Daten wurden vom Nutzer angegeben — verwende sie EXAKT so, ohne Platzhalter für bekannte Felder:
{known_block}

Regeln:
- Felder die bekannt sind: direkt eintragen, KEIN Platzhalter
- Felder die fehlen: als [Platzhalter] kennzeichnen und am Ende in einer kurzen Checkliste auflisten
- Format: sauberes Markdown mit ## Überschriften
- Sprache: Deutsch
- Keine unnötigen Erklärungen davor — starte direkt mit dem Dokument
- Am Ende: einzeiliger ⚖️ Hinweis dass dies eine Vorlage ist"""

        result = llm_generate(prompt=llm_prompt)
        llm_text = result.get('text', '').strip()

        # Fallback auf Template-Generator wenn LLM versagt
        if not llm_text or len(llm_text) < 100:
            from .document_generator import generate_document
            return generate_document(detected_doc, company_name, user_message, struct)

        return llm_text

    if category == 'legal':
        result = get_legal_assistant().analyze_legal_question(user_message)
        if result.get('response') and len(result['response']) > 50:
            return result['response']

    if category in ('founding', 'finance', 'tax', 'strategy', 'marketing'):
        response = get_rule_based_response(user_message)
        if response and 'Starte deinen ersten' not in response and len(response) > 100:
            return response

    return None


def _generate_ai_response(user_message: str, enhanced_prompt: str,
                           context_messages: list, category: str, user_info: dict = None) -> dict:
    """
    Generiert KI-Antwort über LLM, mit Rule-Based Fallback.
    Returns: {'text': str, 'model': str, 'fallback': bool, 'processing_time_ms': int}
    """
    ai_result = generate_response(
        prompt=enhanced_prompt or user_message,
        context_messages=context_messages,
        user_info=user_info,
    )

    text = ai_result.get('text', '').strip()
    is_fallback = ai_result.get('fallback', False)

    # Qualitätsprüfung: War LLM-Antwort brauchbar?
    is_good = (
        text
        and len(text) >= 30
        and not text.lower().startswith('ich kann')
        and not text.lower().startswith('als ki')
        and text.strip() != user_message.strip()
    )

    if not is_good:
        logger.info(f"LLM unbrauchbar (len={len(text)}), Rule-Based Fallback aktiviert")
        text = get_rule_based_response(user_message)
        is_fallback = True

    return {
        'text': text,
        'model': ai_result.get('model_used', 'rule-based'),
        'fallback': is_fallback,
        'processing_time_ms': ai_result.get('processing_time_ms', 0),
    }


def _handle_image_upload(request, subscription):
    """
    Verarbeitet optionalen Bild-Upload (Pro/Business).
    Returns: (image_file | None, note_text: str)
    """
    image = request.FILES.get('image')
    if not image:
        return None, ''

    can_upload, reason = subscription.can_upload_image()
    if not can_upload:
        return None, f'[Hinweis: Bild-Upload abgelehnt — {reason}]'

    if image.size > 10 * 1024 * 1024:
        return None, '[Hinweis: Bild zu groß — max. 10 MB erlaubt]'

    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if image.content_type not in allowed_types:
        return None, '[Hinweis: Ungültiger Dateityp. Erlaubt: JPG, PNG, WebP, GIF]'

    subscription.increment_usage(image=True)
    return image, '[Bild erfolgreich hochgeladen]'


# ─────────────────────────────────────────────────────────────
# HAUPT-CHAT-VIEW
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class ChatView(APIView):
    """
    POST /chat/message/

    Haupt-Chat-Endpunkt. Verarbeitet Nutzernachricht und
    gibt KI-Antwort zurück.

    Request Body (multipart/form-data oder JSON):
        message          : str  — Nutzernachricht (Pflicht)
        conversation_id  : UUID — Bestehende Konversation (optional)
        image            : File — Bild-Upload (optional, nur Pro/Business)

    Response 200:
        conversation_id    : UUID
        message_id         : UUID
        response           : str
        category           : str   — Erkannte Business-Kategorie
        confidence         : float
        reasoning_steps    : list
        recommended_tools  : list
        model_used         : str
        is_fallback        : bool
        processing_time_ms : int
        remaining_messages : int
        plan               : str
        is_new_conversation: bool

    Response 429: Limit erreicht
    Response 404: Konversation nicht gefunden
    Response 400: Validierungsfehler
    """
    # JWT + SessionAuthentication ohne CSRF-Zwang
    # SessionAuthentication wird NICHT verwendet — sie erzwingt CSRF bei POST.
    # Die View ist @csrf_exempt + JWT-geschützt.
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        start_time = time.time()

        # ── SCHRITT 1: Request validieren ─────────────────────
        # Daten normalisieren — funktioniert für FormData UND JSON
        raw_message = (
            request.data.get('message') or
            request.POST.get('message') or
            ''
        )
        if isinstance(raw_message, list):  # QueryDict gibt manchmal Liste zurück
            raw_message = raw_message[0] if raw_message else ''
        
        conv_id = (request.data.get('conversation_id') or request.POST.get('conversation_id') or None)
        if isinstance(conv_id, list):
            conv_id = conv_id[0] if conv_id else None

        logger.info(
            f"Chat POST | message_len={len(raw_message)} | conv={conv_id} | "
            f"data_keys={list(request.data.keys())} | content_type={request.content_type}"
        )

        normalized_data = {
            'message': raw_message,
            'conversation_id': conv_id,
        }
        if request.FILES.get('image'):
            normalized_data['image'] = request.FILES['image']

        serializer = ChatRequestSerializer(data=normalized_data)
        if not serializer.is_valid():
            logger.warning(f"Validierungsfehler: {serializer.errors} | data={dict(request.data)}")
            # Fehler-Detail als lesbaren String zurückgeben
            error_detail = '; '.join(
                f"{field}: {', '.join(str(e) for e in errs)}"
                for field, errs in serializer.errors.items()
            )
            return Response(
                {
                    'error': 'invalid_request',
                    'detail': error_detail,
                    'message': error_detail,
                    'fields': serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        subscription = user.get_subscription()
        data = serializer.validated_data
        user_message: str = data['message']
        conversation_id = data.get('conversation_id')

        logger.info(
            f"Chat | user={user.email} | conv={conversation_id} | "
            f"len={len(user_message)} | plan={subscription.plan}"
        )

        # ── SCHRITT 2: Plan-Limits prüfen ─────────────────────
        can_send, limit_reason = subscription.can_send_message(len(user_message))
        if not can_send:
            logger.info(f"Limit erreicht für {user.email}: {limit_reason}")
            return Response({
                'error': 'limit_exceeded',
                'message': limit_reason,
                'upgrade_url': '/#pricing',
                'remaining_messages': 0,
                'plan': subscription.plan,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # ── SCHRITT 3: Konversation laden / erstellen ──────────
        conversation, is_new = _get_or_create_conversation(
            user, conversation_id, user_message
        )
        if conversation is None:
            return Response(
                {'error': 'conversation_not_found',
                 'message': 'Konversation nicht gefunden oder gehört nicht dir.'},
                status=status.HTTP_404_NOT_FOUND
            )

        limits = subscription.get_limits()
        context_messages = conversation.get_context_messages(
            limit=limits.get('conversation_history', 5)
        )

        # ── SCHRITT 4: Bild-Upload verarbeiten ─────────────────
        uploaded_image, image_note = _handle_image_upload(request, subscription)
        effective_message = (
            f"{user_message}\n\n{image_note}" if image_note else user_message
        )

        # ── SCHRITT 5: Reasoning Engine ────────────────────────
        reasoning = get_reasoning_engine().analyze(effective_message, context_messages)

        logger.info(
            f"Reasoning | category={reasoning.category} | "
            f"confidence={reasoning.confidence:.2f} | "
            f"tools={reasoning.recommended_tools}"
        )

        # Konversations-Topic setzen (nur wenn noch 'general')
        if conversation.topic == 'general' and reasoning.category != 'general':
            Conversation.objects.filter(pk=conversation.pk).update(
                topic=reasoning.category
            )
            conversation.topic = reasoning.category

        # ── SCHRITT 6: Antwort generieren ──────────────────────
        # Priorität: Spezial-Handler → LLM → Rule-Based Fallback

        ai_response_text = None
        model_used = 'unknown'
        is_fallback = False

        # 6a. Spezial-Handler (präzise, ohne LLM-Latenz)
        specialist_response = _route_to_specialist(reasoning.category, user_message)
        if specialist_response:
            ai_response_text = specialist_response
            model_used = f'specialist:{reasoning.category}'
            logger.info(f"Spezial-Handler aktiv: {reasoning.category}")

        # 6b. LLM + Fallback
        if not ai_response_text:
            user_info = {
                'name': f"{user.first_name} {user.last_name}".strip(),
                'company': getattr(user, 'company_name', ''),
                'plan': subscription.plan,
            }
            ai_result = _generate_ai_response(
                user_message=user_message,
                enhanced_prompt=reasoning.enhanced_prompt,
                context_messages=context_messages,
                category=reasoning.category,
                user_info=user_info,
            )
            ai_response_text = ai_result['text']
            model_used = ai_result['model']
            is_fallback = ai_result['fallback']

        # 6c. Absolutes Sicherheitsnetz
        if not ai_response_text or len(ai_response_text.strip()) < 10:
            ai_response_text = get_rule_based_response(user_message)
            model_used = 'rule-based:safety-net'
            is_fallback = True

        # ── SCHRITT 7: Rechtliche Disclaimer anfügen ───────────
        ai_response_text = get_reasoning_engine().add_disclaimers(
            ai_response_text, reasoning
        )

        processing_time = int((time.time() - start_time) * 1000)

        # ── SCHRITT 8: Atomisch speichern ─────────────────────
        with transaction.atomic():
            Message.objects.create(
                conversation=conversation,
                role='user',
                content=user_message,
                image=uploaded_image,
            )

            ai_msg = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=ai_response_text,
                reasoning_steps=reasoning.reasoning_steps,
                business_category=reasoning.category,
                confidence_score=round(reasoning.confidence, 3),
                sources_used=[model_used],
                processing_time_ms=processing_time,
            )

            Conversation.objects.filter(pk=conversation.pk).update(
                message_count=conversation.message_count + 2
            )

            subscription.increment_usage(message=True)

        logger.info(
            f"Chat done | model={model_used} | "
            f"time={processing_time}ms | fallback={is_fallback}"
        )

        # ── SCHRITT 9: PDF anbieten wenn sinnvoll ─────────────
        from .pdf_service import is_pdf_worthy
        offer_pdf = is_pdf_worthy(ai_response_text)

        # ── SCHRITT 10: Response ───────────────────────────────
        return Response({
            'conversation_id': str(conversation.id),
            'message_id': str(ai_msg.id),
            'response': ai_response_text,
            'category': reasoning.category,
            'confidence': round(reasoning.confidence, 3),
            'reasoning_steps': reasoning.reasoning_steps,
            'recommended_tools': reasoning.recommended_tools,
            'model_used': model_used,
            'is_fallback': is_fallback,
            'processing_time_ms': processing_time,
            'offer_pdf': offer_pdf,
            'pdf_url': f'/chat/message/{str(ai_msg.id)}/pdf/' if offer_pdf else None,
            'remaining_messages': subscription.get_remaining_messages(),
            'plan': subscription.plan,
            'conversation_title': conversation.title,
            'is_new_conversation': is_new,
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# KONVERSATIONS-VIEWS
# ─────────────────────────────────────────────────────────────

class ConversationListView(generics.ListCreateAPIView):
    """
    GET  /chat/conversations/  — Konversationen auflisten
    POST /chat/conversations/  — Neue Konversation erstellen

    Query-Params (GET):
        ?topic=legal        — Nach Thema filtern
        ?search=GmbH        — Titelsuche (case-insensitive)
        ?ordering=-updated_at
    """
    serializer_class = ConversationSerializer
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Conversation.objects.filter(
            user=self.request.user, is_active=True
        )
        topic = self.request.query_params.get('topic')
        if topic:
            qs = qs.filter(topic=topic)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(title__icontains=search)

        ordering = self.request.query_params.get('ordering', '-updated_at')
        valid_orderings = ['-updated_at', 'updated_at', '-created_at', 'title']
        qs = qs.order_by(ordering if ordering in valid_orderings else '-updated_at')
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /chat/conversations/<id>/  — Konversation + Nachrichten
    PATCH  /chat/conversations/<id>/  — Titel oder Topic ändern
    DELETE /chat/conversations/<id>/  — Soft-Delete (DSGVO-konform)
    """
    serializer_class = ConversationSerializer
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(
            user=self.request.user, is_active=True
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        logger.info(f"Konversation {instance.id} gelöscht von {request.user.email}")
        return Response(
            {'message': 'Konversation erfolgreich gelöscht.'},
            status=status.HTTP_200_OK
        )

    def partial_update(self, request, *args, **kwargs):
        allowed = {'title', 'topic'}
        data = {k: v for k, v in request.data.items() if k in allowed}
        if not data:
            return Response(
                {'error': 'Nur "title" und "topic" können geändert werden.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class ConversationClearView(APIView):
    """
    POST /chat/conversations/<pk>/clear/
    Löscht alle Nachrichten, behält die Konversation.
    """
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(
                id=pk, user=request.user, is_active=True
            )
        except Conversation.DoesNotExist:
            return Response({'error': 'Nicht gefunden.'}, status=404)

        deleted_count, _ = Message.objects.filter(conversation=conversation).delete()
        conversation.message_count = 0
        conversation.summary = ''
        conversation.save(update_fields=['message_count', 'summary'])

        return Response({
            'message': f'{deleted_count} Nachrichten gelöscht.',
            'conversation_id': str(conversation.id),
        })


class MessageHistoryView(generics.ListAPIView):
    """
    GET /chat/conversations/<conversation_id>/messages/

    Query-Params:
        ?role=user | assistant | system
    """
    serializer_class = MessageSerializer
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        qs = Message.objects.filter(
            conversation_id=conversation_id,
            conversation__user=self.request.user,
            conversation__is_active=True
        ).order_by('created_at')

        role = self.request.query_params.get('role')
        if role in ('user', 'assistant', 'system'):
            qs = qs.filter(role=role)
        return qs

    def list(self, request, *args, **kwargs):
        if not Conversation.objects.filter(
            id=self.kwargs['conversation_id'], user=request.user
        ).exists():
            return Response({'error': 'Konversation nicht gefunden.'}, status=404)
        return super().list(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────
# BUSINESS DOKUMENT VIEWS
# ─────────────────────────────────────────────────────────────

class BusinessDocumentView(APIView):
    """
    POST /chat/generate-document/
    Generiert strukturierte Business-Dokumente (Pro/Business Plan).

    Request Body:
        doc_type        : str  — Dokumenttyp
        context         : dict — Kontext (Branche, Rechtsform, etc.)
        conversation_id : UUID — Verknüpfung (optional)

    Verfügbare doc_types:
        founding_checklist | business_plan | pitch_deck_outline
        executive_summary  | market_analysis | legal_checklist | financial_plan
    """
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [permissions.IsAuthenticated, PlanPermission]

    VALID_TYPES = [
        'founding_checklist', 'business_plan', 'pitch_deck_outline',
        'executive_summary', 'market_analysis', 'financial_plan', 'legal_checklist',
    ]

    def post(self, request):
        doc_type = request.data.get('doc_type', 'business_plan')
        context = request.data.get('context', {})
        if isinstance(context, str):
            try:
                context = json.loads(context)
            except json.JSONDecodeError:
                context = {}
        conversation_id = request.data.get('conversation_id')

        if doc_type not in self.VALID_TYPES:
            return Response({
                'error': 'invalid_doc_type',
                'available': self.VALID_TYPES,
            }, status=status.HTTP_400_BAD_REQUEST)

        title, content = self._generate(doc_type, context)

        conversation = None
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id, user=request.user, is_active=True
                )
            except Conversation.DoesNotExist:
                pass

        doc = BusinessDocument.objects.create(
            user=request.user,
            conversation=conversation,
            doc_type=doc_type,
            title=title,
            content=content,
        )

        logger.info(f"Dokument generiert: {doc_type} für {request.user.email}")

        return Response({
            'document_id': str(doc.id),
            'title': doc.title,
            'doc_type': doc.doc_type,
            'content': doc.content,
            'created_at': doc.created_at,
        }, status=status.HTTP_201_CREATED)

    def _generate(self, doc_type: str, ctx: dict):
        """Delegiert an den passenden Generator."""
        logic = get_business_logic()

        if doc_type == 'founding_checklist':
            rf = ctx.get('rechtsform', 'GmbH')
            return f"Gründungs-Checkliste: {rf}", logic.generate_founding_checklist(rf)

        if doc_type == 'business_plan':
            industry = ctx.get('industry', '')
            company = ctx.get('company_name', '')
            title = f"Businessplan{' – ' + industry if industry else ''}"
            return title, logic.analyze_business_plan_request(industry, company)

        if doc_type == 'pitch_deck_outline':
            company = ctx.get('company_name', 'Dein Startup')
            return f"Pitch Deck – {company}", self._pitch_deck(ctx)

        if doc_type == 'executive_summary':
            company = ctx.get('company_name', 'Unternehmen')
            return f"Executive Summary – {company}", self._executive_summary(ctx)

        if doc_type == 'market_analysis':
            industry = ctx.get('industry', 'Branche')
            return f"Marktanalyse – {industry}", self._market_analysis(ctx)

        if doc_type == 'legal_checklist':
            rf = ctx.get('rechtsform', 'GmbH')
            return f"Rechtliche Checkliste – {rf}", self._legal_checklist(ctx)

        if doc_type == 'financial_plan':
            company = ctx.get('company_name', 'Unternehmen')
            return f"Finanzplan – {company}", self._financial_plan(ctx)

        return doc_type.replace('_', ' ').title(), '# Dokument\n\nInhalt folgt.'

    def _pitch_deck(self, ctx: dict) -> str:
        company = ctx.get('company_name', '[Unternehmensname]')
        return f"""# Pitch Deck Gliederung – {company}

## Folie 1: Titel
- **{company}** — [Tagline in einem Satz]
- Gründerteam · Datum · Kontakt

## Folie 2: Problem
- Welchen konkreten Schmerz löst ihr?
- Warum sind bestehende Lösungen unzureichend?

## Folie 3: Lösung & USP
- Euer Produkt/Service in 3 Sätzen
- Screenshot oder Mockup
- Alleinstellungsmerkmal

## Folie 4: Marktgröße (TAM → SAM → SOM)
- TAM: [X Mrd. €] · SAM: [X Mio. €] · SOM: [X Mio. €]

## Folie 5: Geschäftsmodell
- Wie verdient ihr Geld? (Abo / einmalig / Freemium)
- Unit Economics: CLV, CAC, Marge

## Folie 6: Traktion & Milestones
- Aktuelle Kennzahlen · Referenzkunden · Wachstum

## Folie 7: Team
- Gründer mit relevantem Background
- Warum genau IHR? · Advisors

## Folie 8: Wettbewerb
- Wettbewerbsmatrix · Positionierung · Unfairer Vorteil (Moat)

## Folie 9: Go-to-Market
- Kundengewinnungskanäle · Wachstumsstrategie · 12-Monats-Plan

## Folie 10: Finanzplanung (3 Jahre)
| Jahr | Umsatz | Kunden | Team |
|------|--------|--------|------|
| J+1  | [X €]  | [X]    | [X]  |
| J+2  | [X €]  | [X]    | [X]  |
| J+3  | [X €]  | [X]    | [X]  |

## Folie 11: Funding Ask
- **Gesuchtes Kapital:** [X EUR] für [Laufzeit]
- Verwendung: [X% Produkt / X% Marketing / X% Team]

## Folie 12: Vision & CTA
- Wo steht {company} in 5 Jahren?
- Kontakt: [E-Mail]

---
💡 Max. 12-15 Folien · 1 Kernaussage pro Folie · Visuals > Text
"""

    def _executive_summary(self, ctx: dict) -> str:
        company = ctx.get('company_name', '[Unternehmensname]')
        return f"""# Executive Summary – {company}

## Das Unternehmen
**{company}** bietet [Produkt/Service] für [Zielgruppe].
Gegründet: [Jahr] · Rechtsform: [GmbH/UG] · Sitz: [Stadt]

## Problem & Lösung
**Problem:** [2-3 Sätze — welcher Schmerz, wie groß?]
**Lösung:** [Was macht ihr? USP in 2 Sätzen.]

## Markt
- Zielgruppe: [Beschreibung]
- Marktgröße (TAM): [X Mrd. €/Jahr]
- Wachstum: [X% p.a.]

## Geschäftsmodell
[Wie verdient ihr Geld? Preisstrategie in 2 Sätzen.]

## Team
| Name | Rolle | Erfahrung |
|------|-------|-----------|
| [Name] | CEO | [Background] |
| [Name] | CTO | [Background] |

## Finanzprognose
| Jahr | Umsatz | EBIT |
|------|--------|------|
| J+1  | [X €]  | [X €] |
| J+2  | [X €]  | [X €] |
| J+3  | [X €]  | [X €] |

## Finanzierungsbedarf
**Gesuchtes Kapital:** [X EUR] — Verwendung: [Kurzbeschreibung]

*Vertraulich — für [Empfänger] · Stand {timezone.now().year}*
"""

    def _market_analysis(self, ctx: dict) -> str:
        industry = ctx.get('industry', '[Branche]')
        return f"""# Marktanalyse – {industry}

## 1. Marktübersicht
**Branche:** {industry} · **Fokus:** [Deutschland / DACH / Europa]

## 2. Marktgröße
| Segment | Größe | Wachstum p.a. |
|---------|-------|----------------|
| TAM (Gesamtmarkt) | [X Mrd. €] | [X%] |
| SAM (Erreichbarer Markt) | [X Mio. €] | [X%] |
| SOM (Realistischer Anteil) | [X Mio. €] | [X%] |

## 3. Zielgruppe
- Primäre Zielgruppe: [Beschreibung]
- Entscheider: [Wer kauft?] · Hauptprobleme: [P1, P2]

## 4. Wettbewerbsanalyse
| Wettbewerber | Stärken | Schwächen | Anteil |
|--------------|---------|-----------|--------|
| [Konkurrent 1] | [S] | [W] | [X%] |
| [Konkurrent 2] | [S] | [W] | [X%] |

## 5. SWOT-Analyse
**Stärken:** [S1, S2] · **Schwächen:** [W1, W2]
**Chancen:** [C1, C2] · **Risiken:** [R1, R2]

## 6. Markttrends
1. [Trend 1 — z.B. Digitalisierung]
2. [Trend 2 — z.B. Nachhaltigkeit]
3. [Trend 3]

## 7. Unsere Positionierung
[Wie differenzieren wir uns klar vom Wettbewerb?]

*Quellen: [Statista / Branchenverband] · Stand {timezone.now().year}*
"""

    def _legal_checklist(self, ctx: dict) -> str:
        rf = ctx.get('rechtsform', 'GmbH')
        return f"""# Rechtliche Checkliste – {rf} Gründung

## ✅ Vor der Gründung
- [ ] Geschäftsidee rechtlich prüfen (Patente, Marken, Lizenzen)
- [ ] Firmennamen recherchieren (Handelsregister + Markenamt)
- [ ] Gesellschaftsvertrag entwerfen lassen
- [ ] Steuerberater + Rechtsanwalt beauftragen

## ✅ Gründungsprozess
- [ ] Notartermin (für {rf} Pflicht)
- [ ] Stammkapital einzahlen + Nachweis erbringen
- [ ] Handelsregistereintragung beantragen
- [ ] Gewerbeanmeldung beim Gewerbeamt (20–65 €)
- [ ] Fragebogen zur steuerlichen Erfassung (Finanzamt)

## ✅ Nach der Gründung
- [ ] Geschäftskonto eröffnen (getrennt von Privat!)
- [ ] USt-IdNr. beantragen (falls nötig)
- [ ] IHK/HWK-Mitgliedschaft prüfen
- [ ] Betriebshaftpflicht + Krankenversicherung klären

## ✅ Website & Online-Recht
- [ ] Impressum (§ 5 TMG — Pflicht!)
- [ ] Datenschutzerklärung (DSGVO — Pflicht!)
- [ ] AGB (bei E-Commerce empfohlen)
- [ ] Cookie-Einwilligung + Widerrufsbelehrung

## ✅ Laufende Pflichten
- [ ] Buchhaltung einrichten (EÜR oder doppelte Buchführung)
- [ ] USt-Voranmeldung einrichten (monatlich/quartalsweise)
- [ ] Jahresabschluss fristgerecht erstellen
- [ ] Aufbewahrungsfristen einhalten (10 Jahre für Belege)

⚖️ *Diese Checkliste ersetzt keine Rechtsberatung.*
*Erstellt mit JDS Business AI · Stand {timezone.now().year}*
"""

    def _financial_plan(self, ctx: dict) -> str:
        company = ctx.get('company_name', '[Unternehmen]')
        return f"""# Finanzplan – {company}

## 1. Startkapital & Finanzierungsquellen
| Quelle | Betrag | Anteil |
|--------|--------|--------|
| Eigenkapital | [X €] | [X%] |
| KfW Gründerkredit | [X €] | [X%] |
| Sonstige | [X €] | [X%] |
| **Gesamt** | **[X €]** | **100%** |

## 2. Einmalige Gründungskosten
| Position | Kosten |
|----------|--------|
| Notar & Handelsregister | [X €] |
| Stammkapital (Einlage) | [X €] |
| Website & Software | [X €] |
| Marketing (Launch) | [X €] |
| Rechts- & Steuerberatung | [X €] |
| **Gesamt** | **[X €]** |

## 3. Monatliche Fixkosten
| Position | Betrag/Monat |
|----------|-------------|
| Miete/Büro | [X €] |
| Personal (Gehälter + Abgaben) | [X €] |
| Software/SaaS-Tools | [X €] |
| Buchhaltung/Steuerberater | [X €] |
| Versicherungen | [X €] |
| Marketing (laufend) | [X €] |
| **Gesamt** | **[X €]** |

## 4. Umsatzprognose (3 Jahre)
| Zeitraum | Umsatz | Kosten | Ergebnis |
|----------|--------|--------|----------|
| Quartal 1 | [X €] | [X €] | [X €] |
| Quartal 2 | [X €] | [X €] | [X €] |
| Jahr 1 gesamt | [X €] | [X €] | [X €] |
| Jahr 2 | [X €] | [X €] | [X €] |
| Jahr 3 | [X €] | [X €] | [X €] |

## 5. Break-Even-Analyse
- Fixkosten/Monat: [X €]
- Deckungsbeitrag pro Einheit/Kunde: [X €]
- **Break-Even-Menge:** [X Einheiten/Monat]
- **Break-Even voraussichtlich erreicht:** Monat [X]

## 6. Liquiditätsreserve
Empfehlung: Immer mind. **3 Monats-Fixkosten** als Puffer halten.
Puffer = [X €] · Zielkonto: [Geschäftskonto]

💡 *Tools: DATEV, Lexware, Fastbill, Kontist für laufende Buchführung.*
"""


# ─────────────────────────────────────────────────────────────
# DOKUMENT-LISTE & DETAIL
# ─────────────────────────────────────────────────────────────

class UserDocumentsView(generics.ListAPIView):
    """
    GET /chat/documents/

    Alle gespeicherten Business-Dokumente des Nutzers.
    Query-Params:
        ?doc_type=business_plan
        ?ordering=-updated_at
    """
    serializer_class = BusinessDocumentSerializer
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = BusinessDocument.objects.filter(user=self.request.user)
        doc_type = self.request.query_params.get('doc_type')
        if doc_type:
            qs = qs.filter(doc_type=doc_type)
        ordering = self.request.query_params.get('ordering', '-updated_at')
        valid = ['-updated_at', 'updated_at', '-created_at', 'title', 'doc_type']
        return qs.order_by(ordering if ordering in valid else '-updated_at')


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /chat/documents/<id>/  — Dokument abrufen
    PATCH  /chat/documents/<id>/  — Bearbeiten (erhöht Versionsnummer)
    DELETE /chat/documents/<id>/  — Dauerhaft löschen
    """
    serializer_class = BusinessDocumentSerializer
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BusinessDocument.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        if 'content' in serializer.validated_data:
            BusinessDocument.objects.filter(pk=instance.pk).update(
                version=instance.version + 1
            )


# ─────────────────────────────────────────────────────────────
# CHAT-VORSCHLÄGE
# ─────────────────────────────────────────────────────────────

class ChatSuggestionsView(APIView):
    """
    GET /chat/suggestions/
    Kontextbasierte Vorschläge für den nächsten Chat.
    """
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [permissions.IsAuthenticated]

    DEFAULT_SUGGESTIONS = [
        {"text": "Wie gründe ich eine GmbH?", "category": "founding", "icon": "🏢"},
        {"text": "Erstelle mir eine Businessplan-Gliederung", "category": "business_plan", "icon": "📋"},
        {"text": "Was muss in mein Impressum?", "category": "legal", "icon": "⚖️"},
        {"text": "Welche Förderungen gibt es für Startups?", "category": "finance", "icon": "💰"},
        {"text": "Wie erstelle ich einen Arbeitsvertrag?", "category": "hr", "icon": "👥"},
        {"text": "Was ist eine SWOT-Analyse?", "category": "strategy", "icon": "🎯"},
    ]

    CATEGORY_FOLLOWUPS = {
        'founding': [
            {"text": "Was kostet eine GmbH-Gründung?", "icon": "💶"},
            {"text": "GmbH vs. UG — was ist besser?", "icon": "🤔"},
            {"text": "Wie lange dauert die GmbH-Gründung?", "icon": "⏱️"},
        ],
        'business_plan': [
            {"text": "Hilf mir mit der Finanzplanung", "icon": "📊"},
            {"text": "Wie schreibe ich eine Marktanalyse?", "icon": "🔍"},
            {"text": "Was gehört in eine Executive Summary?", "icon": "✍️"},
        ],
        'legal': [
            {"text": "Brauche ich AGB für meinen Online-Shop?", "icon": "🛒"},
            {"text": "Was bedeutet DSGVO für mein Business?", "icon": "🛡️"},
            {"text": "Ich habe eine Abmahnung — was tun?", "icon": "⚠️"},
        ],
        'finance': [
            {"text": "Was ist der KfW Gründerkredit?", "icon": "🏦"},
            {"text": "Wie berechne ich den Break-Even?", "icon": "📈"},
            {"text": "Welche Steuern zahlt eine GmbH?", "icon": "🧾"},
        ],
        'hr': [
            {"text": "Was muss in einen Arbeitsvertrag?", "icon": "📄"},
            {"text": "Wie funktioniert eine Kündigung?", "icon": "📋"},
            {"text": "Was kostet mich ein Mitarbeiter wirklich?", "icon": "💶"},
        ],
    }

    def get(self, request):
        suggestions = list(self.DEFAULT_SUGGESTIONS)
        try:
            last_conv = Conversation.objects.filter(
                user=request.user, is_active=True
            ).order_by('-updated_at').first()

            if last_conv and last_conv.topic != 'general':
                followups = self.CATEGORY_FOLLOWUPS.get(last_conv.topic, [])
                if followups:
                    suggestions = [
                        {**f, "category": last_conv.topic} for f in followups
                    ] + suggestions[:3]
        except Exception as e:
            logger.warning(f"Suggestions-Fehler: {e}")

        return Response({'suggestions': suggestions[:6]})