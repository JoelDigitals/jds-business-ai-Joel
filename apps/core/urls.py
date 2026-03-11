"""JDS Core URLs"""
from django.urls import path
from . import views
from .views import ImpressumView, DatenschutzView

urlpatterns = [
    # Pages
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('chat/', views.chat_view, name='chat'),
    path("impressum/", ImpressumView.as_view(), name="impressum"),
    path("datenschutz/", DatenschutzView.as_view(), name="datenschutz"),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('nutzungsbedingungen/', views.terms_of_service, name='terms'),

    # Auth (normale Seiten)
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # AJAX Auth (für Modal in base.html)
    path('api/auth/ajax-login/', views.ajax_login, name='ajax_login'),
    path('api/auth/ajax-register/', views.ajax_register, name='ajax_register'),

    # JWT für Session-User
    path('api/auth/session-token/', views.session_token_view, name='session_token'),

    # Codes
    path('code/', views.redeem_code_view, name='redeem_code'),
    path('admin-codes/', views.code_admin_view, name='code_admin'),
]
