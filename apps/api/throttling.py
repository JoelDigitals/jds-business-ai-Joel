"""JDS Business AI - API Throttling / Rate Limiting"""
from rest_framework.throttling import BaseThrottle
from django.core.cache import cache
import time


class PlanBasedThrottle(BaseThrottle):
    """
    Plan-basiertes Rate-Limiting:
    - Free: 10/Tag
    - Pro: 200/Tag
    - Business: 10000/Tag
    """

    def allow_request(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True  # Für anonyme Anfragen (andere Auth übernimmt)

        subscription = request.user.get_subscription()
        subscription.reset_daily_limits_if_needed()
        limits = subscription.get_limits()

        self.plan = subscription.plan
        self.limit = limits['messages_per_day']
        self.current = subscription.messages_today

        return self.current < self.limit

    def wait(self):
        """Warte bis Mitternacht (tägliche Limits)"""
        import datetime
        now = datetime.datetime.now()
        midnight = (now + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return (midnight - now).seconds


class APIKeyThrottle(BaseThrottle):
    """Throttling speziell für API-Key Anfragen"""

    def allow_request(self, request, view):
        # auth = request.auth ist der APIKey wenn API-Key Auth
        api_key = getattr(request, 'auth', None)
        if hasattr(api_key, 'is_within_rate_limit'):
            return api_key.is_within_rate_limit()
        return True

    def wait(self):
        return 3600  # 1 Stunde
