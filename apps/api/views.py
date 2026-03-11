"""
JDS Business AI - Public Developer API Views
REST API für externe Entwickler
"""
import logging
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from .authentication import APIKey
from .serializers import APIKeySerializer, APIKeyCreateSerializer
from apps.ai_engine.views import ChatView as InternalChatView
from apps.ai_engine.permissions import PlanPermission

logger = logging.getLogger('apps.api')


# ============================================================
# API-KEY VERWALTUNG
# ============================================================

class APIKeyListView(generics.ListAPIView):
    """
    GET /api/v1/keys/
    Alle API-Keys des Nutzers auflisten
    """
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated, PlanPermission]

    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user, is_active=True)


class APIKeyCreateView(APIView):
    """
    POST /api/v1/keys/create/
    Neuen API-Key erstellen

    Wichtig: Der Key wird NUR einmal angezeigt! Sicher aufbewahren.
    """
    permission_classes = [permissions.IsAuthenticated, PlanPermission]

    @extend_schema(
        request=APIKeyCreateSerializer,
        responses={201: {'description': 'API-Key erstellt'}},
        examples=[
            OpenApiExample(
                'Neuer API-Key',
                value={'name': 'Mein Backend Server'},
                request_only=True,
            )
        ]
    )
    def post(self, request):
        serializer = APIKeyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        # Limit: Max 10 API-Keys pro Nutzer
        existing_keys = APIKey.objects.filter(user=request.user, is_active=True).count()
        if existing_keys >= 10:
            return Response({'error': 'Maximal 10 API-Keys erlaubt.'}, status=400)

        try:
            api_key_obj, plain_key = APIKey.generate_key(
                user=request.user,
                name=serializer.validated_data['name'],
            )
        except PermissionError as e:
            return Response({'error': str(e)}, status=403)

        return Response({
            'id': str(api_key_obj.id),
            'name': api_key_obj.name,
            'key': plain_key,  # NUR einmal anzeigen!
            'key_prefix': f"jds_{api_key_obj.key_prefix}...",
            'created_at': api_key_obj.created_at,
            'warning': '⚠️ Speichere diesen Key sicher. Er wird nie wieder angezeigt!',
            'rate_limit': f"{api_key_obj.get_daily_limit()} Anfragen/Tag",
        }, status=201)


class APIKeyDeleteView(APIView):
    """
    DELETE /api/v1/keys/<id>/
    API-Key deaktivieren
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            api_key = APIKey.objects.get(id=pk, user=request.user)
            api_key.is_active = False
            api_key.save()
            return Response({'message': 'API-Key deaktiviert.'})
        except APIKey.DoesNotExist:
            return Response({'error': 'API-Key nicht gefunden.'}, status=404)


# ============================================================
# PUBLIC API ENDPUNKTE
# ============================================================

class APIStatusView(APIView):
    """
    GET /api/v1/status/
    API-Status und eigene Limits abrufen (öffentlich)
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        response = {
            'status': 'operational',
            'version': '1.0.0',
            'name': 'JDS Business AI API',
            'docs': '/api/docs/',
        }

        if request.user.is_authenticated:
            subscription = request.user.get_subscription()
            response.update({
                'authenticated': True,
                'plan': subscription.plan,
                'remaining_messages': subscription.get_remaining_messages(),
                'api_access': subscription.has_api_access(),
            })

            # API-Key Infos
            api_key = getattr(request, 'auth', None)
            if hasattr(api_key, 'requests_today'):
                response['api_key_usage'] = {
                    'requests_today': api_key.requests_today,
                    'daily_limit': api_key.get_daily_limit(),
                }

        return Response(response)


class APIChatView(APIView):
    """
    POST /api/v1/chat/
    KI-Chat über API (erfordert Pro/Business Plan + API-Key)

    Erlaubt externen Apps, die JDS Business AI zu nutzen.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': 'Deine Frage an JDS AI'},
                    'conversation_id': {'type': 'string', 'description': 'UUID einer bestehenden Konversation (optional)'},
                    'language': {'type': 'string', 'default': 'de', 'description': 'Sprache der Antwort'},
                },
                'required': ['message'],
            }
        },
        responses={
            200: {
                'description': 'KI-Antwort',
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                'response': {'type': 'string'},
                                'conversation_id': {'type': 'string'},
                                'category': {'type': 'string'},
                                'confidence': {'type': 'number'},
                            }
                        }
                    }
                }
            }
        },
        tags=['Chat'],
        summary='KI-Chat Nachricht senden',
        description='Sendet eine Nachricht an JDS Business AI und erhält eine Antwort.'
    )
    def post(self, request):
        # Nutze den internen Chat-Handler
        internal_view = InternalChatView()
        internal_view.request = request
        internal_view.kwargs = {}
        internal_view.format_kwarg = None
        return internal_view.post(request)


class APIBusinessInfoView(APIView):
    """
    GET /api/v1/business/rechtsformen/
    Strukturierte Geschäftsinformationen über API abrufen
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, topic=None):
        from apps.ai_engine.business_logic import KNOWLEDGE_BASE, BusinessLogic
        logic = BusinessLogic()

        if topic == 'rechtsformen':
            return Response({
                'rechtsformen': KNOWLEDGE_BASE['rechtsformen'],
                'tipp': 'Nutze /api/v1/chat/ für personalisierte Beratung'
            })
        elif topic == 'gruendungsschritte':
            return Response({
                'schritte': KNOWLEDGE_BASE['gruendungsschritte_allgemein'],
            })
        elif topic == 'businessplan':
            return Response({
                'struktur': KNOWLEDGE_BASE['businessplan_struktur'],
            })
        elif topic == 'finanzierung':
            return Response({
                'optionen': KNOWLEDGE_BASE['finanzierung'],
            })
        else:
            return Response({
                'verfuegbare_topics': [
                    'rechtsformen', 'gruendungsschritte', 'businessplan', 'finanzierung'
                ],
                'beispiel': '/api/v1/business/rechtsformen/'
            })
