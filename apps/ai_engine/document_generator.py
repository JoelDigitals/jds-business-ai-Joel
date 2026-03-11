"""
JDS Business AI — Dokument-Generator
Erstellt fertige Rechtsdokumente, Vorlagen und Texte auf Anfrage.
"""
import re
from datetime import datetime

CURRENT_YEAR = datetime.now().year


def extract_structured_data(user_message):
    """
    Extrahiert strukturierte Felder aus User-Nachrichten.
    Erkennt Muster wie: Firma: X, Vorname: Y, Adresse: Z, Email: X, etc.
    """
    data = {}
    msg = user_message

    field_patterns = [
        ('company',    r'(?:firma|company|unternehmen|unternehmensname)\s*[:\-]\s*(.+?)(?=\s+(?:vorname|nachname|adresse|email|tel|plz|keine|ust|website)|[,\n]|$)'),
        ('first_name', r'(?:vorname|firstname)\s*[:\-]\s*([A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df\-]+)'),
        ('last_name',  r'(?:nachname|lastname|familienname)\s*[:\-]\s*([A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df\-]+)'),
        ('address',    r'(?:adresse|anschrift|stra\u00dfe|str\.)\s*[:\-]\s*(.+?)(?=\s+(?:email|tel|plz|vorname|nachname|keine|ust)|[,\n]|$)'),
        ('email',      r'(?:email|e-mail|mail)\s*[:\-]\s*([^\s,\n]+@[^\s,\n]+)'),
        ('phone',      r'(?:tel(?:efon)?|phone|mobil)\s*[:\-]\s*([+\d\s\-/()]{7,})'),
        ('url',        r'(?:website|webseite|url|domain|homepage)\s*[:\-]\s*([^\s,\n]+)'),
        ('vat_id',     r'(?:ust(?:\s*-?\s*id(?:nr\.?)?)?|umsatzsteuer\s*id(?:nr\.)?)\s*[:\-]\s*([DE\d]+)'),
        ('tax_no',     r'(?:steuernummer|steuer\s*nr\.?)\s*[:\-]\s*([/\d ]+)'),
        ('rechtsform', r'(?:rechtsform|firmierung)\s*[:\-]\s*([A-Za-z]+)'),
    ]
    for key, pattern in field_patterns:
        m = re.search(pattern, msg, re.IGNORECASE)
        if m:
            data[key] = m.group(1).strip().rstrip(',. ')

    # Boolesche Flags
    if re.search(r'keine\s+umsatzsteuer|kleinunternehmer|ohne\s+ust', msg, re.IGNORECASE):
        data['no_vat'] = True
    if re.search(r'keine?\s+steuernummer', msg, re.IGNORECASE):
        data['no_tax_no'] = True

    # Rechtsform aus Firmennamen ableiten
    if 'company' in data and 'rechtsform' not in data:
        for form in ['GmbH', 'UG', 'AG', 'GbR', 'OHG', 'KG']:
            if form.lower() in data['company'].lower():
                data['rechtsform'] = form
                break

    return data


def _extract_extras(user_message):
    """Fallback: Extras aus freiem Text extrahieren."""
    msg = user_message.lower()
    extras = {}
    url_m = re.search(r'(https?://[^\s]+|www\.[^\s]+)', user_message)
    if url_m:
        extras['url'] = url_m.group(1)
    for form in ['GmbH', 'UG', 'AG', 'GbR', 'OHG', 'KG', 'Einzelunternehmen']:
        if form.lower() in msg:
            extras['rechtsform'] = form
            break
    return extras


def generate_document(doc_type, company_name, user_message, struct=None):
    """Hauptfunktion: Leitet an den richtigen Generator weiter."""
    if struct is None:
        struct = extract_structured_data(user_message)
    extras = _extract_extras(user_message)
    merged = {**extras, **struct}
    company = (company_name or merged.get('company') or '[Ihr Unternehmen]').strip()

    generators = {
        'impressum':      _gen_impressum,
        'datenschutz':    _gen_datenschutz,
        'agb':            _gen_agb,
        'nda':            _gen_nda,
        'arbeitsvertrag': _gen_arbeitsvertrag,
        'rechnung':       _gen_rechnung,
        'mahnschreiben':  _gen_mahnung,
    }
    fn = generators.get(doc_type, _gen_impressum)
    return fn(company, merged, user_message)


