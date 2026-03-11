"""
JDS Business AI - Business Logic & Wissensdatenbank
Umfangreiches Wissen über deutsche Unternehmensführung, Gründung & mehr.
Diese Datenbank dient als Basis für intelligente Antworten.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger('ai_engine')


# ============================================================
# WISSENSDATENBANK - Deutsche Unternehmensführung
# ============================================================

KNOWLEDGE_BASE = {
    'rechtsformen': {
        'GmbH': {
            'vollname': 'Gesellschaft mit beschränkter Haftung',
            'mindestkapital': 25000,
            'gruendungskosten': '1.500 - 3.000 EUR',
            'haftung': 'Begrenzt auf Gesellschaftsvermögen',
            'gesellschafter': 'Mind. 1',
            'vorteile': [
                'Beschränkte Haftung - persönliches Vermögen geschützt',
                'Professionelle Außenwirkung',
                'Flexibel in der Gestaltung',
                'Fremdkapitalaufnahme einfacher',
            ],
            'nachteile': [
                'Hohes Mindestkapital (25.000 EUR)',
                'Aufwändige Buchhaltung (Jahresabschluss)',
                'Körperschaftsteuer + Gewerbesteuer',
                'Handelsregisterpflicht (laufende Kosten)',
            ],
            'geeignet_fuer': 'Unternehmen mit mehreren Gesellschaftern, Startups mit Investoren',
            'gruendungsschritte': [
                '1. Gesellschaftsvertrag notariell beurkunden',
                '2. Stammkapital auf Geschäftskonto einzahlen',
                '3. Anmeldung beim Handelsregister',
                '4. Gewerbeanmeldung beim Gewerbeamt',
                '5. Anmeldung beim Finanzamt (Fragebogen)',
                '6. ggf. IHK-Mitgliedschaft',
            ],
        },
        'UG': {
            'vollname': 'Unternehmergesellschaft (haftungsbeschränkt)',
            'mindestkapital': 1,
            'gruendungskosten': '300 - 1.000 EUR',
            'haftung': 'Begrenzt auf Gesellschaftsvermögen',
            'gesellschafter': 'Mind. 1',
            'vorteile': [
                'Startkapital ab 1 EUR möglich',
                'Beschränkte Haftung',
                'Schnelle Gründung möglich',
                'Günstiger Einstieg in GmbH-Welt',
            ],
            'nachteile': [
                '25% Gewinnthesaurierungspflicht (bis 25.000 EUR)',
                'Geringere Außenwirkung als GmbH',
                'Kein Mindestkapital = kein Puffer',
                '"Mini-GmbH" Wahrnehmung',
            ],
            'geeignet_fuer': 'Gründer mit wenig Startkapital, Freelancer die expandieren',
        },
        'Einzelunternehmen': {
            'vollname': 'Einzelunternehmen / Freiberufler',
            'mindestkapital': 0,
            'gruendungskosten': '20 - 100 EUR (nur Gewerbeanmeldung)',
            'haftung': 'Unbegrenzt - auch Privatvermögen',
            'gesellschafter': '1 (der Inhaber)',
            'vorteile': [
                'Sofort einsatzbereit',
                'Minimaler Aufwand',
                'Geringe laufende Kosten',
                'Einfache Buchhaltung (EÜR bis 60.000 EUR Umsatz)',
            ],
            'nachteile': [
                'Volle persönliche Haftung',
                'Keine Trennung Privat/Geschäftlich',
                'Schwieriger für Investoren',
                'Steuerlich limitiert',
            ],
            'geeignet_fuer': 'Freelancer, kleine Handwerker, nebenberuflich Selbstständige',
        },
        'GbR': {
            'vollname': 'Gesellschaft bürgerlichen Rechts',
            'mindestkapital': 0,
            'gruendungskosten': '0 - 500 EUR',
            'haftung': 'Unbegrenzt - gesamtschuldnerisch',
            'gesellschafter': 'Mind. 2',
            'geeignet_fuer': 'Kleine Gemeinschaftsprojekte, Freiberufler-Teams',
        },
    },

    'gruendungsschritte_allgemein': [
        {
            'schritt': 1,
            'title': 'Geschäftsidee validieren',
            'beschreibung': 'Marktforschung, Zielgruppe definieren, Alleinstellungsmerkmal (USP) herausarbeiten',
            'dauer': '2-4 Wochen',
            'kosten': '0 EUR (eigene Recherche)',
            'tools': ['Befragungen', 'Wettbewerbsanalyse', 'Google Trends', 'Branchen-Statistiken'],
        },
        {
            'schritt': 2,
            'title': 'Businessplan erstellen',
            'beschreibung': 'Executive Summary, Marktanalyse, Finanzplanung, Marketing-Strategie',
            'dauer': '2-6 Wochen',
            'kosten': '0 EUR (selbst) bis 3.000 EUR (Berater)',
        },
        {
            'schritt': 3,
            'title': 'Rechtsform wählen',
            'beschreibung': 'Abhängig von Kapital, Gesellschaftern, Haftungswunsch',
            'dauer': '1 Woche',
            'kosten': '0 EUR (Beratung)',
        },
        {
            'schritt': 4,
            'title': 'Gewerbeanmeldung / Finanzamt',
            'beschreibung': 'Gewerbe anmelden, Fragebogen zur steuerlichen Erfassung ausfüllen',
            'dauer': '1-2 Wochen',
            'kosten': '20-65 EUR (Gewerbeanmeldung)',
        },
        {
            'schritt': 5,
            'title': 'Geschäftskonto eröffnen',
            'beschreibung': 'Separate Konten für Geschäft und Privat sind essentiell',
            'empfehlungen': ['N26 Business', 'Kontist', 'Commerzbank', 'Deutsche Bank Business'],
        },
        {
            'schritt': 6,
            'title': 'Buchhaltung einrichten',
            'beschreibung': 'Software für Rechnungen, Ausgaben, Steuer',
            'tools': ['Lexware', 'DATEV', 'Fastbill', 'Invoiz', 'Sevdesk'],
        },
        {
            'schritt': 7,
            'title': 'Versicherungen abschließen',
            'wichtige': ['Betriebshaftpflicht', 'Berufshaftpflicht (Freelancer)', 'Krankenversicherung'],
        },
    ],

    'businessplan_struktur': {
        'kapitel': [
            {
                'nummer': 1,
                'titel': 'Executive Summary',
                'inhalt': 'Kurzfassung aller wichtigen Aspekte (max. 2 Seiten)',
                'wichtigkeit': 'SEHR HOCH - wird zuerst gelesen',
            },
            {
                'nummer': 2,
                'titel': 'Unternehmen & Gründer',
                'inhalt': 'Unternehmensgeschichte, Team, Qualifikationen',
            },
            {
                'nummer': 3,
                'titel': 'Produkt / Dienstleistung',
                'inhalt': 'Was bietest du an? Alleinstellungsmerkmal (USP), Nutzen für Kunden',
            },
            {
                'nummer': 4,
                'titel': 'Markt & Wettbewerb',
                'inhalt': 'Marktgröße, Zielgruppe, Wettbewerbsanalyse, SWOT',
            },
            {
                'nummer': 5,
                'titel': 'Marketing & Vertrieb',
                'inhalt': 'Wie erreichst du Kunden? Preisgestaltung, Kanäle',
            },
            {
                'nummer': 6,
                'titel': 'Finanzplanung',
                'inhalt': 'Umsatzprognose, Kostenplan, Cashflow, Break-Even-Analyse',
                'wichtigkeit': 'SEHR HOCH für Investoren und Banken',
            },
            {
                'nummer': 7,
                'titel': 'Risikoanalyse',
                'inhalt': 'Was kann schiefgehen? Wie begegnest du den Risiken?',
            },
        ],
        'tipps': [
            'Realistisch sein - Banken merken übertriebene Prognosen',
            'Konkrete Zahlen verwenden',
            'Quellen für Marktdaten angeben',
            'Von außen lesen lassen bevor du einreichst',
        ],
    },

    'rechtliche_grundlagen': {
        'pflichtangaben_website': [
            'Vollständiger Name und Adresse',
            'Telefon und E-Mail',
            'Handelsregisternummer (wenn zutreffend)',
            'USt-IdNr. (wenn vorhanden)',
            'Datenschutzerklärung (DSGVO)',
            'Bei GmbH: Geschäftsführer, Sitz, Stammkapital',
        ],
        'wichtige_vertraege': [
            'Allgemeine Geschäftsbedingungen (AGB)',
            'Arbeitsverträge (Schriftform empfohlen)',
            'Kundenverträge / Dienstleistungsverträge',
            'Geheimhaltungsvereinbarungen (NDA)',
            'Gesellschaftsvertrag',
            'Mietvertrag für Geschäftsräume',
        ],
        'dsgvo_basics': [
            'Datenschutzerklärung auf jeder Website Pflicht',
            'Einwilligung für Newsletter und Tracking',
            'Datensparsamkeit: Nur notwendige Daten speichern',
            'Auskunftsrecht der Kunden',
            'Meldepflicht bei Datenpannen (72h)',
        ],
    },

    'finanzierung': {
        'eigenfinanzierung': 'Eigenes Kapital - keine Schulden, aber begrenzt',
        'bankkredit': 'Gründerkredit der KfW Bank oft günstig',
        'foerderung': [
            'KfW Gründerkredit',
            'BAFA Gründungsberatung',
            'Bundesländer-Programme (variieren)',
            'EU-Förderungen (EFRE)',
            'Gründerstipendium NRW (regional)',
        ],
        'venture_capital': 'Für skalierbare Startups - gibt Anteile ab',
        'crowdfunding': ['Kickstarter', 'Indiegogo', 'Startnext (DE)'],
        'business_angels': 'Erfahrene Unternehmer die investieren und beraten',
    },
}


class BusinessLogic:
    """
    Business-Logik Engine - nutzt die Wissensdatenbank für strukturierte Antworten
    """

    def get_rechtsform_comparison(self, rechtsformen: list = None) -> dict:
        """Vergleicht verschiedene Rechtsformen"""
        if not rechtsformen:
            rechtsformen = ['GmbH', 'UG', 'Einzelunternehmen']

        result = {}
        for rf in rechtsformen:
            if rf in KNOWLEDGE_BASE['rechtsformen']:
                result[rf] = KNOWLEDGE_BASE['rechtsformen'][rf]

        return result

    def get_gruendungsschritte(self, rechtsform: str = 'allgemein') -> list:
        """Gibt Gründungsschritte für eine Rechtsform zurück"""
        if rechtsform in KNOWLEDGE_BASE['rechtsformen']:
            rf_data = KNOWLEDGE_BASE['rechtsformen'][rechtsform]
            if 'gruendungsschritte' in rf_data:
                return rf_data['gruendungsschritte']

        return KNOWLEDGE_BASE['gruendungsschritte_allgemein']

    def get_businessplan_template(self) -> dict:
        """Gibt Businessplan-Struktur zurück"""
        return KNOWLEDGE_BASE['businessplan_struktur']

    def generate_founding_checklist(self, rechtsform: str) -> str:
        """Generiert eine Gründungs-Checkliste als Text"""
        steps = self.get_gruendungsschritte(rechtsform)
        rf_data = KNOWLEDGE_BASE['rechtsformen'].get(rechtsform, {})

        checklist = f"# Gründungs-Checkliste: {rechtsform}\n\n"

        if rf_data:
            checklist += f"**Mindestkapital:** {rf_data.get('mindestkapital', 'k.A.')} EUR\n"
            checklist += f"**Geschätzte Gründungskosten:** {rf_data.get('gruendungskosten', 'k.A.')}\n"
            checklist += f"**Haftung:** {rf_data.get('haftung', 'k.A.')}\n\n"

        checklist += "## Schritte:\n\n"
        for i, step in enumerate(steps, 1):
            if isinstance(step, dict):
                checklist += f"- [ ] **{step.get('title', step.get('schritt', i))}**: {step.get('beschreibung', '')}\n"
            else:
                checklist += f"- [ ] {step}\n"

        return checklist

    def analyze_business_plan_request(self, industry: str = '', company_type: str = '') -> str:
        """Erstellt eine Businessplan-Gliederung"""
        template = KNOWLEDGE_BASE['businessplan_struktur']
        result = "# Businessplan-Struktur für dein Unternehmen\n\n"

        for kapitel in template['kapitel']:
            result += f"## {kapitel['nummer']}. {kapitel['titel']}\n"
            result += f"**Inhalt:** {kapitel['inhalt']}\n"
            if kapitel.get('wichtigkeit'):
                result += f"⭐ **Wichtigkeit:** {kapitel['wichtigkeit']}\n"
            result += "\n"

        result += "\n## 💡 Tipps:\n"
        for tip in template['tipps']:
            result += f"- {tip}\n"

        return result


def _generate_personalized_businessplan(company_name: str, original_message: str) -> str:
    """
    Erstellt einen personalisierten Businessplan.
    Versucht zuerst Groq/LLM, Fallback auf strukturierte Template-Antwort.
    """
    import re, datetime
    from django.conf import settings

    name = company_name.strip() if company_name else ''
    year = datetime.date.today().year
    msg = original_message.lower()

    # ── Versuche LLM für personalisierten Plan ─────────────
    groq_key = getattr(settings, 'GROQ_API_KEY', '') or ''
    if groq_key and name:
        try:
            prompt = f"""Erstelle einen vollständigen, professionellen Businessplan für das Unternehmen "{name}".

