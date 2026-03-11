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
    Unterstützt BEIDE Formate:
      - Strukturiert: "Firma: Joel Digitals\nVorname: Joel\n..."
      - Freitext:     "Schreibe ein Impressum für Joel Digitals (www.joel-digitals.de)"
    """
    data = {}
    msg = user_message

    # ── 1. Strukturierte Felder mit Label: Wert ──────────────────────────────
    labeled_patterns = [
        ('company',    r'(?:firma|company|unternehmen(?:sname)?)\s*[:\-]\s*(.+?)(?=\s*\n|\s+(?:vorname|nachname|adresse|email|tel|plz|keine|ust|website|steuernummer)|$)'),
        ('first_name', r'(?:vorname|firstname)\s*[:\-]\s*([A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df\-]+)'),
        ('last_name',  r'(?:nachname|lastname|familienname)\s*[:\-]\s*([A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df\-]+)'),
        ('address',    r'(?:adresse|anschrift|stra\u00dfe|str\.)\s*[:\-]\s*(.+?)(?=\s*\n|\s+(?:email|tel|vorname|nachname|keine|ust|steuernummer)|$)'),
        ('email',      r'(?:email|e-mail|mail)\s*[:\-]\s*([^\s,\n]+@[^\s,\n]+)'),
        ('phone',      r'(?:tel(?:efon)?|phone|mobil)\s*[:\-]\s*([+\d\s\-/()]{7,})'),
        ('url',        r'(?:website|webseite|url|domain|homepage)\s*[:\-]\s*([^\s,\n]+)'),
        ('vat_id',     r'(?:ust(?:\s*-?\s*id(?:nr\.?)?)?|umsatzsteuer[-\s]?id(?:nr\.)?)\s*[:\-]\s*([DE\d]+)'),
        ('tax_no',     r'(?:steuernummer|steuer[-\s]?nr\.?)\s*[:\-]\s*([/\d ]+)'),
        ('rechtsform', r'(?:rechtsform|firmierung)\s*[:\-]\s*([A-Za-z]+)'),
    ]
    for key, pattern in labeled_patterns:
        m = re.search(pattern, msg, re.IGNORECASE | re.MULTILINE)
        if m:
            data[key] = m.group(1).strip().rstrip(',. ')

    # ── 2. Freitext-Extraktion: URL in Klammern oder nach "für/von" ──────────
    # URL überall im Text — auch in Klammern wie "(www.joel-digitals.de)"
    if 'url' not in data:
        url_m = re.search(
            r'(?:^|\s|\()((https?://|www\.)[^\s\),\n]+)',
            msg, re.IGNORECASE
        )
        if url_m:
            data['url'] = url_m.group(1).rstrip(')')

    # E-Mail überall im Text
    if 'email' not in data:
        mail_m = re.search(r'[\w.\-]+@[\w.\-]+\.\w{2,}', msg)
        if mail_m:
            data['email'] = mail_m.group(0)

    # Telefon überall
    if 'phone' not in data:
        tel_m = re.search(r'(?<!\d)(\+49[\d\s\-/()]{6,}|\b0[\d\s\-/()]{7,})', msg)
        if tel_m:
            data['phone'] = tel_m.group(1).strip()

    # Deutsche Adresse (Straße Nr, PLZ Stadt) — auch ohne Label
    if 'address' not in data:
        addr_m = re.search(
            r'([A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df][A-Za-z\u00e4\u00f6\u00fc\u00df\s\-]+\s+\d+[a-z]?'
            r'(?:[,\s]+\d{5}\s+[A-Za-z\u00e4\u00f6\u00fc\u00df\s]+)?)',
            msg, re.IGNORECASE
        )
        if addr_m:
            data['address'] = addr_m.group(1).strip().rstrip(',')

    # ── 3. Firmenname aus Freitext wenn kein Label gefunden ──────────────────
    if 'company' not in data:
        # "für Joel Digitals" / "von Joel Digitals" / "der Firma Joel Digitals"
        co_m = re.search(
            r'(?:f\u00fcr|fuer|von|der\s+firma|unternehmen)\s+'
            r'([A-Z\u00c4\u00d6\u00dc][A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df0-9 &.\-]{1,50}?)'
            r'(?=\s*[\(\.,\n]|\s+(?:mit|und|f\u00fcr|in|ab|ist|hat|gmbh|ug|ag|www\.|https?:)|$)',
            msg, re.IGNORECASE
        )
        if co_m:
            raw = co_m.group(1).strip().rstrip(',. ')
            # Keine Verben/Stopwörter als Firmenname
            if raw.lower() not in {'ein', 'eine', 'einen', 'mein', 'meine', 'meinen', 'uns', 'mir'}:
                data['company'] = raw

    # ── 4. Boolesche Flags ───────────────────────────────────────────────────
    if re.search(r'keine\s+umsatzsteuer|kleinunternehmer|ohne\s+ust|keine\s+ust', msg, re.IGNORECASE):
        data['no_vat'] = True
    if re.search(r'keine?\s+steuernummer', msg, re.IGNORECASE):
        data['no_tax_no'] = True

    # ── 5. Rechtsform aus Firmennamen ableiten ───────────────────────────────
    company_str = data.get('company', '') + ' ' + msg
    if 'rechtsform' not in data:
        for form in ['GmbH', 'UG', 'AG', 'GbR', 'OHG', 'KG']:
            if re.search(r'\b' + form + r'\b', company_str, re.IGNORECASE):
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
    owner = (f"{first} {last}".strip()) or extras.get('owner', '')
    raw_address = extras.get('address', '')
    email = extras.get('email', '')
    phone = extras.get('phone', '')
    url   = extras.get('url', '')
    no_vat = extras.get('no_vat', False)

    # URL sauber formatieren
    if url and not url.startswith('http'):
        url_display = url
        url_href = 'https://' + url.lstrip('www.')
    elif url:
        url_display = url.replace('https://', '').replace('http://', '')
        url_href = url
    else:
        url_display = ''
        url_href = ''

    # PLZ+Stadt aus Adresse trennen
    street = raw_address
    city_plz = ''
    if raw_address:
        city_m = re.search(r'(\d{5}\s+[A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df][A-Za-z\u00e4\u00f6\u00fc\u00df\s\-]+)', raw_address)
        if city_m:
            city_plz = city_m.group(1).strip()
            street = raw_address[:raw_address.find(city_m.group(0))].strip().rstrip(',')

    # GmbH/UG extra section
    gf_section = ''
    if rechtsform in ('GmbH', 'UG', 'AG'):
        gf_section = (
            f"\n**Handelsregister:** Amtsgericht [Stadt], HRB [Nummer]"
            f"\n**Gesch\u00e4ftsf\u00fchrer/in:** {owner or '[Name]'}"
            f"\n**Stammkapital:** [Betrag] EUR"
        )

    # USt-Abschnitt
    if no_vat:
        vat_section = (
            "Gem\u00e4\u00df \u00a7\u00a019 UStG wird keine Umsatzsteuer erhoben und "
            "daher nicht ausgewiesen (Kleinunternehmerregelung)."
        )
    else:
        vat_id = extras.get('vat_id', '')
        if vat_id:
            vat_section = f"Umsatzsteuer-Identifikationsnummer gem\u00e4\u00df \u00a7\u00a027a UStG: **{vat_id}**"
        else:
            vat_section = None  # fehlt → in Checkliste

    # Kontaktzeilen zusammenbauen (nur vorhandene)
    contact_lines = []
    if phone:
        contact_lines.append(f"Telefon: {phone}")
    if email:
        contact_lines.append(f"E-Mail: {email}")
    if url_display:
        contact_lines.append(f"Website: {url_display}")
    contact_block = '\n'.join(contact_lines) if contact_lines else '_Kontaktdaten noch eintragen_'

    # Adressblock
    addr_lines = []
    if street:
        addr_lines.append(street)
    if city_plz:
        addr_lines.append(city_plz)
    if addr_lines:
        addr_lines.append('Deutschland')
    addr_block = '\n'.join(addr_lines) if addr_lines else '_Adresse noch eintragen_'

    # Verantwortlicher
    verantw_name = owner or company
    verantw_addr = f"{street}, {city_plz}" if (street and city_plz) else addr_block

    # ── Checkliste — NUR für fehlende Felder ──
    checklist = []
    if not owner:
        checklist.append('- [ ] Vor- und Nachname des Inhabers eintragen')
    if not street or not city_plz:
        checklist.append('- [ ] Vollst\u00e4ndige Adresse (Stra\u00dfe, PLZ, Stadt) erg\u00e4nzen')
    if not phone and not email:
        checklist.append('- [ ] Mindestens eine Kontaktm\u00f6glichkeit (Tel. oder E-Mail) eintragen')
    if not email:
        checklist.append('- [ ] E-Mail-Adresse eintragen')
    if vat_section is None:
        checklist.append('- [ ] USt-IdNr. eintragen **oder** Kleinunternehmerregelung aktivieren (§\u00a019 UStG)')
    if rechtsform in ('GmbH', 'UG', 'AG'):
        checklist.append('- [ ] Handelsregisternummer eintragen')
    checklist.append('- [ ] Impressum im Footer jeder Seite gut sichtbar verlinken')

    cl_text = '\n'.join(checklist) if checklist else '- \u2705 Alle Pflichtfelder ausgef\u00fcllt!'

    vat_block = vat_section if vat_section else '_USt-IdNr. noch eintragen oder Kleinunternehmerregelung aktivieren_'

    return f"""## Impressum \u2013 {company}