# ─────────────────────────────────────────────────────────
# IMPRESSUM
# ─────────────────────────────────────────────────────────
def _gen_impressum(company, extras, msg):
    rechtsform = extras.get('rechtsform', 'Einzelunternehmen')
    first = extras.get('first_name', '')
    last  = extras.get('last_name', '')
    owner = (f"{first} {last}".strip()) or extras.get('owner', '[Vorname Nachname]')
    raw_address = extras.get('address', '')
    email = extras.get('email', '[kontakt@ihre-website.de]')
    phone = extras.get('phone', '+49 [Vorwahl] [Nummer]')
    no_vat = extras.get('no_vat', False)

    # PLZ+Stadt aus Adresse trennen
    street = raw_address
    city_plz = ''
    if raw_address:
        city_m = re.search(r'(\d{5}\s+[A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df ]+)', raw_address)
        if city_m:
            city_plz = city_m.group(1).strip()
            street = raw_address[:raw_address.find(city_m.group(0))].strip().rstrip(',')
    if not street:
        street = '[Stra\u00dfe und Hausnummer]'
    if not city_plz:
        city_plz = extras.get('city', '[PLZ] [Stadt]')

    # GmbH/UG extra section
    gf_section = ''
    if rechtsform in ('GmbH', 'UG', 'AG'):
        gf_section = (
            f"\n**Handelsregister:** Amtsgericht [Stadt], HRB [Nummer]"
            f"\n**Gesch\u00e4ftsf\u00fchrer/in:** {owner}"
            f"\n**Stammkapital:** [Betrag] EUR"
        )

    # USt-Abschnitt
    if no_vat:
        vat_section = (
            "Gem\u00e4\u00df \u00a7 19 UStG wird keine Umsatzsteuer erhoben und daher nicht ausgewiesen "
            "(Kleinunternehmerregelung)."
        )
    else:
        vat_id = extras.get('vat_id', '')
        if vat_id:
            vat_section = f"Umsatzsteuer-Identifikationsnummer gem\u00e4\u00df \u00a7 27a UStG: **{vat_id}**"
        else:
            vat_section = "Umsatzsteuer-Identifikationsnummer gem\u00e4\u00df \u00a7 27a UStG: DE[Ihre USt-IdNr.]"

    # Checkliste nur fuer fehlende Felder
    checklist = []
    if '[Stra' in street:
        checklist.append('- [ ] Stra\u00dfe & Hausnummer eintragen')
    if '[PLZ]' in city_plz:
        checklist.append('- [ ] PLZ und Stadt eintragen')
    if '[Vorwahl]' in phone:
        checklist.append('- [ ] Telefonnummer eintragen')
    if '[kontakt' in email:
        checklist.append('- [ ] E-Mail-Adresse eintragen')
    if not no_vat and '[Ihre' in vat_section:
        checklist.append('- [ ] USt-IdNr. eintragen oder Kleinunternehmer-Hinweis aktivieren')
    if rechtsform in ('GmbH', 'UG', 'AG'):
        checklist.append('- [ ] Handelsregisternummer eintragen')
    checklist.append('- [ ] Impressum im Footer jeder Seite gut sichtbar verlinken')

    cl_text = '\n'.join(checklist) if checklist else '- \u2705 Alle Felder vollst\u00e4ndig!'

    return f"""## Impressum f\u00fcr {company}

---

## Impressum

**Angaben gem\u00e4\u00df \u00a7 5 TMG**

**{company}**
{owner}
{street}
{city_plz}
Deutschland
{gf_section}

**Kontakt:**
Telefon: {phone}
E-Mail: {email}

**Umsatzsteuer:**
{vat_section}

**Verantwortlich f\u00fcr den Inhalt nach \u00a7 55 Abs. 2 RStV:**
{owner}
{street}, {city_plz}

---

## Haftungsausschluss

**Haftung f\u00fcr Inhalte**
Die Inhalte dieser Website wurden mit gr\u00f6\u00dfter Sorgfalt erstellt. F\u00fcr die Richtigkeit, Vollst\u00e4ndigkeit und Aktualit\u00e4t der Inhalte kann keine Gew\u00e4hr \u00fcbernommen werden.

**Haftung f\u00fcr Links**
Das Angebot enth\u00e4lt Links zu externen Webseiten Dritter. F\u00fcr die Inhalte verlinkter Seiten ist stets der jeweilige Anbieter verantwortlich.

**Urheberrecht**
Die durch die Seitenbetreiber erstellten Inhalte und Werke unterliegen dem deutschen Urheberrecht.

---

\U0001f4a1 **Checkliste:**
{cl_text}

\u2696\ufe0f **Hinweis:** Vorlage gem\u00e4\u00df \u00a7 5 TMG. Bei GmbH/UG oder speziellen Branchen empfiehlt sich eine anwaltliche Pr\u00fcfung."""


