"""JDS Custom Exception Handler"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
import logging

logger = logging.getLogger('core')


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Originaldaten flach extrahieren
        original = response.data
        
        # detail kann string oder dict sein — immer als string
        if isinstance(original, dict):
            detail = original.get('detail', '')
            if not isinstance(detail, str):
                detail = str(detail)
            # Andere Felder durchreichen
            message = detail or str(original)
        elif isinstance(original, list):
            message = '; '.join(str(e) for e in original)
        else:
            message = str(original)

        response.data = {
            'error': True,
            'status_code': response.status_code,
            'message': message,          # ← immer ein String
            'detail': message,           # ← Kompatibilität mit DRF-Standard
            'original': original,        # ← Originaldaten für Debugging
            'hint': _get_hint(response.status_code),
        }

        logger.debug(f"Exception handler: {response.status_code} — {message}")

    return response


def _get_hint(status_code):
    hints = {
        429: 'Tageslimit erreicht. Upgrade auf Pro für mehr Kapazität.',
        403: 'Diese Funktion ist in deinem Plan nicht verfügbar.',
        401: 'Bitte melde dich erneut an.',
        404: 'Die angefragte Ressource wurde nicht gefunden.',
    }
    return hints.get(status_code)
