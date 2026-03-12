"""
JDS Business AI - PDF Download + SSE Streaming View
"""
import json
import time
import logging
from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication

logger = logging.getLogger('ai_engine')

_DEFAULT_AUTH = [JWTAuthentication, SessionAuthentication]


@method_decorator(csrf_exempt, name='dispatch')
class MessagePDFView(APIView):
    """GET /chat/message/<id>/pdf/ — Lädt Chat-Antwort als professionelles PDF."""
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id):
        from .models import Message
        from .pdf_service import generate_pdf
        from rest_framework.response import Response

        try:
            msg = Message.objects.get(
                id=message_id,
                conversation__user=request.user,
                role='assistant'
            )
        except Message.DoesNotExist:
            return Response({'error': 'Nachricht nicht gefunden.'}, status=404)

        user = request.user
        title = msg.conversation.title or 'JDS Business AI Bericht'
        company = getattr(user, 'company_name', '') or ''
        user_name = f"{user.first_name} {user.last_name}".strip() or user.email

        try:
            pdf_bytes = generate_pdf(
                title=title,
                content=msg.content,
                company_name=company,
                user_name=user_name,
            )
            safe_title = ''.join(
                c for c in title if c.isalnum() or c in ' _-'
            )[:40].replace(' ', '_')
            resp = HttpResponse(pdf_bytes, content_type='application/pdf')
            resp['Content-Disposition'] = f'attachment; filename="JDS_{safe_title}.pdf"'
            return resp
        except Exception as e:
            logger.error(f"PDF Fehler: {e}", exc_info=True)
            return Response({'error': f'PDF konnte nicht erstellt werden: {e}'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ChatStreamView(APIView):
    """
    POST /chat/stream/
    SSE Events:
      {"type":"start",    "conversation_id":"...", "category":"..."}
      {"type":"thinking", "steps":[...]}   <- Denkvorgang SEPARAT, nie im Text
      {"type":"chunk",    "text":"..."}    <- Reiner AI-Text-Chunk
      {"type":"done",     "message_id":"...", ...}
      {"type":"error",    "message":"..."}
    """
    authentication_classes = _DEFAULT_AUTH
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_message = (request.data.get('message') or '').strip()
        conv_id = request.data.get('conversation_id') or None

        if not raw_message:
            return HttpResponse(
                'data: {"type":"error","message":"Nachricht fehlt"}\n\n',
                content_type='text/event-stream'
            )

        user = request.user
        sub = user.get_subscription()
        can_send, reason = sub.can_send_message(len(raw_message))

        if not can_send:
            def limit_stream():
                yield f'data: {json.dumps({"type":"error","message":reason,"limit":True})}\n\n'
            return StreamingHttpResponse(limit_stream(), content_type='text/event-stream')

        from .views import _get_or_create_conversation
        from .reasoning_engine import get_reasoning_engine

        conversation, is_new = _get_or_create_conversation(user, conv_id, raw_message)
        if not conversation:
            def err_stream():
                yield 'data: {"type":"error","message":"Konversation nicht gefunden"}\n\n'
            return StreamingHttpResponse(err_stream(), content_type='text/event-stream')

        limits = sub.get_limits()
        context_messages = conversation.get_context_messages(
            limit=limits.get('conversation_history', 5)
        )
        reasoning = get_reasoning_engine().analyze(raw_message, context_messages)

        user_info = {
            'name': f"{user.first_name} {user.last_name}".strip(),
            'company': getattr(user, 'company_name', '') or '',
            'plan': sub.plan,
        }

        import django.conf as dj_conf

        def event_stream():
            full_text = ''
            start = time.time()
            used_groq = False
            model_label = 'rule-based'

            # EVENT 1: Start
            yield f'data: {json.dumps({"type":"start","category":reasoning.category,"conversation_id":str(conversation.id),"is_new":is_new})}\n\n'

            # EVENT 2: Denkvorgang SEPARAT senden (NIE in den Nachrichtentext mischen)
            thinking_steps = []
            for step in reasoning.reasoning_steps:
                action = step.get('action', '')
                result_val = step.get('result', '')
                inp = step.get('input', '')
                thinking_steps.append({
                    'action': action,
                    'result': result_val or (inp[:120] if inp else ''),
                })
            thinking_steps.append({
                'action': 'Kategorie erkannt',
                'result': f"{reasoning.category} ({int(reasoning.confidence * 100)}% Konfidenz)",
            })
            yield f'data: {json.dumps({"type":"thinking","steps":thinking_steps})}\n\n'

            groq_key = getattr(dj_conf.settings, 'GROQ_API_KEY', '') or ''

            # PRIORITÄT 1: Spezial-Handler
            try:
                from .views import _route_to_specialist
                specialist_text = _route_to_specialist(reasoning.category, raw_message)
                if specialist_text and len(specialist_text.strip()) > 50:
                    full_text = specialist_text
                    model_label = f'specialist:{reasoning.category}'
                    for i, word in enumerate(full_text.split(' ')):
                        chunk = word + (' ' if i < len(full_text.split(' ')) - 1 else '')
                        yield f'data: {json.dumps({"type":"chunk","text":chunk})}\n\n'
                        time.sleep(0.02 if word.endswith(('.', '!', '?')) else 0.006)
            except Exception as e:
                logger.error(f"Spezial-Handler Fehler: {e}", exc_info=True)
                full_text = ''

            # PRIORITÄT 2: Groq LLM Streaming
            if not full_text and groq_key and groq_key.strip():
                try:
                    from .llm_service import _groq_stream
                    prompt = reasoning.enhanced_prompt or raw_message
                    for chunk in _groq_stream(prompt, context_messages, groq_key.strip(), user_info):
                        if chunk:
                            full_text += chunk
                            yield f'data: {json.dumps({"type":"chunk","text":chunk})}\n\n'
                    if full_text.strip():
                        used_groq = True
                        model_label = 'groq/llama-3.3-70b-versatile'
                        logger.info(f"Groq OK: {len(full_text)} Zeichen")
                    else:
                        logger.warning("Groq: Kein Text erhalten")
                        full_text = ''
                except Exception as e:
                    logger.error(f"Groq Fehler: {e}")
                    full_text = ''

            # PRIORITÄT 3: Wissensdatenbank-Fallback
            if not full_text or not full_text.strip():
                model_label = 'knowledge-fallback'
                try:
                    from .views import _knowledge_fallback
                    full_text = _knowledge_fallback(reasoning.category, raw_message)
                except Exception:
                    from .business_logic import get_rule_based_response
                    full_text = get_rule_based_response(raw_message)

                words = full_text.split(' ')
                streamed = ''
                for i, word in enumerate(words):
                    chunk = word + (' ' if i < len(words) - 1 else '')
                    streamed += chunk
                    yield f'data: {json.dumps({"type":"chunk","text":chunk})}\n\n'
                    if word.endswith(('.', '!', '?')):
                        time.sleep(0.04)
                    elif word.endswith((',', ';', ':')):
                        time.sleep(0.02)
                    else:
                        time.sleep(0.010)
                full_text = streamed

            # Disclaimer (nur Text, kein Denkvorgang)
            try:
                from .reasoning_engine import get_reasoning_engine as gre
                full_text = gre().add_disclaimers(full_text, reasoning)
            except Exception:
                pass

            processing_time = int((time.time() - start) * 1000)

            # Speichern
            try:
                with transaction.atomic():
                    from .models import Message, Conversation
                    Message.objects.create(
                        conversation=conversation,
                        role='user',
                        content=raw_message,
                    )
                    ai_msg = Message.objects.create(
                        conversation=conversation,
                        role='assistant',
                        content=full_text,
                        reasoning_steps=reasoning.reasoning_steps,
                        business_category=reasoning.category,
                        confidence_score=round(reasoning.confidence, 3),
                        processing_time_ms=processing_time,
                        sources_used=[model_label],
                    )
                    Conversation.objects.filter(pk=conversation.pk).update(
                        message_count=conversation.message_count + 2
                    )
                    sub.increment_usage(message=True)

                from .pdf_service import is_pdf_worthy
                offer_pdf = is_pdf_worthy(full_text)

                done_payload = {
                    "type": "done",
                    "message_id": str(ai_msg.id),
                    "processing_time_ms": processing_time,
                    "category": reasoning.category,
                    "confidence": round(reasoning.confidence, 3),
                    "remaining_messages": sub.get_remaining_messages(),
                    "offer_pdf": offer_pdf,
                    "pdf_url": f"/chat/message/{str(ai_msg.id)}/pdf/" if offer_pdf else None,
                    "model_used": model_label,
                    "is_fallback": not used_groq,
                }
                yield f'data: {json.dumps(done_payload)}\n\n'

            except Exception as e:
                logger.error(f"Stream Speicher-Fehler: {e}", exc_info=True)
                yield f'data: {json.dumps({"type":"error","message":str(e)})}\n\n'

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache, no-store'
        response['X-Accel-Buffering'] = 'no'
        response['X-Content-Type-Options'] = 'nosniff'
        return response