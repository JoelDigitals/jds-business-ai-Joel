"""
JDS Business AI - Core Views
Login, Registrierung, Chat, Dashboard, Codes
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Subscription, AccessCode, GDPRLog
from .serializers import RegisterSerializer, UserSerializer, SubscriptionSerializer

logger = logging.getLogger('core')


# ─────────────────────────────────────────────────────────────
# HILFSFUNKTION: JWT für eingeloggten User holen
# ─────────────────────────────────────────────────────────────
def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


# ─────────────────────────────────────────────────────────────
# AUTH: Login & Registrierung (Django Session + JWT)
# ─────────────────────────────────────────────────────────────

def login_view(request):
    """POST: Email + Passwort → Django-Session + JWT zurück"""
    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('/chat/')
        return render(request, 'auth/login.html')

    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=email, password=password)

    if user and user.is_active:
        login(request, user)
        tokens = _get_tokens(user)
        response = redirect(request.POST.get('next', '/chat/'))
        # JWT auch als Cookie setzen (optional, für JS-Zugriff)
        response.set_cookie('jds_access', tokens['access'], httponly=False, samesite='Lax')
        return response

    return render(request, 'auth/login.html', {'error': 'E-Mail oder Passwort falsch.'})


def register_view(request):
    """POST: Neuen Account anlegen"""
    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('/chat/')
        return render(request, 'auth/register.html')

    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    password2 = request.POST.get('password2', '')
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    gdpr = request.POST.get('gdpr_consent') == 'on'

    errors = []
    if not email:
        errors.append('E-Mail ist Pflichtfeld.')
    if User.objects.filter(email=email).exists():
        errors.append('Diese E-Mail ist bereits registriert.')
    if len(password) < 8:
        errors.append('Passwort muss mindestens 8 Zeichen haben.')
    if password != password2:
        errors.append('Passwörter stimmen nicht überein.')
    if not gdpr:
        errors.append('Bitte akzeptiere die Datenschutzerklärung.')

    if errors:
        return render(request, 'auth/register.html', {
            'errors': errors,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
        })

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        gdpr_consent=True,
        gdpr_consent_date=timezone.now(),
    )
    Subscription.objects.create(user=user, plan='free')

    login(request, user)
    logger.info(f"Neuer User registriert: {email}")
    return redirect('/chat/')


def logout_view(request):
    logout(request)
    return redirect('/')


# ─────────────────────────────────────────────────────────────
# JWT SESSION-TOKEN (für JS wenn nur Session vorhanden)
# ─────────────────────────────────────────────────────────────
@login_required
def session_token_view(request):
    tokens = _get_tokens(request.user)
    return JsonResponse(tokens)


# ─────────────────────────────────────────────────────────────
# AJAX AUTH (für base.html Modal — bleibt als Fallback)
# ─────────────────────────────────────────────────────────────
@csrf_exempt
@require_POST
def ajax_login(request):
    import json
    try:
        body = json.loads(request.body)
    except Exception:
        body = {}
    email = body.get('email', '')
    password = body.get('password', '')
    user = authenticate(request, username=email, password=password)
    if user and user.is_active:
        login(request, user)
        tokens = _get_tokens(user)
        return JsonResponse({'success': True, **tokens})
    return JsonResponse({'success': False, 'error': 'Ungültige Anmeldedaten.'}, status=401)


@csrf_exempt
@require_POST
def ajax_register(request):
    import json
    try:
        body = json.loads(request.body)
    except Exception:
        body = {}

    email = body.get('email', '').strip()
    password = body.get('password', '')
    password2 = body.get('password2', '')
    first_name = body.get('first_name', '').strip()
    last_name = body.get('last_name', '').strip()
    gdpr = body.get('gdpr_consent', False)

    if not email:
        return JsonResponse({'error': 'E-Mail fehlt.'}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'E-Mail bereits registriert.'}, status=400)
    if len(password) < 8:
        return JsonResponse({'error': 'Passwort zu kurz (min. 8 Zeichen).'}, status=400)
    if password != password2:
        return JsonResponse({'error': 'Passwörter stimmen nicht überein.'}, status=400)
    if not gdpr:
        return JsonResponse({'error': 'Datenschutzerklärung muss akzeptiert werden.'}, status=400)

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        gdpr_consent=True,
        gdpr_consent_date=timezone.now(),
    )
    Subscription.objects.create(user=user, plan='free')
    login(request, user)
    tokens = _get_tokens(user)
    logger.info(f"Ajax-Register: {email}")
    return JsonResponse({'success': True, **tokens})


# ─────────────────────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────────────────────

def landing_page(request):
    return render(request, 'landing/index.html')


@login_required
def dashboard(request):
    sub = request.user.get_subscription()
    sub.reset_daily_limits_if_needed()
    limits = sub.get_limits()
    return render(request, 'core/dashboard.html', {
        'subscription': sub,
        'limits': limits,
        'remaining_messages': sub.get_remaining_messages(),
    })


@login_required
def chat_view(request):
    sub = request.user.get_subscription()
    sub.reset_daily_limits_if_needed()
    limits = sub.get_limits()
    quick_topics = [
        {'icon': '🏢', 'label': 'GmbH gründen',         'text': 'Wie gründe ich eine GmbH?'},
        {'icon': '📋', 'label': 'Businessplan',          'text': 'Erstelle mir einen Businessplan'},
        {'icon': '⚖️', 'label': 'Impressum & DSGVO',     'text': 'Was muss in mein Impressum?'},
        {'icon': '💰', 'label': 'Finanzierung',          'text': 'Welche Förderungen gibt es für Startups?'},
        {'icon': '👥', 'label': 'Mitarbeiter einstellen','text': 'Wie erstelle ich einen Arbeitsvertrag?'},
        {'icon': '🎯', 'label': 'SWOT-Analyse',          'text': 'Was ist eine SWOT-Analyse?'},
    ]
    return render(request, 'chat/index.html', {
        'subscription': sub,
        'limits': limits,
        'remaining_messages': sub.get_remaining_messages(),
        'quick_topics': quick_topics,
        'user': request.user,
    })


def privacy_policy(request):
    return render(request, 'legal/privacy.html')


def terms_of_service(request):
    return render(request, 'legal/terms.html')


# ─────────────────────────────────────────────────────────────
# CODES EINLÖSEN
# ─────────────────────────────────────────────────────────────

@login_required
def redeem_code_view(request):
    """Seite zum Einlösen von Zugangscodes"""
    success = None
    error = None

    if request.method == 'POST':
        code_str = request.POST.get('code', '').strip().upper()
        try:
            code = AccessCode.objects.get(code=code_str)
            ok, msg = code.redeem(request.user)
            if ok:
                success = msg
                GDPRLog.objects.create(
                    user=request.user,
                    action='code_redeemed',
                    details={'code': code_str, 'plan': code.plan},
                )
            else:
                error = msg
        except AccessCode.DoesNotExist:
            error = 'Ungültiger Code. Bitte prüfe die Eingabe.'

    sub = request.user.get_subscription()
    return render(request, 'core/redeem.html', {
        'subscription': sub,
        'success': success,
        'error': error,
    })


# ─────────────────────────────────────────────────────────────
# ADMIN: CODES GENERIEREN & VERWALTEN
# ─────────────────────────────────────────────────────────────

@staff_member_required
def code_admin_view(request):
    """Admin-Seite: Codes erstellen und auflisten"""
    message = None

    if request.method == 'POST':
        plan = request.POST.get('plan', 'pro')
        period = request.POST.get('period', 'monthly')
        count = min(int(request.POST.get('count', 1)), 100)
        note = request.POST.get('note', '')

        # Ablauf des Codes selbst (optional)
        code_expires_days = request.POST.get('code_expires_days', '')
        expires_at = None
        if code_expires_days:
            try:
                expires_at = timezone.now() + __import__('datetime').timedelta(days=int(code_expires_days))
            except Exception:
                pass

        created = []
        for _ in range(count):
            c = AccessCode.objects.create(
                plan=plan,
                period=period,
                note=note,
                expires_at=expires_at,
                created_by=request.user,
            )
            created.append(c)

        message = f"{count} Code(s) erstellt."

    # Filter
    plan_filter = request.GET.get('plan', '')
    used_filter = request.GET.get('used', '')
    codes = AccessCode.objects.all()
    if plan_filter:
        codes = codes.filter(plan=plan_filter)
    if used_filter == '0':
        codes = codes.filter(is_used=False)
    elif used_filter == '1':
        codes = codes.filter(is_used=True)

    return render(request, 'admin_custom/codes.html', {
        'codes': codes[:200],
        'message': message,
        'plan_filter': plan_filter,
        'used_filter': used_filter,
        'total': AccessCode.objects.count(),
        'unused': AccessCode.objects.filter(is_used=False).count(),
        'used': AccessCode.objects.filter(is_used=True).count(),
    })


# ─────────────────────────────────────────────────────────────
# REST API VIEWS (für base.html Modal)
# ─────────────────────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            errs = '; '.join(
                f"{f}: {', '.join(str(e) for e in es)}"
                for f, es in serializer.errors.items()
            )
            return Response({'error': errs}, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        Subscription.objects.get_or_create(user=user, defaults={'plan': 'free'})
        login(request, user)
        tokens = _get_tokens(user)
        return Response({**tokens, 'success': True}, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class SubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sub = request.user.get_subscription()
        return Response({
            'plan': sub.plan,
            'plan_display': sub.get_plan_display(),
            'expires_at': sub.expires_at,
            'billing_period': sub.billing_period,
            'remaining_messages': sub.get_remaining_messages(),
            'messages_today': sub.messages_today,
        })


class GDPRDataExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        sub = user.get_subscription()
        data = {
            'user': {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'company_name': user.company_name,
                'created_at': str(user.created_at),
                'gdpr_consent': user.gdpr_consent,
            },
            'subscription': {
                'plan': sub.plan,
                'started_at': str(sub.started_at),
                'total_messages': sub.total_messages,
            },
        }
        from django.http import JsonResponse
        return JsonResponse(data)


class GDPRDeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.request_data_deletion()
        return Response({'message': 'Löschanfrage eingereicht. Daten werden innerhalb von 30 Tagen gelöscht.'})
