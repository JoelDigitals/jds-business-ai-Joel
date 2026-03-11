"""JDS Business AI - Developer API URLs"""
from django.urls import path
from . import views

urlpatterns = [
    # Status
    path('status/', views.APIStatusView.as_view(), name='api_status'),

    # API-Key Verwaltung
    path('keys/', views.APIKeyListView.as_view(), name='api_keys_list'),
    path('keys/create/', views.APIKeyCreateView.as_view(), name='api_key_create'),
    path('keys/<uuid:pk>/delete/', views.APIKeyDeleteView.as_view(), name='api_key_delete'),

    # Chat API
    path('chat/', views.APIChatView.as_view(), name='api_chat'),

    # Business Info API
    path('business/', views.APIBusinessInfoView.as_view(), {'topic': None}, name='api_business'),
    path('business/<str:topic>/', views.APIBusinessInfoView.as_view(), name='api_business_topic'),
]
