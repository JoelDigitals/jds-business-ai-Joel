"""
JDS Business AI - Legal Assistant
Rechtliche Unterstützung für Unternehmen (kein Ersatz für Anwalt!)
"""
import logging
from typing import Optional

logger = logging.getLogger('ai_engine')

LEGAL_KNOWLEDGE = {
    'vertragstypen': {
        'dienstleistungsvertrag': {
            'beschreibung': 'Vereinbarung über Erbringung von Dienstleistungen',
            'pflichtinhalte': [
                'Vertragsparteien (Name, Adresse)',
                'Beschreibung der Leistung',
                'Vergütung und Zahlungsmodalitäten',
                'Laufzeit und Kündigung',
                'Haftungsregelung',
                'Gerichtsstand',
            ],
            'tipp': 'Leistungsumfang SEHR konkret beschreiben - vermeidet Streit',
        },
        'kaufvertrag': {
            'beschreibung': 'Verkauf von Waren oder Dienstleistungen',
            'pflichtinhalte': [
                'Kaufgegenstand genau beschreiben',
                'Kaufpreis und Zahlungsbedingungen',
                'Lieferung und Eigentumsübergang',
                'Gewährleistung (2 Jahre gesetzlich)',
                'Widerrufsrecht (bei Verbrauchern online: 14 Tage)',
            ],
        },
        'arbeitsvertrag': {
            'beschreibung': 'Arbeitsverhältnis zwischen Arbeitgeber und Arbeitnehmer',
            'pflichtinhalte': [
                'Beginn und Art der Tätigkeit',
                'Arbeitsort',
                'Vergütung',
                'Arbeitszeit (max. 48h/Woche)',
                'Urlaubsanspruch (min. 20 Tage/Jahr)',
                'Kündigungsfristen',
                'Probezeit (max. 6 Monate)',
            ],
            'hinweis': 'Schriftform empfohlen. Mindestlohn beachten!',
        },
        'mietvertrag_gewerbe': {
            'beschreibung': 'Anmietung von Geschäftsräumen',
            'besonderheiten': [
                'Keine Schutzrechte wie bei Wohnraum',
                'Frei verhandelbar',
                'Oft langfristig - sorgfältig prüfen',
                'Kaution verhandeln',
            ],
        },
        'nda': {
            'beschreibung': 'Non-Disclosure Agreement / Geheimhaltungsvereinbarung',
            'wann_noetig': [
                'Gespräche mit potenziellen Partnern',
                'Gespräche mit Investoren',
                'Einstellung von Mitarbeitern mit Zugang zu Geheimnissen',
            ],
            'pflichtinhalte': [
                'Was ist vertraulich?',
                'Wer ist gebunden?',
                'Wie lange gilt die Geheimhaltung?',
                'Ausnahmen',
                'Konsequenzen bei Verstoß',
            ],
        },
    },

    'gesellschaftsrecht': {
        'gmbh_gruendung': {
            'notarkosten': '500-1.500 EUR',
            'handelsregisterkosten': '150-350 EUR',
            'stammkapital_min': 25000,
            'gesellschaftervertrag_pflicht': True,
            'voraussetzungen': [
                'Mindestkapital 25.000 EUR (mind. 12.500 bei Gründung einzahlen)',
                'Notarieller Gesellschaftsvertrag',
                'Handelsregistereintragung',
                'Gewerbeanmeldung',
            ],
        },
        'geschaeftsfuehrung': {
            'pflichten': [
                'Sorgfaltspflicht (wie ordentlicher Kaufmann)',
                'Buchführungspflicht',
                'Steuerpflichten',
                'Insolvenzantragspflicht bei Zahlungsunfähigkeit',
                'Jährlicher Jahresabschluss',
            ],
            'haftung': 'Persönliche Haftung bei Pflichtverletzung möglich',
        },
    },

    'arbeitsrecht': {
        'kuendigungsfristen': {
            'probezeit': '2 Wochen (beiderseits)',
            'nach_2_jahren': '1 Monat zum Monatsende',
            'nach_5_jahren': '2 Monate zum Monatsende',
            'nach_10_jahren': '4 Monate',
            'nach_20_jahren': '7 Monate',
        },
        'mindestlohn_2024': 12.41,
        'arbeitnehmerschutz': [
            'Kündigungsschutz nach 6 Monaten (>10 Mitarbeiter)',
            'Mutterschutz und Elternzeit',
            'Schwerbehinderung: besonderer Kündigungsschutz',
            'Betriebsrat hat Mitspracherecht',
        ],
    },

    'steuerrecht_basics': {
        'steuerarten_unternehmen': {
            'einkommensteuer': 'Für Einzelunternehmer und Personengesellschaften (14-45%)',
            'koerperschaftsteuer': 'Für GmbH/AG: 15% + Solidaritätszuschlag',
            'gewerbesteuer': 'Abhängig von Gemeinde: ca. 7-18% (auf Gewerbeertrag)',
            'umsatzsteuer': 'Regelsteuersatz 19%, ermäßigt 7%',
        },
        'kleinunternehmerregelung': {
            'umsatz_limit': '22.000 EUR/Vorjahr und 50.000 EUR/aktuelles Jahr',
            'vorteil': 'Keine Umsatzsteuer berechnen und abführen',
            'nachteil': 'Kein Vorsteuerabzug möglich',
            'tipp': 'Gut für B2C-Gründer, weniger gut für B2B',
        },
    },

    'abmahnungen': {
        'was_ist_das': 'Aufforderung zur Unterlassung von Rechtsverletzungen',
        'haeufige_gruende': [
            'Fehlendes/fehlerhaftes Impressum',
            'Fehlende Datenschutzerklärung',
            'Wettbewerbsverstöße (irreführende Werbung)',
            'Urheberrechtsverletzungen (Bilder, Texte)',
            'Fehlende AGB / fehlerhafte AGB',
        ],
        'was_tun': [
            '1. Ruhe bewahren, Fristen beachten',
            '2. Anwalt einschalten',
            '3. Rechtmäßigkeit prüfen lassen',
            '4. Niemals voreilig Unterlassungserklärung unterschreiben',
        ],
    },
}


