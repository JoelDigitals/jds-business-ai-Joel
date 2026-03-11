"""
JDS Business AI - Reasoning Engine
"Selbstdenk-Logik" - Chain of Thought Reasoning für bessere Antworten

Der Reasoning Engine analysiert die Nutzerfrage in mehreren Schritten:
1. Frage verstehen & kategorisieren
2. Relevante Wissensbasen identifizieren
3. Antwort-Strategie planen
4. Antwort generieren & verfeinern
5. Quellen & Warnhinweise hinzufügen
"""
import logging
import re
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger('ai_engine')


@dataclass
class ReasoningResult:
    """Ergebnis des Reasoning-Prozesses"""
    category: str = 'general'
    subcategory: str = ''
    confidence: float = 0.8
    reasoning_steps: list = field(default_factory=list)
    requires_legal_disclaimer: bool = False
    requires_tax_disclaimer: bool = False
    requires_financial_disclaimer: bool = False
    recommended_tools: list = field(default_factory=list)
    context_keywords: list = field(default_factory=list)
    urgency: str = 'normal'  # 'low', 'normal', 'high'
    enhanced_prompt: str = ''


class ReasoningEngine:
    """
    Haupt-Reasoning-Engine für JDS Business AI.
    Analysiert Nutzerfragen und plant optimale Antwortstrategien.
    """

    # Kategorie-Keywords (für schnelle Erkennung)
    CATEGORIES = {
        'founding': {
            'keywords': ['gründen', 'gründung', 'gmbh', 'ug', 'ag', 'einzelunternehmen',
                        'gewerbeanmeldung', 'handelsregister', 'startup', 'unternehmen gründen',
                        'selbstständig', 'freiberufler', 'gewerbe anmelden'],
            'weight': 1.0,
        },
        'business_plan': {
            'keywords': [
                'businessplan', 'business plan', 'bussiness plan', 'bussinesplan',
                'geschäftsplan', 'geschäftsmodell', 'executive summary',
                'mission statement', 'vision', 'pitch deck',
                'investor', 'plan erstellen', 'plan schreiben', 'plan entwickeln',
                'unternehmensplan', 'konzept erstellen', 'konzept schreiben',
            ],
            'weight': 1.0,
        },
        'legal': {
            'keywords': ['vertrag', 'recht', 'gesetz', 'agb', 'impressum', 'datenschutz',
                        'dsgvo', 'haftung', 'kündigung', 'klage', 'anwalt', 'rechtlich',
                        'rechtsform', 'satzung', 'gesellschaftsvertrag', 'arbeitsvertrag'],
            'weight': 1.0,
            'disclaimer': True,
        },
        'finance': {
            'keywords': ['budget', 'cashflow', 'bilanz', 'gewinn', 'verlust', 'kredit',
                        'darlehen', 'bank', 'investition', 'rendite', 'roi', 'finanzplan',
                        'liquidität', 'rechnungslegung', 'buchhaltung', 'controlling'],
            'weight': 1.0,
            'financial_disclaimer': True,
        },
        'tax': {
            'keywords': ['steuer', 'steuern', 'ust', 'mwst', 'mehrwertsteuer', 'einkommensteuer',
                        'körperschaftsteuer', 'gewerbesteuer', 'finanzamt', 'steuererklärung',
                        'abschreibung', 'betriebsausgaben', 'umsatzsteuer'],
            'weight': 1.0,
            'tax_disclaimer': True,
        },
        'marketing': {
            'keywords': ['marketing', 'werbung', 'social media', 'seo', 'zielgruppe',
                        'kunde', 'marke', 'branding', 'vertrieb', 'verkauf', 'umsatz steigern',
                        'reichweite', 'kampagne', 'content'],
            'weight': 0.9,
        },
        'hr': {
            'keywords': ['mitarbeiter', 'personal', 'hr', 'gehalt', 'lohn', 'einstellung',
                        'bewerbung', 'kündigung', 'arbeitszeit', 'urlaub', 'sozialversicherung',
                        'arbeitnehmer', 'arbeitsvertrag erstellen'],
            'weight': 0.9,
        },
        'strategy': {
            'keywords': ['strategie', 'wachstum', 'skalierung', 'expansion', 'markt',
                        'wettbewerber', 'analyse', 'swot', 'konkurrenz', 'marktforschung',
                        'positionierung', 'differenzierung'],
            'weight': 0.9,
        },
    }

    FOUNDING_SUBTYPES = {
        'rechtsform': ['gmbh', 'ug', 'ag', 'einzelunternehmen', 'gbr', 'ohg', 'kg', 'partg'],
        'anmeldung': ['anmelden', 'anmeldung', 'handelsregister', 'notar', 'gewerbeanmeldung'],
        'kosten': ['kosten', 'kapital', 'stammkapital', 'eigenkapital', 'gründungskosten'],
        'dauer': ['wie lange', 'dauer', 'zeitraum', 'wann', 'schnell'],
    }

    def analyze(self, user_message: str, conversation_history: list = None) -> ReasoningResult:
        """
        Hauptmethode: Analysiert Nutzernachricht und erstellt Reasoning-Plan.
        """
        result = ReasoningResult()
        message_lower = user_message.lower()

        # Schritt 1: Kategorie erkennen
        result.reasoning_steps.append({
            'step': 1,
            'action': 'Frage kategorisieren',
            'input': user_message[:100],
        })

        category, confidence = self._classify_message(message_lower)
        result.category = category
        result.confidence = confidence

        result.reasoning_steps.append({
            'step': 2,
            'action': 'Kategorie erkannt',
            'result': f"Kategorie: {category} (Konfidenz: {confidence:.0%})",
        })

        # Schritt 2: Disclaimer-Bedarf prüfen
        cat_config = self.CATEGORIES.get(category, {})
        result.requires_legal_disclaimer = cat_config.get('disclaimer', False)
        result.requires_tax_disclaimer = cat_config.get('tax_disclaimer', False)
        result.requires_financial_disclaimer = cat_config.get('financial_disclaimer', False)

        # Schritt 3: Kontext-Keywords extrahieren
        result.context_keywords = self._extract_keywords(message_lower)

        result.reasoning_steps.append({
            'step': 3,
            'action': 'Schlüsselwörter extrahiert',
            'result': result.context_keywords[:5],
        })

        # Schritt 4: Tools empfehlen (für Pro/Business)
        result.recommended_tools = self._recommend_tools(category, message_lower)

        # Schritt 5: Enhanced Prompt erstellen
        result.enhanced_prompt = self._enhance_prompt(
            user_message, category, result.context_keywords, conversation_history
        )

        result.reasoning_steps.append({
            'step': 4,
            'action': 'Antwort-Strategie geplant',
            'result': f"Tools: {result.recommended_tools}, Disclaimer: {result.requires_legal_disclaimer}",
        })

        logger.info(f"Reasoning abgeschlossen: {category} ({confidence:.0%})")
        return result

    def _classify_message(self, message: str) -> tuple[str, float]:
        """Klassifiziert die Nachricht in eine Business-Kategorie"""
        scores = {}

        for category, config in self.CATEGORIES.items():
            score = 0
            for keyword in config['keywords']:
                if keyword in message:
                    # Längere Keywords bekommen mehr Gewicht
                    score += len(keyword.split()) * config['weight']
            if score > 0:
                scores[category] = score

        if not scores:
            return 'general', 0.5

        best_category = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = min(0.95, scores[best_category] / total + 0.3)

        return best_category, confidence

    def _extract_keywords(self, message: str) -> list:
        """Extrahiert wichtige Schlüsselwörter"""
        # Stopwörter entfernen
        stopwords = {'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'und', 'oder', 'aber',
                    'wie', 'was', 'wo', 'wer', 'wann', 'warum', 'welche', 'kann', 'muss',
                    'soll', 'will', 'habe', 'bin', 'ist', 'sind', 'war', 'haben', 'sein',
                    'für', 'mit', 'bei', 'von', 'zu', 'in', 'an', 'auf', 'das', 'die', 'der', 'ein', 'eine'}

        words = re.findall(r'\b[a-züöäß]{3,}\b', message)
        return [w for w in words if w not in stopwords][:10]

    def _recommend_tools(self, category: str, message: str) -> list:
        """Empfiehlt passende Business-Tools basierend auf Kategorie"""
        tool_map = {
            'founding': ['founding_wizard', 'legal_form_advisor', 'founding_checklist'],
            'business_plan': ['business_plan_generator', 'financial_projections'],
            'legal': ['legal_document_analyzer', 'contract_checker'],
            'finance': ['cash_flow_calculator', 'financial_planner'],
            'tax': ['tax_overview', 'expense_tracker'],
            'marketing': ['market_research', 'competitor_analysis'],
            'strategy': ['swot_analysis', 'market_research'],
            'hr': ['hr_templates', 'salary_calculator'],
        }
        return tool_map.get(category, ['general_business_advisor'])

    def _enhance_prompt(self, original: str, category: str, keywords: list,
                        history: list = None) -> str:
        """
        Erstellt einen verbesserten Prompt mit Business-Kontext für die KI.
        """
        enhancements = {
            'founding': "Beantworte diese Gründungsfrage mit konkreten Schritten, Kosten und Zeitangaben für Deutschland.",
            'business_plan': "Erstelle eine strukturierte, professionelle Antwort mit klaren Abschnitten.",
            'legal': "Gib eine informativen Überblick, weise aber klar darauf hin, dass ein Rechtsanwalt konsultiert werden sollte.",
            'finance': "Nutze konkrete Zahlen, Beispiele und weise auf einen Steuerberater hin wenn relevant.",
            'tax': "Erkläre die steuerlichen Grundlagen verständlich und empfehle einen Steuerberater für individuelle Beratung.",
            'marketing': "Gib praxiserprobte Marketing-Tipps mit Beispielen aus dem deutschen Markt.",
            'strategy': "Analysiere strategisch mit Vor- und Nachteilen, nutze Frameworks wie SWOT wenn hilfreich.",
            'hr': "Berücksichtige deutsches Arbeitsrecht und gib praktische Empfehlungen.",
        }

        enhancement = enhancements.get(category, "Antworte hilfreich und praxisorientiert.")

        context = ""
        if history and len(history) > 0:
            context = f"\n[Kontext: Der Nutzer hat bereits {len(history)} Nachrichten gesendet in dieser Session.]"

        return f"{enhancement}{context}\n\nFrage: {original}"

    def add_disclaimers(self, response_text: str, reasoning: ReasoningResult) -> str:
        """Fügt notwendige Rechtswarnungen zur Antwort hinzu"""
        disclaimers = []

        if reasoning.requires_legal_disclaimer:
            disclaimers.append(
                "\n\n⚖️ **Rechtlicher Hinweis:** Diese Informationen sind allgemeiner Natur und ersetzen "
                "keine Rechtsberatung. Für konkrete rechtliche Fragen konsultiere bitte einen Rechtsanwalt."
            )

        if reasoning.requires_tax_disclaimer:
            disclaimers.append(
                "\n\n🏦 **Steuerlicher Hinweis:** Diese Informationen sind allgemeiner Natur. "
                "Für individuelle Steuerberatung wende dich an einen Steuerberater oder das Finanzamt."
            )

        if reasoning.requires_financial_disclaimer:
            disclaimers.append(
                "\n\n💡 **Finanzhinweis:** Dies ist keine Finanzberatung. "
                "Bei wichtigen Finanzentscheidungen empfehle ich, einen Finanzberater hinzuzuziehen."
            )

        return response_text + "".join(disclaimers)