Anfrage des Nutzers: {original_message}

Der Businessplan soll enthalten:
1. Executive Summary (2-3 Sätze über {name})
2. Unternehmensbeschreibung & Gründer
3. Produkt/Dienstleistung & USP
4. Markt & Zielgruppe (konkrete Zahlen schätzen)
5. Wettbewerbsanalyse mit Tabelle
6. SWOT-Analyse als Tabelle
7. Marketing & Vertrieb (konkrete Kanäle)
8. Finanzplanung (3-Jahres-Prognose mit realistischen Zahlen)
9. Risikoanalyse
10. 90-Tage-Aktionsplan mit Checkboxen

Formatiere mit Markdown (## Überschriften, **fett**, | Tabellen, - Listen).
Sei spezifisch für {name} — keine generischen Floskeln.
Schreibe auf Deutsch, professionell und praxisnah."""

            import urllib.request, json
            messages = [
                {"role": "system", "content": "Du bist ein erfahrener Unternehmensberater. Erstelle detaillierte, individuelle Businesspläne auf Deutsch."},
                {"role": "user", "content": prompt}
            ]
            payload = json.dumps({
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "max_tokens": 3000,
                "temperature": 0.7,
            }).encode('utf-8')
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            text = data['choices'][0]['message']['content'].strip()
            if text and len(text) > 500:
                return text
        except Exception as e:
            pass  # Fallback auf Template

    # ── Branche erkennen ───────────────────────────────────
    if any(w in msg for w in ['digital', 'software', 'app', 'tech', 'it', 'web', 'online', 'saas', 'e-commerce']):
        branche = "Digitale Dienstleistungen / Tech"
        usp = f"Innovative digitale Lösungen — skalierbar, nutzerfreundlich, zukunftssicher"
        zielgruppe = "KMU, Startups und digitale Unternehmer"
        umsatz = [("monatlich", "5.000–10.000€"), ("Jahr 1", "60.000–120.000€"), ("Jahr 2", "150.000–300.000€"), ("Jahr 3", "300.000–600.000€")]
        kosten = ["Software-Lizenzen & Hosting (500–2.000€/Mo)", "Marketing & Ads (1.000–3.000€/Mo)", "Personal/Freelancer (je nach Bedarf)"]
        kanale = ["Website mit SEO-Strategie", "LinkedIn & Xing (B2B)", "Content Marketing & YouTube", "Google Ads & Retargeting"]
        foerderung = "EXIST-Gründerstipendium (bis 3.000€/Mo), KfW StartGeld (bis 125.000€)"
    elif any(w in msg for w in ['handel', 'shop', 'verkauf', 'produkt', 'import', 'export']):
        branche = "Handel / E-Commerce"
        usp = "Kuratiertes Sortiment mit exzellentem Service und schneller Lieferung"
        zielgruppe = "Endkonsumenten und Geschäftskunden im DACH-Raum"
        umsatz = [("monatlich", "8.000–20.000€"), ("Jahr 1", "100.000–250.000€"), ("Jahr 2", "250.000–500.000€"), ("Jahr 3", "500.000–1.000.000€")]
        kosten = ["Wareneinkauf (40–60% Marge)", "Lager & Logistik (10–15%)", "Marketing (10–20%)", "Plattformgebühren (2–15%)"]
        kanale = ["Online-Shop (Shopify/WooCommerce)", "Amazon & eBay Marketplace", "Instagram & Pinterest", "Google Shopping Ads"]
        foerderung = "KfW StartGeld (bis 125.000€), Handelskammer-Förderprogramme"
    elif any(w in msg for w in ['beratung', 'consulting', 'coach', 'training', 'bildung']):
        branche = "Beratung & Coaching"
        usp = "Praxiserprobte Expertise mit messbaren Ergebnissen für Klienten"
        zielgruppe = "Unternehmen und Fach-/Führungskräfte"
        umsatz = [("monatlich", "4.000–8.000€"), ("Jahr 1", "50.000–100.000€"), ("Jahr 2", "100.000–200.000€"), ("Jahr 3", "200.000–400.000€")]
        kosten = ["Büro/Home-Office (0–2.000€/Mo)", "Marketing & Auftritte (500–2.000€/Mo)", "Tools & Software (200–500€/Mo)"]
        kanale = ["LinkedIn (organisch + Ads)", "Empfehlungsnetzwerk", "Vorträge & Webinare", "Eigene Website mit Blog"]
        foerderung = "BAFA Unternehmensberatungsförderung (bis 3.500€), Bildungsprämie"
    elif any(w in msg for w in ['restaurant', 'café', 'food', 'gastronomie', 'lieferservice']):
        branche = "Gastronomie & Food"
        usp = "Authentisches Konzept mit Qualitätsprodukten und einzigartigem Ambiente"
        zielgruppe = "Lokale Laufkundschaft, Stammgäste, Event-Buchungen"
        umsatz = [("monatlich", "15.000–30.000€"), ("Jahr 1", "180.000–360.000€"), ("Jahr 2", "200.000–400.000€"), ("Jahr 3", "250.000–500.000€")]
        kosten = ["Miete (10–15% Umsatz)", "Wareneinsatz (25–35%)", "Personal (30–35%)", "Betrieb & Marketing (10%)"]
        kanale = ["Google My Business", "Instagram & TikTok", "Lieferplattformen (Lieferando)", "Lokale Events & PR"]
        foerderung = "KfW StartGeld, DEHOGA-Förderprogramme, Gastro-Bürgschaften"
    else:
        branche = "Dienstleistungen & Service"
        usp = "Zuverlässige Qualität mit persönlichem Service und schneller Umsetzung"
        zielgruppe = "Privat- und Geschäftskunden regional und überregional"
        umsatz = [("monatlich", "3.000–8.000€"), ("Jahr 1", "40.000–80.000€"), ("Jahr 2", "80.000–150.000€"), ("Jahr 3", "150.000–300.000€")]
        kosten = ["Personal & Subunternehmer", "Material & Ausstattung", "Marketing & Akquise", "Büro & Verwaltung"]
        kanale = ["Empfehlungen & Mundpropaganda", "Google My Business & SEO", "Social Media (Facebook/Instagram)", "Lokale Netzwerke & IHK"]
        foerderung = "KfW StartGeld (bis 125.000€), Gründungszuschuss (Arbeitsagentur)"

    display_name = name if name else "dein Unternehmen"

    return f"""# 📋 Businessplan: {display_name}

**Erstellt:** {datetime.date.today().strftime("%d.%m.%Y")} | **Branche:** {branche} | **Jahr:** {year}

---

## 1. Executive Summary

**{display_name}** ist ein Unternehmen im Bereich {branche}. Das Unternehmen bietet {usp.lower()} an und richtet sich primär an {zielgruppe.lower()}.

Die wichtigsten Erfolgsfaktoren: klare Positionierung, konsequente Kundenorientierung und effizientes Kostenmanagement. Das Ziel für Jahr 1: Break-Even erreichen und eine stabile Kundenbasis aufbauen.

---

## 2. Unternehmen & Gründer

| Kriterium | Detail |
|-----------|--------|
| **Unternehmensname** | {display_name} |
| **Rechtsform** | Empfehlung: UG (haftungsbeschränkt) → später GmbH |
| **Gründungsjahr** | {year} |
| **Branche** | {branche} |
| **Standort** | [Ort eintragen] |

**Gründer-Profil:**
- **Name:** [Vorname Nachname]
- **Funktion:** Geschäftsführer/in
- **Stärken:** [Relevante Erfahrungen & Qualifikationen]
- **Lücken:** [Bereiche wo externe Unterstützung nötig]

---

## 3. Produkt / Dienstleistung

**USP (Alleinstellungsmerkmal):**
{usp}

**Angebot:**
- **Einstieg:** [Basispaket] – [Preis] €
- **Standard:** [Vollpaket] – [Preis] €
- **Premium:** [Individuelle Lösung] – [Preis] €

**Kundennutzen:** Zeitersparnis · Qualität · Zuverlässigkeit · Persönliche Betreuung

---

## 4. Markt & Zielgruppe

**Primäre Zielgruppe:** {zielgruppe}

**Marktgröße (Deutschland):**
Der Markt für {branche} wächst jährlich um ca. 8–15% und bietet großes Potenzial für Neueinsteiger mit klarer Nischenstrategie.

| Segment | TAM | SAM | SOM (realistisch) |
|---------|-----|-----|-------------------|
| Deutschland | 10–50 Mrd. € | 100–500 Mio. € | 200.000–2 Mio. € |

---

## 5. Wettbewerbsanalyse

| Kriterium | {display_name} | Wettbewerber A | Wettbewerber B |
|-----------|----------------|----------------|----------------|
| Preis | Mittel–günstig | Hoch | Niedrig |
| Qualität | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Service | Sehr persönlich | Standard | Basis |
| Reaktionszeit | Schnell | Mittel | Langsam |
| **Vorteil** | **Nische + Service** | Markenbekanntheit | Preis |

---

## 6. SWOT-Analyse

| | **Positiv** | **Negativ** |
|---|---|---|
| **Intern** | ✅ **Stärken:** Expertise, Agilität, niedrige Fixkosten, Kundennähe | ⚠️ **Schwächen:** Fehlende Markenbekanntheit, begrenzte Ressourcen |
| **Extern** | 🚀 **Chancen:** Wachsender Markt, Digitalisierung, Partnerschaften | ⛔ **Risiken:** Wettbewerbsdruck, wirtschaftliche Lage, Fachkräftemangel |

---

## 7. Marketing & Vertrieb

**Kanäle:**
{chr(10).join(f"- {k}" for k in kanale)}

**Marketing-Budget (Empfehlung):**
- Monat 1–3: 500–1.000€/Monat (Aufbau)
- Ab Monat 4: 10–15% des Umsatzes (Wachstum)

**Conversion-Funnel:**
Reichweite → Interesse → Lead → Angebot → Abschluss → Empfehlung

---

## 8. Finanzplanung

**Umsatzprognose:**
| Zeitraum | Umsatz | Kosten (est.) | Ergebnis |
|----------|--------|---------------|----------|
{chr(10).join(f"| {p[0]} | {p[1]} | [Kosten] | [Ergebnis] |" for p in umsatz)}

**Hauptkostenpositionen:**
{chr(10).join(f"- {k}" for k in kosten)}

**Förderungen & Finanzierung:**
- {foerderung}
- Eigenkapital: [Betrag] € (empfohlen: min. 20% Eigenanteil)
- **Break-Even:** Voraussichtlich Monat [X]

---

## 9. Risikoanalyse

| Risiko | Wahrsch. | Auswirkung | Gegenmaßnahme |
|--------|----------|------------|---------------|
| Zu wenig Kunden | Mittel | Hoch | Aktiv netzwerken, Kaltakquise, Testangebote |
| Zahlungsausfälle | Niedrig | Mittel | Anzahlung 30%, Factoring, Mahnwesen |
| Starker Wettbewerb | Mittel | Mittel | USP schärfen, Nische finden, Qualität betonen |
| Liquiditätsengpass | Niedrig | Hoch | 3-Monats-Rücklage, Kreditrahmen reservieren |
| Ausfall Gründer | Niedrig | Sehr hoch | Versicherung, Vertretungsregeln, Dokumentation |

---

## 10. 90-Tage-Aktionsplan

**Monat 1 — Fundament legen:**
- [ ] Rechtsform wählen und Gewerbe/GmbH anmelden
- [ ] Geschäftskonto eröffnen (empfohlen: N26 Business, Commerzbank)
- [ ] Website launchen (WordPress + Elementor oder Squarespace)
- [ ] Social-Media-Profile anlegen und befüllen
- [ ] Erstangebot formulieren und Preise festlegen

**Monat 2 — Erste Kunden gewinnen:**
- [ ] Netzwerk aktivieren — Familie, Freunde, LinkedIn-Kontakte
- [ ] Erstes Angebot verschicken (Ziel: 3 Testklunden)
- [ ] Google My Business einrichten
- [ ] Buchhaltungssoftware einrichten (sevDesk, Lexoffice)
- [ ] Förderanträge stellen ({foerderung.split(",")[0]})

**Monat 3 — Prozesse optimieren:**
- [ ] Feedback von ersten Kunden einholen und auswerten
- [ ] Angebot und Preise anpassen
- [ ] Erstes Marketing-Budget einsetzen
- [ ] Quartalsreview: Zahlen, Lernpunkte, nächste Schritte

---

💡 **Hinweis:** Dieser Businessplan ist eine individualisierte Vorlage für **{display_name}**. Fülle die Platzhalter mit deinen konkreten Zahlen aus. Für Bankgespräche oder Investoren empfiehlt sich die Zusammenarbeit mit einem Steuerberater oder Unternehmensberater.

⚖️ *Rechtlicher Hinweis: KI-generierte Vorlage — ersetzt keine professionelle Unternehmensberatung oder Steuerberatung.*"""


def get_rule_based_response(user_message: str) -> str:
    """
    Regelbasierte Fallback-Antworten wenn das KI-Modell nicht verfügbar ist.
    Nutzt die Wissensdatenbank für strukturierte Antworten.
    """
    message_lower = user_message.lower()
    logic = BusinessLogic()


    # Begrüßungen & Smalltalk
    import random
    msg_stripped = message_lower.strip().rstrip('!?,. ')
    GREETINGS = ['hallo', 'hi', 'hey', 'guten morgen', 'guten tag', 'guten abend', 'moin', 'servus', 'jo', 'na']
    CAPABILITY_Q = ['was kannst du', 'was bist du', 'wer bist du', 'was machst du', 'was kann ich', 'wie kannst du', 'hilf mir', 'was bietest du', 'funktionen']
    HOW_ARE_YOU = ['wie geht', 'wie laeuft', 'alles gut']

    if any(g == msg_stripped for g in GREETINGS) or (len(user_message) < 20 and any(g in message_lower for g in GREETINGS)):
        greets = [
            "Hallo! Schoen, dass du da bist! Ich bin **JDS Business AI** -- dein KI-Berater fuer Gruendung, Businessplanung und alle Business-Fragen.\n\nWomit kann ich dir heute helfen?",
            "Hi! Ich bin JDS Business AI -- immer bereit fuer deine Business-Fragen!\n\nOb Businessplan, GmbH-Gruendung, Marketing oder Foerderung -- einfach losschreiben!",
        ]
        return random.choice(greets)

    if any(q in message_lower for q in CAPABILITY_Q):
        return """## Was ich fuer dich tun kann

Ich bin **JDS Business AI** -- dein KI-Assistent fuer alle Business-Themen:

**Gruendung & Rechtsformen**
- GmbH, UG, Einzelunternehmen, AG, GbR gruenden
- Kosten, Vor-/Nachteile, Gruendungsschritte

**Businessplanung**
- Vollstaendige Businessplaene erstellen (auch als PDF!)
- Executive Summary, SWOT, Finanzplan, Pitch Deck

**Rechtliche Grundlagen**
- Impressum, Datenschutz (DSGVO), AGB
- Vertraege, Markenrecht, Wettbewerbsrecht

**Finanzen & Foerderung**
- KfW-Foerderprogramme, BAFA, EXIST
- Cashflow, Break-Even, Steuern (Grundlagen)

**Marketing & Strategie**
- Marktanalyse, Zielgruppe, SWOT
- Social Media, SEO, Content-Strategie

**Tipp:** Nenn mir deinen Unternehmensnamen und ich erstelle dir einen personalisierten Businessplan -- auch als PDF zum Download!"""

    if any(q in message_lower for q in HOW_ARE_YOU):
        return "Mir geht es gut -- danke! Ich bin bereit fuer deine Business-Fragen. Was steht heute auf der Agenda?"


    # GmbH Fragen
    if 'gmbh' in message_lower and ('gründen' in message_lower or 'gründung' in message_lower or 'kosten' in message_lower):
        data = KNOWLEDGE_BASE['rechtsformen']['GmbH']
        return f"""**GmbH Gründung - Übersicht**

Eine GmbH (Gesellschaft mit beschränkter Haftung) ist die häufigste Rechtsform für Unternehmen in Deutschland.

**Wesentliche Fakten:**
- Mindestkapital: {data['mindestkapital']:,} EUR
- Gründungskosten: {data['gruendungskosten']}
- Haftung: {data['haftung']}

**Vorteile:**
{chr(10).join(['• ' + v for v in data['vorteile']])}

**Nachteile:**
{chr(10).join(['• ' + n for n in data['nachteile']])}

**Gründungsschritte:**
{chr(10).join(data['gruendungsschritte'])}

Brauchst du mehr Details zu einem bestimmten Schritt?"""

    # Rechtsform Vergleich
    elif any(w in message_lower for w in ['welche rechtsform', 'rechtsform wählen', 'gmbh oder ug', 'ug oder gmbh']):
        return """**Rechtsform-Vergleich für Gründer**

**UG (Unternehmergesellschaft) - "Mini-GmbH"**
- Mindestkapital: ab 1 EUR ✅
- Haftung: begrenzt ✅
- Kosten: 300-1.000 EUR
- Nachteil: 25% Gewinnrücklage bis 25.000 EUR ⚠️

**GmbH**
- Mindestkapital: 25.000 EUR
- Haftung: begrenzt ✅
- Kosten: 1.500-3.000 EUR
- Professionelle Außenwirkung ✅

**Einzelunternehmen/Freiberufler**
- Mindestkapital: 0 EUR ✅
- Haftung: UNBEGRENZT ⚠️
- Kosten: 20-100 EUR
- Am einfachsten zu gründen ✅

**Empfehlung:**
- Wenig Kapital → UG, später zur GmbH wechseln
- Kapital vorhanden, mehrere Gesellschafter → GmbH
- Freelancer, kleines Risiko → Einzelunternehmen

Welche Situation trifft auf dich zu?"""

    # Businessplan — personalisiert wenn Unternehmensname erkannt
    elif any(w in message_lower for w in ['businessplan', 'business plan', 'geschäftsplan', 'businessplan erstellen', 'business plan erstellen']):
        # Unternehmensname aus der Nachricht extrahieren
        import re
        name_match = re.search(
            r'(?:für|für das unternehmen|von|für mein(?:e)?(?:n)?\s+(?:unternehmen|firma|startup|company)?)\s+([A-Z][^\s,\.?!]{1,40}(?:\s+[A-Z][^\s,\.?!]{0,30})*)',
            user_message, re.IGNORECASE
        )
        company_name = name_match.group(1).strip() if name_match else ''
        return _generate_personalized_businessplan(company_name, user_message)

    # Gründungsschritte allgemein
    elif any(w in message_lower for w in ['gründen', 'selbstständig', 'startup', 'gewerbe']):
        return """**Unternehmen gründen - Die ersten Schritte**

**Phase 1: Vorbereitung**
1. ✅ Geschäftsidee validieren (Marktforschung, Zielgruppe)
2. ✅ Businessplan erstellen
3. ✅ Finanzierung sichern

**Phase 2: Rechtliches**
4. ✅ Rechtsform wählen (GmbH, UG, Einzelunternehmen?)
5. ✅ Gewerbeanmeldung (20-65 EUR)
6. ✅ Finanzamt: Fragebogen zur steuerlichen Erfassung

**Phase 3: Betrieb starten**
7. ✅ Geschäftskonto eröffnen
8. ✅ Buchhaltungssoftware einrichten
9. ✅ Pflichtversicherungen abschließen
10. ✅ Website mit Impressum und Datenschutz

**Typische Kosten:**
- Einzelunternehmen: 50-200 EUR
- UG: 500-1.500 EUR
- GmbH: 2.000-5.000 EUR

Über welchen Schritt möchtest du mehr erfahren?"""

    # Finanzierung
    elif any(w in message_lower for w in ['finanzierung', 'kredit', 'kfw', 'förderung', 'kapital']):
        fin = KNOWLEDGE_BASE['finanzierung']
        return f"""**Finanzierungsmöglichkeiten für Gründer**

**Staatliche Förderung (empfohlen!):**
{chr(10).join(['• ' + f for f in fin['foerderung']])}

**KfW Gründerkredit** ist besonders empfehlenswert:
- Günstige Zinsen
- Tilgungsfreie Anlaufzeit
- Bis zu 100.000 EUR für Kleinunternehmen

**Weitere Optionen:**
• Eigenfinanzierung: {fin['eigenfinanzierung']}
• Business Angels: {fin['business_angels']}
• Crowdfunding: {', '.join(fin['crowdfunding'])}

**Tipp:** Kombiniere mehrere Quellen. Viele erfolgreiche Gründer nutzen 50% Eigenkapital + 50% KfW-Kredit.

Für mehr Details zu einer bestimmten Finanzierungsart, frag einfach!"""

    # DSGVO / Datenschutz
    elif any(w in message_lower for w in ['dsgvo', 'datenschutz', 'impressum', 'datenschutzerklärung']):
        legal = KNOWLEDGE_BASE['rechtliche_grundlagen']
        return f"""**DSGVO & rechtliche Pflichten für Unternehmen**

**Pflichtangaben auf deiner Website (Impressum):**
{chr(10).join(['• ' + p for p in legal['pflichtangaben_website']])}

**DSGVO-Basics (Datenschutz):**
{chr(10).join(['• ' + d for d in legal['dsgvo_basics']])}

**Wichtige Verträge:**
{chr(10).join(['• ' + v for v in legal['wichtige_vertraege']])}

⚖️ **Hinweis:** Für individuelle Rechtsberatung wende dich an einen Rechtsanwalt. Die Nichteinhaltung kann zu Abmahnungen und Bußgeldern führen.

Über welches Thema möchtest du mehr erfahren?"""

    # ── SWOT-Analyse ──
    elif any(w in message_lower for w in ['swot', 'stärken schwächen', 'chancen risiken', 'swot-analyse', 'swot analyse']):
        return """## SWOT-Analyse

Die **SWOT-Analyse** ist ein klassisches strategisches Werkzeug zur Standortbestimmung deines Unternehmens.

| | Positiv | Negativ |
|---|---|---|
| **Intern** | ✅ **Stärken** (Strengths) | ⚠️ **Schwächen** (Weaknesses) |
| **Extern** | 🚀 **Chancen** (Opportunities) | ⛔ **Risiken** (Threats) |

## Die 4 Felder erklärt

**✅ Stärken (intern)**
Was macht dein Unternehmen besser als die Konkurrenz?
- Einzigartiges Know-how, starke Marke, loyale Kunden
- Effiziente Prozesse, gutes Team, Patente

**⚠️ Schwächen (intern)**
Wo hast du Nachholbedarf?
- Fehlende Ressourcen, veraltete Technologie
- Hohe Kosten, eingeschränkte Reichweite

**🚀 Chancen (extern)**
Welche Markttrends kannst du nutzen?
- Wachsende Zielgruppen, neue Technologien
- Veränderungen bei Mitbewerbern, neue Gesetze

**⛔ Risiken (extern)**
Was könnte dein Geschäft gefährden?
- Neue Konkurrenten, Konjunkturabschwung
- Technologischer Wandel, regulatorische Änderungen

## Strategien ableiten

| Kombination | Strategie |
|---|---|
| Stärke + Chance | **SO-Strategie**: Chancen mit Stärken nutzen |
| Stärke + Risiko | **ST-Strategie**: Stärken gegen Risiken einsetzen |
| Schwäche + Chance | **WO-Strategie**: Schwächen durch Chancen ausgleichen |
| Schwäche + Risiko | **WT-Strategie**: Risiken minimieren, Schwächen abbauen |

💡 **Tipp**: Nenn mir deinen Unternehmensnamen und ich erstelle dir eine vollständige SWOT-Analyse in deinem Businessplan!

⚖️ Hinweis: Für strategische Entscheidungen empfiehlt sich professionelle Unternehmensberatung."""

    # ── Marketing & Strategie ──
    elif any(w in message_lower for w in ['marketing', 'strategie', 'marktanalyse', 'zielgruppe', 'positionierung', 'branding', 'seo', 'social media', 'content']):
        return """## Marketing & Strategie für Gründer

## 1. Zielgruppe definieren
Wer sind deine Kunden? Je spezifischer, desto besser!
- **B2B**: Welche Branche, Unternehmensgröße, Entscheider?
- **B2C**: Alter, Einkommen, Interessen, Probleme?

## 2. Positionierung & USP
Was macht dich einzigartig?
- Preis-Vorteil, Qualitäts-Vorteil oder Nischen-Fokus
- Formuliere deinen USP in einem Satz

## 3. Marketingkanäle

| Kanal | Kosten | Eignung | Aufwand |
|---|---|---|---|
| Google My Business | Kostenlos | Lokal | Niedrig |
| Instagram/Facebook | Ab 0€ | B2C | Mittel |
| LinkedIn | Ab 0€ | B2B | Mittel |
| Google Ads | Ab 5€/Tag | Alle | Mittel |
| SEO/Blog | Zeit | Alle | Hoch |
| Empfehlungen | Kostenlos | Alle | Niedrig |

## 4. Marketing-Budget (Empfehlung)
- **Phase 1** (Monat 1-3): 500–1.000€/Monat für ersten Bekanntheitsaufbau
- **Phase 2** (ab Monat 4): 10–15% des Umsatzes reinvestieren

## 5. Content-Strategie
- Erstelle wöchentlich 2-3 Posts auf deinen Hauptkanälen
- Blog-Artikel für SEO (mindestens 1.000 Wörter)
- Kundenbewertungen aktiv sammeln (Google, Trustpilot)

💡 **Möchtest du einen vollständigen Marketing-Plan** für dein Unternehmen? Nenn mir einfach deinen Firmennamen!"""

    # ── Finanzplanung & Förderung ──
    elif any(w in message_lower for w in ['förderung', 'foerderung', 'kfw', 'bafa', 'exist', 'finanzierung', 'kredit', 'kapital', 'investor']):
        return """## Förderungen & Finanzierung für Gründer

## Staatliche Förderungen

| Programm | Betrag | Wer? | Besonderheit |
|---|---|---|---|
| **KfW StartGeld** | bis 125.000€ | Alle Gründer | 80% Haftungsfreistellung |
| **KfW ERP-Gründerkredit** | bis 25 Mio.€ | Wachstumsphase | Niedrigzins |
| **EXIST-Gründerstipendium** | bis 3.000€/Mo | Studierende/Absolventen | + Sachkosten |
| **Gründungszuschuss** | ~1.500€/Mo | ALG-I-Empfänger | 6 Monate + optional 9 Monate |
| **BAFA-Beratungsförderung** | bis 4.000€ | Alle | 50-80% Beratungskosten |
| **Mikromezzaninkapital** | bis 50.000€ | Kleine Unternehmen | Eigenkapital-ähnlich |

## Vorgehen

- **Schritt 1**: Bundesland-spezifische Förderung prüfen (z.B. NRW.Bank, IBB Berlin)
- **Schritt 2**: KfW-Antrag über Hausbank stellen (nicht direkt bei KfW!)
- **Schritt 3**: Businessplan fertig haben — ist Pflicht für fast alle Förderungen

## Private Finanzierungsquellen
- **Business Angels**: 25.000–500.000€, Beteiligung + Know-how
- **Crowdfunding**: Kickstarter, Startnext — gut für B2C-Produkte
- **Bootstrapping**: Selbstfinanzierung — volle Kontrolle, aber langsamer

💡 **Tipp**: Kombiniere mehrere Förderungen! KfW + Gründungszuschuss + BAFA ist möglich.

⚖️ Hinweis: Förderanträge erfordern genaue Prüfung. Steuerberater oder Gründerberater einschalten!"""

    # ── Arbeitsvertrag & HR ──
    elif any(w in message_lower for w in ['arbeitsvertrag', 'mitarbeiter einstellen', 'gehalt', 'lohn', 'kündigung', 'probezeit', 'minijob']):
        return """## Arbeitsvertrag & Mitarbeiter

## Pflichtinhalte eines Arbeitsvertrags

| Inhalt | Details |
|---|---|
| **Beginn & Tätigkeit** | Startdatum, Berufsbezeichnung, Aufgaben |
| **Arbeitsort** | Büro, Remote, hybrid |
| **Vergütung** | Bruttogehalt, Bonus, Extras |
| **Arbeitszeit** | Stunden/Woche (max. 48h), Überstunden |
| **Urlaub** | Mindestens 20 Tage/Jahr (bei 5-Tage-Woche) |
| **Kündigungsfristen** | Probezeit: 2 Wochen; danach gestaffelt |
| **Probezeit** | Maximal 6 Monate |

## Mindestlohn 2024/2025
- Aktueller Mindestlohn: **12,82€/Stunde** (ab Jan 2025)
- Minijob-Grenze: **556€/Monat**

## Einstellungsprozess
1. Stelle mit Anforderungsprofil ausschreiben
2. Bewerbungsgespräch + ggf. Probearbeit
3. Arbeitsvertrag aufsetzen (Schriftform empfohlen!)
4. Sozialversicherung anmelden (Krankenkasse)
5. Lohnsteuer ans Finanzamt abführen

⚖️ **Wichtig**: Arbeitsrecht ist komplex. Für individuelle Verträge immer Rechtsanwalt einschalten!"""

    # ── Default: Zuletzt noch Dokument-Generator versuchen ──
    # (Fängt Fälle ab die durch den Intent-Check in views.py nicht erkannt wurden)
    else:
        DOC_KEYWORDS = {
            'impressum': ['impressum'],
            'datenschutz': ['datenschutz', 'datenschutzerklärung'],
            'agb': [' agb', 'allgemeine geschäftsbedingungen'],
            'nda': ['nda', 'geheimhaltungsvertrag'],
            'arbeitsvertrag': ['arbeitsvertrag', 'anstellungsvertrag'],
            'rechnung': ['rechnungsvorlage', 'musterrechnung'],
            'mahnschreiben': ['mahnung', 'mahnschreiben'],
        }
        detected_doc = None
        for dk, dkw in DOC_KEYWORDS.items():
            if any(k in message_lower for k in dkw):
                detected_doc = dk
                break
        if detected_doc:
            import re
            try:
                from .document_generator import generate_document, extract_structured_data
                struct = extract_structured_data(user_message)
                company = struct.get('company', '')
                if not company:
                    cm = re.search(
                        r'(?:für|fuer|for|von|firma|unternehmen)[ \t]+'
                        r'([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9 \-\.&]+?)'
                        r'(?:\s+(?:mit|und|für|in)|[,\.?!\n]|$)',
                        user_message.split('\n')[0], re.IGNORECASE
                    )
                    company = cm.group(1).strip() if cm else ''
                return generate_document(detected_doc, company, user_message, struct)
            except Exception:
                pass

        # Letzter Fallback: hilfreiche generische Antwort
        return """Wie kann ich dir helfen? Ich bin **JDS Business AI** — dein Assistent für Gründer & Unternehmer.

Hier ein paar Beispiele was ich kann:
- *"Schreibe ein Impressum für [Firmenname]"*
- *"Erstelle einen Businessplan für [Firmenname]"*
- *"Wie gründe ich eine GmbH?"*
- *"Welche Förderungen gibt es?"*
- *"Erstelle eine Datenschutzerklärung"*

💡 **Tipp:** Nenn mir deinen Firmennamen und konkrete Daten — ich erstelle dir sofort ein fertiges Dokument!"""