class LegalAssistant:
    """
    Rechtlicher Assistent für allgemeine Informationen.
    KEIN ERSATZ FÜR EINEN RECHTSANWALT!
    """

    DISCLAIMER = "\n\n⚖️ **Wichtiger Hinweis:** Diese Informationen sind allgemeiner Natur und keine Rechtsberatung. Für konkrete Rechtsfragen konsultiere bitte einen Rechtsanwalt."

    def get_contract_template_info(self, contract_type: str) -> str:
        """Gibt Informationen zu einem Vertragstyp zurück"""
        vertraege = LEGAL_KNOWLEDGE['vertragstypen']
        contract_data = vertraege.get(contract_type.lower().replace(' ', '_'))

        if not contract_data:
            return f"Vertragstyp '{contract_type}' nicht gefunden. Verfügbar: {', '.join(vertraege.keys())}"

        result = f"**{contract_type.replace('_', ' ').title()}**\n\n"
        result += f"📋 {contract_data['beschreibung']}\n\n"

        if 'pflichtinhalte' in contract_data:
            result += "**Pflichtinhalte:**\n"
            for item in contract_data['pflichtinhalte']:
                result += f"• {item}\n"

        if 'tipp' in contract_data:
            result += f"\n💡 **Tipp:** {contract_data['tipp']}"

        if 'hinweis' in contract_data:
            result += f"\n⚠️ **Hinweis:** {contract_data['hinweis']}"

        return result + self.DISCLAIMER

    def get_labor_law_info(self, topic: str) -> str:
        """Gibt Informationen zum Arbeitsrecht zurück"""
        ar = LEGAL_KNOWLEDGE['arbeitsrecht']
        result = "**Arbeitsrecht - Grundlagen**\n\n"

        if 'kündigung' in topic.lower():
            result += "**Kündigungsfristen:**\n"
            for zeitraum, frist in ar['kuendigungsfristen'].items():
                result += f"• {zeitraum.replace('_', ' ').title()}: {frist}\n"

        result += f"\n**Aktueller Mindestlohn:** {ar['mindestlohn_2024']} EUR/Stunde\n"
        result += "\n**Wichtige Arbeitnehmerrechte:**\n"
        for recht in ar['arbeitnehmerschutz']:
            result += f"• {recht}\n"

        return result + self.DISCLAIMER

    def analyze_legal_question(self, question: str) -> dict:
        """Analysiert eine Rechtsfrage und gibt Infos + Empfehlungen zurück"""
        question_lower = question.lower()
        result = {
            'category': 'general',
            'response': '',
            'urgency': 'normal',
            'needs_lawyer': False,
            'disclaimer': self.DISCLAIMER,
        }

        if any(w in question_lower for w in ['abmahnung', 'abgemahnt', 'unterlassung']):
            result['category'] = 'abmahnung'
            result['urgency'] = 'high'
            result['needs_lawyer'] = True
            ab = LEGAL_KNOWLEDGE['abmahnungen']
            result['response'] = f"**Abmahnung erhalten - was tun?**\n\n"
            result['response'] += "**Häufige Abmahngründe:**\n"
            for grund in ab['haeufige_gruende']:
                result['response'] += f"• {grund}\n"
            result['response'] += "\n**Sofort-Maßnahmen:**\n"
            for schritt in ab['was_tun']:
                result['response'] += f"{schritt}\n"

        elif any(w in question_lower for w in ['arbeitsvertrag', 'mitarbeiter einstellen', 'angestellte']):
            result['category'] = 'arbeitsrecht'
            result['response'] = self.get_contract_template_info('arbeitsvertrag')

        elif any(w in question_lower for w in ['impressum', 'website pflicht', 'was muss auf']):
            result['category'] = 'impressum'
            pflichten = LEGAL_KNOWLEDGE['gesellschaftsrecht']
            result['response'] = "**Pflichtangaben auf deiner Website (Impressum)**\n\n"
            # Use from business logic
            from .business_logic import KNOWLEDGE_BASE
            for p in KNOWLEDGE_BASE['rechtliche_grundlagen']['pflichtangaben_website']:
                result['response'] += f"• {p}\n"
            result['response'] += "\n⚠️ Fehlendes Impressum kann zu Abmahnungen führen!"

        elif any(w in question_lower for w in ['kündigung', 'kündigen', 'frist']):
            result['category'] = 'kuendigung'
            result['response'] = self.get_labor_law_info('kündigung')

        else:
            result['response'] = "Ich helfe dir gerne bei rechtlichen Grundfragen. Stell mir eine konkretere Frage zu:\n"
            result['response'] += "• Vertragstypen (Arbeitsvertrag, Dienstleistungsvertrag, NDA)\n"
            result['response'] += "• Impressum und Datenschutz\n"
            result['response'] += "• Abmahnungen\n"
            result['response'] += "• Gesellschaftsrecht (GmbH Gründung)\n"
            result['response'] += "• Arbeitsrecht\n"

        return result
