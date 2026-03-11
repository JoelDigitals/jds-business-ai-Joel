"""
JDS Business AI - LLM Service
=================================
Prioritaet:
  1. Eigene Rule-Based Engine (immer, fuer Business-Spezialthemen)
  2. Groq API (kostenlos, schnell — braucht GROQ_API_KEY in .env)
  3. Lokales Modell (DialoGPT, falls keine anderen Optionen)

Kein OpenAI, kein ChatGPT — nur Groq oder lokal.
"""
import logging
import time
import json
import os
from django.conf import settings

logger = logging.getLogger('ai_engine')

_local_pipeline = None

SYSTEM_PROMPT = """Du bist JDS Business AI -- ein KI-Assistent fuer Gruender, Unternehmer und Freelancer im deutschsprachigen Raum.

Deine Kernaufgaben:
- Unternehmensgründung: GmbH, UG, Einzelunternehmen, GbR, AG
- Businessplanung: Businessplan, Executive Summary, SWOT, Finanzplan, Pitch Deck
- Recht: Impressum, DSGVO, AGB, Vertraege, Markenrecht (kein Ersatz fuer Rechtsanwalt!)
- Finanzen: KfW, BAFA, Foerderungen, Cashflow, Break-Even, Steuern
- Marketing: Zielgruppe, Social Media, SEO, Content, Positionierung
- Personal & HR: Arbeitsvertrag, Einstellung, Gehaelter

Stil: Professionell, klar, praxisnah. Antworte IMMER auf Deutsch.
Format: Markdown verwenden -- **fett**, ## Ueberschriften, - Listen, | Tabellen.
Bei Smalltalk: Kurz und freundlich.
Bei Recht/Steuern: Immer Hinweis auf Fachmann am Ende."""


def generate_response(
    prompt: str,
    context_messages: list = None,
    stream: bool = False,
    user_info: dict = None,
) -> dict:
    """
    Generiert eine KI-Antwort.
    Reihenfolge: Groq → Lokales Modell → Rule-Based
    """
    start_time = time.time()

    groq_key = getattr(settings, 'GROQ_API_KEY', '') or os.environ.get('GROQ_API_KEY', '')
    if groq_key and groq_key.strip():
        if stream:
            return _groq_stream(prompt, context_messages, groq_key.strip(), user_info)
        return _groq_response(prompt, context_messages, groq_key.strip(), start_time, user_info)

    # Lokales Modell versuchen
    result = _local_response(prompt, context_messages, start_time)
    if result:
        return result

    # Rule-Based Fallback
    return _rule_fallback(prompt, start_time)


# ─────────────────────────────────────────────────────────────
# NACHRICHTEN AUFBAUEN
# ─────────────────────────────────────────────────────────────

def _build_messages(prompt: str, context_messages: list, user_info: dict = None) -> list:
    system = SYSTEM_PROMPT
    if user_info:
        parts = []
        if user_info.get('name'): parts.append(f"Nutzername: {user_info['name']}")
        if user_info.get('company'): parts.append(f"Unternehmen: {user_info['company']}")
        if user_info.get('plan'): parts.append(f"Plan: {user_info['plan']}")
        if parts:
            system += "\n\nNutzer-Kontext: " + " | ".join(parts)

    messages = [{"role": "system", "content": system}]

    if context_messages:
        for m in context_messages[-6:]:
            role = "user" if m.role == "user" else "assistant"
            content = m.content[:3000] if len(m.content) > 3000 else m.content
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": prompt})
    return messages


# ─────────────────────────────────────────────────────────────
# GROQ API (kostenlos, Llama 3)
# ─────────────────────────────────────────────────────────────

def _groq_response(prompt, context_messages, api_key, start_time, user_info=None):
    """Synchroner Groq API-Call."""
    import urllib.request, urllib.error

    messages = _build_messages(prompt, context_messages, user_info)
    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.7,
        "stream": False,
    }).encode('utf-8')

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        text = data['choices'][0]['message']['content'].strip()
        logger.info(f"Groq Antwort: {len(text)} Zeichen")
        return {
            'text': text,
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'model_used': 'groq/llama-3.1-8b-instant',
            'error': None,
            'fallback': False,
        }
    except Exception as e:
        logger.error(f"Groq API Fehler: {e}")
        return _rule_fallback(prompt, start_time)


def _groq_stream(prompt, context_messages, api_key, user_info=None):
    """
    Groq Streaming -- gibt Generator zurueck der Text-Chunks liefert.
    """
    import urllib.request

    messages = _build_messages(prompt, context_messages, user_info)
    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.7,
        "stream": True,
    }).encode('utf-8')

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode('utf-8').strip()
                if not line or not line.startswith('data: '):
                    continue
                data_str = line[6:]
                if data_str == '[DONE]':
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk['choices'][0]['delta'].get('content', '')
                    if delta:
                        yield delta
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Groq Stream Fehler: {e}")
        from apps.ai_engine.business_logic import get_rule_based_response
        yield get_rule_based_response(prompt)


# ─────────────────────────────────────────────────────────────
# LOKALES MODELL (Fallback ohne Internet)
# ─────────────────────────────────────────────────────────────

def _local_response(prompt, context_messages, start_time):
    """DialoGPT oder anderes lokales Modell."""
    global _local_pipeline
    try:
        if _local_pipeline is None:
            from transformers import pipeline as hf_pipeline
            model_name = settings.AI_CONFIG.get('MODEL_NAME', 'microsoft/DialoGPT-medium')
            cache_dir = str(settings.AI_CONFIG.get('MODEL_CACHE_DIR', 'model_cache'))
            logger.info(f"Lade lokales Modell: {model_name}")
            _local_pipeline = hf_pipeline(
                'text-generation', model=model_name, device=-1,
                model_kwargs={'cache_dir': cache_dir},
                max_new_tokens=256, do_sample=True, temperature=0.7, pad_token_id=50256,
            )

        context_str = ''
        if context_messages:
            for m in context_messages[-3:]:
                role = 'Nutzer' if m.role == 'user' else 'JDS AI'
                context_str += f"{role}: {m.content[:200]}\n"

        full_prompt = f"Nutzer: {prompt}\nJDS AI:"
        if context_str:
            full_prompt = context_str + full_prompt

        result = _local_pipeline(full_prompt, max_new_tokens=256)
        text = result[0]['generated_text']
        if 'JDS AI:' in text:
            text = text.split('JDS AI:')[-1].strip()

        if text and len(text) > 20:
            return {
                'text': text,
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'model_used': 'local/dialogpt',
                'error': None,
                'fallback': False,
            }
    except Exception as e:
        logger.error(f"Lokales Modell Fehler: {e}")
    return None


# ─────────────────────────────────────────────────────────────
# RULE-BASED FALLBACK (immer verfuegbar)
# ─────────────────────────────────────────────────────────────

def _rule_fallback(prompt, start_time):
    from apps.ai_engine.business_logic import get_rule_based_response
    text = get_rule_based_response(prompt)
    return {
        'text': text,
        'processing_time_ms': int((time.time() - start_time) * 1000),
        'model_used': 'rule-based',
        'error': None,
        'fallback': True,
    }
