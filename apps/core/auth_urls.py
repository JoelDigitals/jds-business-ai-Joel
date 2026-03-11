"""JDS Auth URLs - JWT + Registration + Profile + GDPR"""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from .views import RegisterView, UserProfileView, GDPRDataExportView, GDPRDeleteAccountView, SubscriptionView
from . import views as core_views

urlpatterns = [
    # JWT Session-Token (für eingeloggte Session-User)
    path('session-token/', core_views.session_token_view, name='session_token'),

    # JWT
    path('login/',   TokenObtainPairView.as_view(),  name='token_obtain'),
    path('refresh/', TokenRefreshView.as_view(),     name='token_refresh'),
    path('logout/',  TokenBlacklistView.as_view(),   name='token_blacklist'),

    # AJAX Auth (für Modals in base.html — CSRF-exempt)
    path('ajax-login/',    core_views.ajax_login,    name='ajax_login'),
    path('ajax-register/', core_views.ajax_register, name='ajax_register'),

    # Account
    path('register/',     RegisterView.as_view(),         name='register'),
    path('profile/',      UserProfileView.as_view(),       name='profile'),
    path('subscription/', SubscriptionView.as_view(),      name='subscription'),

    # DSGVO
    path('gdpr/export/', GDPRDataExportView.as_view(), name='gdpr_export'),
    path('gdpr/delete/', GDPRDeleteAccountView.as_view(), name='gdpr_delete'),
]