# ─────────────────────────────────────────────────────────
# DATENSCHUTZERKLAERUNG
# ─────────────────────────────────────────────────────────
def _gen_datenschutz(company, extras, msg):
    owner = (extras.get('first_name', '') + ' ' + extras.get('last_name', '')).strip() or '[Vorname Nachname]'
    email = extras.get('email', '[datenschutz@ihre-website.de]')

    return f"""## Datenschutzerkl\u00e4rung f\u00fcr {company}

---

## Datenschutzerkl\u00e4rung

**Stand: {datetime.now().strftime('%B %Y')}**

## 1. Verantwortlicher

**{company}**
{owner}
[Adresse]
E-Mail: {email}

## 2. Welche Daten wir erheben

Bei der Nutzung unserer Website werden automatisch erfasst:
- IP-Adresse (anonymisiert nach 7 Tagen)
- Datum und Uhrzeit des Zugriffs
- Aufgerufene Seiten und Referrer-URL
- Browsertyp und Betriebssystem

**Rechtsgrundlage:** Art. 6 Abs. 1 lit. f DSGVO

## 3. Kontaktformular / E-Mail

Bei Kontaktaufnahme speichern wir die Anfrage inkl. Kontaktdaten.
**Rechtsgrundlage:** Art. 6 Abs. 1 lit. b DSGVO

## 4. Cookies

Technisch notwendige Cookies: keine Einwilligung erforderlich.
Optionale Cookies (Analyse, Marketing): Einwilligung gem. Art. 6 Abs. 1 lit. a DSGVO.

## 5. Ihre Rechte

- **Auskunft** (Art. 15 DSGVO)
- **Berichtigung** (Art. 16 DSGVO)
- **L\u00f6schung** (Art. 17 DSGVO)
- **Einschr\u00e4nkung** (Art. 18 DSGVO)
- **Daten\u00fcbertragbarkeit** (Art. 20 DSGVO)
- **Widerspruch** (Art. 21 DSGVO)

Anfragen an: {email}

## 6. Beschwerderecht

BfDI \u2014 Graurheindorfer Str. 153, 53117 Bonn | www.bfdi.bund.de

---

\U0001f4a1 **Erg\u00e4nzungen je nach Situation:**
- [ ] Hosting-Anbieter nennen (IONOS, Hetzner, etc.)
- [ ] Google Analytics / Matomo erw\u00e4hnen (falls genutzt)
- [ ] Social-Media-Plugins erg\u00e4nzen
- [ ] Cookie-Banner implementieren

\u2696\ufe0f **Hinweis:** Vorlage f\u00fcr Standardf\u00e4lle. Bei Online-Shops oder US-Tools Anpassungen n\u00f6tig."""


