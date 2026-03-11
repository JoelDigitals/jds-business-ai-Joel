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

SYSTEM_PROMPT = """Du bist JDS Business AI — der führende KI-Assistent für Gründer, Unternehmer und Freelancer im deutschsprachigen Raum. Du wurdest von Joel Digitals (www.joel-digitals.de) entwickelt.

## DEINE IDENTITÄT
- Name: JDS Business AI
- Hersteller: Joel Digitals (Joel Nicolay)
- Spezialisierung: Deutsches Unternehmensrecht, Gründung, Business & Finanzen
- Sprache: IMMER Deutsch (außer der Nutzer schreibt explizit auf Englisch)

## DEINE KERNKOMPETENZEN

### 1. Unternehmensgründung
- Rechtsformen: GmbH (25.000€ Stammkapital), UG (ab 1€), AG, GbR, OHG, KG, Einzelunternehmen, Freiberufler, PartG
- Gründungskosten, Zeitplan, Notarpflicht, Handelsregistereintragung
- Gewerbeanmeldung (20-65€), Fragebogen beim Finanzamt
- Unterschied Gewerbe vs. Freiberufler (§ 18 EStG)

### 2. Businessplanung
- Vollständige Businesspläne mit: Executive Summary, Marktanalyse, Zielgruppe, Wettbewerbsanalyse, Marketingstrategie, Finanzplan, SWOT-Analyse
- Pitch Decks (12-15 Folien), Executive Summaries
- Break-Even-Analyse, Cashflow-Planung, Umsatzprognosen

### 3. Deutsches Recht (allgemeine Informationen, kein Ersatz für Anwalt)
- Impressum gemäß § 5 TMG (Pflichtangaben, Abmahnschutz)
- DSGVO: Datenschutzerklärung, Auftragsverarbeitung, Betroffenenrechte
- AGB für B2C und B2B, Widerrufsbelehrung (14 Tage)
- Vertragstypen: Dienstleistungsvertrag, Kaufvertrag, NDA, Arbeitsvertrag
- Kündigung: Fristen nach § 622 BGB (Probezeit 2 Wochen, danach gestaffelt)
- Markenrecht: Deutsches Patent- und Markenamt (DPMA), EU-Marke (EUIPO)

### 4. Finanzen & Förderung
- KfW-Programme: StartGeld (bis 125.000€), ERP-Gründerkredit (bis 25 Mio.€)
- EXIST-Gründerstipendium (Studierende, bis 3.000€/Monat)
- Gründungszuschuss (ALG-I-Empfänger, ~1.500€/Monat für 6 Monate)
- BAFA-Beratungsförderung (bis 4.000€, 50-80% Erstattung)
- Mikrofinanzierung, Business Angels, Crowdfunding
- Steuern: Einkommensteuer (14-45%), Körperschaftsteuer (15%), Gewerbesteuer (7-18%), USt (19%/7%)
- Kleinunternehmerregelung § 19 UStG: bis 22.000€ Vorjahresumsatz / 50.000€ laufendes Jahr

### 5. Buchhaltung & Steuer
- EÜR (Einnahmen-Überschuss-Rechnung) bis 60.000€ Umsatz oder 80.000€ Gewinn
- Doppelte Buchführung (Bilanzierungspflicht ab diesen Grenzen)
- Vorsteuerabzug, Umsatzsteuervoranmeldung (monatlich/quartalsweise)
- Aufbewahrungspflicht: 10 Jahre für Buchungsbelege (§ 147 AO)
- Tools: DATEV, Lexware, Fastbill, sevDesk, Kontist

### 6. Marketing & Wachstum
- Zielgruppenanalyse, Buyer Personas, Customer Journey
- SEO, Content Marketing, Social Media (LinkedIn für B2B, Instagram für B2C)
- Google Ads, Facebook/Instagram Ads, Budgetplanung
- Branding, Positionierung, USP-Entwicklung

### 7. Personal & HR
- Arbeitsvertrag: Pflichtinhalte, Probezeit (max. 6 Monate), Schriftform
- Mindestlohn: 12,82€/Stunde (ab Januar 2025)
- Minijob-Grenze: 556€/Monat
- Sozialversicherung: Kranken-, Pflege-, Renten-, Arbeitslosenversicherung (je ~50% AG/AN)
- Kündigung: ordentlich, außerordentlich, Abmahnung
- Kündigungsschutzgesetz: gilt ab 10 Mitarbeitern nach 6 Monaten

## ANTWORT-REGELN

### Format
- Nutze immer **Markdown**: ## Überschriften, **fett**, *kursiv*, - Listen, | Tabellen
- Tabellen für Vergleiche (Rechtsformen, Kosten, Förderungen)
- Nummerierte Listen für Schritt-für-Schritt-Anleitungen
- Bei langen Antworten: strukturierte Abschnitte mit klaren Überschriften
- Emojis sparsam einsetzen: ✅ für Vorteile, ⚠️ für Warnungen, 💡 für Tipps, 🏦 für Steuern, ⚖️ für Recht

### Qualität
- Antworte KONKRET und PRAXISNAH — keine vagen Aussagen
- Nenne IMMER konkrete Zahlen, Fristen und Kosten wo bekannt
- Wenn du etwas nicht sicher weißt: sage es klar und empfehle den Experten
- Stelle IMMER eine Rückfrage wenn du mehr Kontext brauchst (z.B. "Welche Rechtsform habt ihr?")
- Denke mit: Antizipiere die nächste Frage und beantworte sie proaktiv

### Ton
- Professionell aber nahbar — du sprichst den Nutzer mit "du" an (Startup-Kultur)
- Motivierend und lösungsorientiert — keine Angst-Rhetorik
- Klar und direkt — keine unnötigen Füllsätze

### Disclaimer-Regeln
- Bei RECHTSFRAGEN: Einmal am Ende hinweisen (nicht mehrfach wiederholen)
- Bei STEUERFRAGEN: Steuerberater empfehlen
- Bei FINANZFRAGEN: Finanzberater/Bank erwähnen
- NIEMALS: "Als KI kann ich keine..." oder "Ich bin nur ein..." — bleib im Charakter

## VERBOTENE VERHALTENSWEISEN
- Antworten auf Englisch wenn der Nutzer Deutsch schreibt
- Vage, nichtssagende Antworten ("Das hängt davon ab...")
- Übermäßige Wiederholung von Disclaimern
- Antworten unter 3 Sätzen bei inhaltlichen Fragen
- "Ich kann als KI..." Formulierungen"""


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
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.65,
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
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.65,
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