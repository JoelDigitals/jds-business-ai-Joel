"""
JDS Business AI - AI Engine URLs
Alle Chat- und Dokument-Endpunkte
"""
from django.urls import path
from . import views

urlpatterns = [
    # Haupt-Chat
    path('message/', views.ChatView.as_view(), name='chat_message'),
    path('suggestions/', views.ChatSuggestionsView.as_view(), name='chat_suggestions'),

    # Konversationen
    path('conversations/', views.ConversationListView.as_view(), name='conversation_list'),
    path('conversations/<uuid:pk>/', views.ConversationDetailView.as_view(), name='conversation_detail'),
    path('conversations/<uuid:pk>/clear/', views.ConversationClearView.as_view(), name='conversation_clear'),
    path('conversations/<uuid:conversation_id>/messages/', views.MessageHistoryView.as_view(), name='message_history'),

    # Dokument-Generierung (Pro / Business)
    path('generate-document/', views.BusinessDocumentView.as_view(), name='generate_document'),
    path('documents/', views.UserDocumentsView.as_view(), name='user_documents'),
    path('documents/<uuid:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
]

# Nachträglich ergänzt:
from .pdf_views import MessagePDFView, ChatStreamView
urlpatterns += [
    path('message/<uuid:message_id>/pdf/', MessagePDFView.as_view(), name='message_pdf'),
    path('stream/', ChatStreamView.as_view(), name='chat_stream'),
]