# ─────────────────────────────────────────────────────────
# AGB
# ─────────────────────────────────────────────────────────
def _gen_agb(company, extras, msg):
    is_shop = any(w in msg.lower() for w in ['shop', 'kaufen', 'bestell', 'produkt', 'versand'])
    context = 'Online-Shop' if is_shop else 'Dienstleistungen'

    return f"""## AGB f\u00fcr {company}

---

## Allgemeine Gesch\u00e4ftsbedingungen ({context})

**{company}** | [Adresse] | **Stand: {datetime.now().strftime('%B %Y')}**

## \u00a7 1 Geltungsbereich

Gelten f\u00fcr alle Vertr\u00e4ge zwischen **{company}** und dem Kunden.

## \u00a7 2 Vertragsschluss

Angebote freibleibend. Best\u00e4tigung der Auftragsannahme schriftlich (E-Mail gen\u00fcgt).

## \u00a7 3 Preise

Alle Preise in Euro zzgl. gesetzlicher MwSt.
*(Bei Kleinunternehmer: Endpreise, keine MwSt. ausgewiesen)*

## \u00a7 4 Zahlung

F\u00e4llig **14 Tage** nach Rechnungserhalt. Bei Verzug: Zinsen 9 % \u00fcber Basiszinssatz (\u00a7 288 BGB).

## \u00a7 5 Gew\u00e4hrleistung

Es gelten die gesetzlichen Gew\u00e4hrleistungsrechte.

## \u00a7 6 Haftungsbeschr\u00e4nkung

Haftung nur f\u00fcr Vorsatz und grobe Fahrl\u00e4ssigkeit. Bei einfacher Fahrl\u00e4ssigkeit begrenzt auf typische Sch\u00e4den.

## \u00a7 7 Datenschutz

Gem\u00e4\u00df unserer Datenschutzerkl\u00e4rung auf der Website.

## \u00a7 8 Schlussbestimmungen

Deutsches Recht gilt. Gerichtsstand [Stadt] (bei Kaufleuten).

---

\U0001f4a1 **Checkliste:**
- [ ] **Widerrufsbelehrung erg\u00e4nzen** (Pflicht bei B2C!)
- [ ] Zahlungsfrist anpassen
- [ ] Kleinunternehmer-Regelung pr\u00fcfen
- [ ] AGB in jeder Rechnung verlinken

\u2696\ufe0f **Hinweis:** Anwaltliche Pr\u00fcfung empfohlen, besonders bei B2C."""


# ─────────────────────────────────────────────────────────
# NDA
# ─────────────────────────────────────────────────────────
def _gen_nda(company, extras, msg):
    return f"""## NDA f\u00fcr {company}

---

## Geheimhaltungsvereinbarung (NDA)

**Partei A:** {company}, [Adresse]
**Partei B:** [Name/Unternehmen], [Adresse]
**Stand: {datetime.now().strftime('%d.%m.%Y')}**

## \u00a7 1 Gegenstand

Zusammenarbeit im Bereich **[Projektbeschreibung]** mit Austausch vertraulicher Informationen.

## \u00a7 2 Vertrauliche Informationen

Gesch\u00e4ftsgeheimnisse, Finanzdaten, Quellcode, Kundenlisten, Preiskalkulationen.

## \u00a7 3 Geheimhaltungspflicht

Strikte Geheimhaltung. Keine Weitergabe an Dritte ohne schriftliche Zustimmung.

## \u00a7 4 Laufzeit

**[2/3/5] Jahre** ab Unterzeichnung.

## \u00a7 5 Vertragsstrafe bei Versto\u00df

**[Betrag] EUR** + Schadensersatz.

---

**Unterschriften:** _________________  |  _________________

---

\U0001f4a1 Vertragsstrafe festlegen \u2022 Laufzeit anpassen \u2022 Von beiden Parteien unterschreiben

\u2696\ufe0f **Hinweis:** Anwaltliche Beratung bei hohem Schadenspotenzial empfohlen."""


