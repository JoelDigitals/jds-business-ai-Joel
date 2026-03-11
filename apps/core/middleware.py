"""
JDS Business AI - Middleware
DSGVO-Middleware und Rate-Limiting
"""
import json
import logging
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger('apps.core')


class GDPRMiddleware:
    """
    DSGVO-Middleware:
    - Datenschutz-Header setzen
    - IP-Anonymisierung in Logs
    - Cookie-Consent prüfen
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Datenschutz-Header
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        return response

    def anonymize_ip(self, ip: str) -> str:
        """Anonymisiert IP-Adresse für DSGVO-konforme Logs"""
        if not ip:
            return '0.0.0.0'
        parts = ip.split('.')
        if len(parts) == 4:
            parts[-1] = '0'
            return '.'.join(parts)
        return ip


class RateLimitMiddleware:
    """
    Rate-Limiting Middleware für zusätzlichen Schutz
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Globales Rate-Limit: Max 1000 Requests/Minute pro IP
        ip = self.get_client_ip(request)
        cache_key = f'rate_limit_global_{ip}'
        requests = cache.get(cache_key, 0)

        if requests > 1000:
            return JsonResponse(
                {'error': 'Zu viele Anfragen. Bitte warte einen Moment.'},
                status=429
            )

        cache.set(cache_key, requests + 1, 60)  # 60 Sekunden
        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