---

**Angaben gem\u00e4\u00df \u00a7 5 TMG**

**{company}**{f"{chr(10)}{owner}" if owner else ""}
{addr_block}
{gf_section}
**Kontakt:**
{contact_block}

**Umsatzsteuer:**
{vat_block}

**Verantwortlich f\u00fcr den Inhalt nach \u00a7 55 Abs. 2 RStV:**
{verantw_name}
{verantw_addr}

---

### Haftungsausschluss

**Haftung f\u00fcr Inhalte**
Die Inhalte dieser Website wurden mit gr\u00f6\u00dfter Sorgfalt erstellt. F\u00fcr die Richtigkeit, Vollst\u00e4ndigkeit und Aktualit\u00e4t der Inhalte kann keine Gew\u00e4hr \u00fcbernommen werden. Als Diensteanbieter sind wir gem\u00e4\u00df \u00a7 7 Abs. 1 TMG f\u00fcr eigene Inhalte nach den allgemeinen Gesetzen verantwortlich.

**Haftung f\u00fcr Links**
Das Angebot enth\u00e4lt Links zu externen Webseiten Dritter. F\u00fcr die Inhalte verlinkter Seiten ist stets der jeweilige Anbieter verantwortlich. Zum Zeitpunkt der Verlinkung wurden keine Rechtsverst\u00f6\u00dfe festgestellt.

**Urheberrecht**
Die durch den Seitenbetreiber erstellten Inhalte und Werke unterliegen dem deutschen Urheberrecht. Vervielf\u00e4ltigung, Bearbeitung und Verbreitung bed\u00fcrfen der schriftlichen Zustimmung.

---

{f"💡 **Checkliste f\u00fcr fehlende Angaben:**{chr(10)}{cl_text}{chr(10)}{chr(10)}" if any('[ ]' in c for c in checklist) else "✅ **Alle Pflichtfelder ausgef\u00fcllt!**{chr(10)}{chr(10)}"}\
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