# ─────────────────────────────────────────────────────────
# ARBEITSVERTRAG
# ─────────────────────────────────────────────────────────
def _gen_arbeitsvertrag(company, extras, msg):
    return f"""## Arbeitsvertrag-Vorlage f\u00fcr {company}

---

## Arbeitsvertrag

**Arbeitgeber:** {company}, [Adresse]
**Arbeitnehmer/in:** [Vorname Nachname], [Adresse]

## \u00a7 1 Beginn, T\u00e4tigkeit, Ort

Beginn: **[Datum]** | T\u00e4tigkeit: **[Berufsbezeichnung]** | Ort: **[Ort / Remote]**

## \u00a7 2 Probezeit

6 Monate Probezeit. K\u00fcndigungsfrist: 2 Wochen.

## \u00a7 3 Arbeitszeit

**[Stunden] Stunden/Woche** (max. 48h gesetzlich)

## \u00a7 4 Verg\u00fctung

Bruttogehalt: **[Betrag] EUR/Monat** \u2014 Auszahlung letzter Werktag des Monats.

## \u00a7 5 Urlaub

**[24/28/30] Werktage** j\u00e4hrlich *(Minimum bei 5-Tage-Woche: 20 Tage)*

## \u00a7 6 K\u00fcndigung

Nach Probezeit: gesetzliche Fristen (\u00a7 622 BGB). Schriftform erforderlich.

## \u00a7 7 Geheimhaltung

Stillschweigen \u00fcber Betriebsgeheimnisse auch nach Beendigung.

---

**Unterschriften:** _________________  |  _________________

---

\U0001f4a1 **Hinweise:**
- [ ] Mindestlohn: **12,82 \u20ac/Stunde** (ab 01.01.2025)
- [ ] Sozialversicherung anmelden
- [ ] Bei Minijob/Teilzeit: Sonderregeln beachten

\u2696\ufe0f **Hinweis:** Basisvorlage. Tarifvertr\u00e4ge beachten."""


# ─────────────────────────────────────────────────────────
# RECHNUNGSVORLAGE
# ─────────────────────────────────────────────────────────
def _gen_rechnung(company, extras, msg):
    return f"""## Rechnungsvorlage f\u00fcr {company}

---

**{company}** | [Adresse] | USt-IdNr. oder Kleinunternehmer-Hinweis

**An:** [Kunde, Adresse]

**Rechnungs-Nr.:** {CURRENT_YEAR}-001 | **Datum:** {datetime.now().strftime('%d.%m.%Y')} | **F\u00e4llig:** [Datum + 14 Tage]

| Pos. | Beschreibung | Menge | Einzelpreis | Gesamt |
|------|-------------|-------|-------------|--------|
| 1    | [Leistung]  | 1     | [Preis] \u20ac  | [Preis] \u20ac |

**Netto:** [X] \u20ac | **MwSt 19%:** [Y] \u20ac | **Gesamt: [Z] \u20ac**

IBAN: DE[...] | BIC: [...] | Verwendungszweck: Rechnung {CURRENT_YEAR}-001

---

\U0001f4a1 Pflichtangaben: Name+Adresse beider Parteien \u2022 Steuernummer/USt-IdNr. \u2022 Rechnungsnummer \u2022 Leistungsdatum \u2022 Netto+MwSt+Brutto

\u2696\ufe0f Aufbewahrungspflicht: 10 Jahre (\u00a7 147 AO)."""


# ─────────────────────────────────────────────────────────
# MAHNSCHREIBEN
# ─────────────────────────────────────────────────────────
def _gen_mahnung(company, extras, msg):
    return f"""## Mahnschreiben-Vorlage f\u00fcr {company}

---

**{company}** | [Adresse]
**An:** [Schuldner, Adresse]

**Betreff: Mahnung \u2014 Rechnung Nr. [Nummer]**

[Stadt], {datetime.now().strftime('%d.%m.%Y')}

Sehr geehrte/r [Name],

trotz unserer Rechnung vom **[Datum]** \u00fcber **[Betrag] EUR** haben wir keinen Zahlungseingang verzeichnen k\u00f6nnen.

Bitte \u00fcberweisen Sie bis **[Datum + 10 Tage]** auf:
IBAN: DE[...] | Verwendungszweck: Rechnung [Nummer]

Andernfalls sehen wir uns gezwungen, rechtliche Schritte einzuleiten.

Mit freundlichen Gr\u00fc\u00dfen, {company}

---

\U0001f4a1 3 Stufen: Zahlungserinnerung \u2192 1. Mahnung \u2192 Mahnbescheid (www.online-mahnantrag.de)

\u2696\ufe0f Ab Verzug: Zinsen 9 % + 40 \u20ac Pauschale (\u00a7 288 Abs. 5 BGB)."""