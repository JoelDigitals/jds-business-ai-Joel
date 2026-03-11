"""JDS Business AI - AI Engine Permissions"""
from rest_framework.permissions import BasePermission


class PlanPermission(BasePermission):
    """Prüft ob der Nutzer den richtigen Plan hat"""
    message = "Diese Funktion erfordert einen Pro oder Business Plan."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        subscription = request.user.get_subscription()
        return subscription.plan in ('pro', 'business')


class BusinessPlanPermission(BasePermission):
    """Nur für Business-Plan Nutzer"""
    message = "Diese Funktion ist nur im Business Plan verfügbar."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        subscription = request.user.get_subscription()
        return subscription.plan == 'business'
