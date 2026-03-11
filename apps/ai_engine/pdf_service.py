"""
JDS Business AI - PDF Generation Service
Erstellt professionelle PDFs aus Chat-Antworten (Businesspläne, Reports, etc.)
"""
import io
import logging
from datetime import datetime

logger = logging.getLogger('ai_engine')


def generate_pdf(title: str, content: str, company_name: str = '', user_name: str = '') -> bytes:
    """
    Konvertiert Markdown-Text in ein professionelles PDF.
    Gibt PDF als bytes zurück.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
        import re

        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2.5*cm, rightMargin=2.5*cm,
            topMargin=2.5*cm, bottomMargin=2.5*cm,
            title=title,
            author='JDS Business AI',
        )

        # ── Farben ────────────────────────────────────────────
        INDIGO   = HexColor('#4f46e5')
        INDIGO_L = HexColor('#e0e7ff')
        SLATE_900= HexColor('#0f172a')
        SLATE_700= HexColor('#334155')
        SLATE_500= HexColor('#64748b')
        SLATE_100= HexColor('#f1f5f9')
        EMERALD  = HexColor('#059669')

        # ── Styles ────────────────────────────────────────────
        styles = getSampleStyleSheet()

        s_title = ParagraphStyle('JDSTitle',
            fontSize=26, fontName='Helvetica-Bold',
            textColor=SLATE_900, spaceAfter=4,
            alignment=TA_LEFT, leading=32,
        )
        s_subtitle = ParagraphStyle('JDSSubtitle',
            fontSize=11, fontName='Helvetica',
            textColor=SLATE_500, spaceAfter=20,
        )
        s_h1 = ParagraphStyle('JDSH1',
            fontSize=16, fontName='Helvetica-Bold',
            textColor=INDIGO, spaceBefore=16, spaceAfter=6, leading=20,
        )
        s_h2 = ParagraphStyle('JDSH2',
            fontSize=13, fontName='Helvetica-Bold',
            textColor=SLATE_700, spaceBefore=12, spaceAfter=4, leading=18,
        )
        s_h3 = ParagraphStyle('JDSH3',
            fontSize=11, fontName='Helvetica-Bold',
            textColor=SLATE_700, spaceBefore=8, spaceAfter=3, leading=15,
        )
        s_body = ParagraphStyle('JDSBody',
            fontSize=10, fontName='Helvetica',
            textColor=SLATE_700, spaceAfter=4, leading=15,
        )
        s_bullet = ParagraphStyle('JDSBullet',
            fontSize=10, fontName='Helvetica',
            textColor=SLATE_700, spaceAfter=2, leading=14,
            leftIndent=14, firstLineIndent=0,
        )
        s_footer = ParagraphStyle('JDSFooter',
            fontSize=8, fontName='Helvetica',
            textColor=SLATE_500, alignment=TA_CENTER,
        )

        story = []

        # ── Header ────────────────────────────────────────────
        header_data = [[
            Paragraph(f'<b>{title}</b>', s_title),
        ]]
        header_table = Table(header_data, colWidths=[doc.width])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), INDIGO_L),
            ('TOPPADDING', (0,0), (-1,-1), 16),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ('LEFTPADDING', (0,0), (-1,-1), 16),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 6))

        # Meta-Info
        meta_parts = []
        if company_name:
            meta_parts.append(f'<b>Unternehmen:</b> {company_name}')
        if user_name:
            meta_parts.append(f'<b>Erstellt für:</b> {user_name}')
        meta_parts.append(f'<b>Datum:</b> {datetime.now().strftime("%d.%m.%Y")}')
        meta_parts.append('<b>Erstellt von:</b> JDS Business AI')
        story.append(Paragraph(' &nbsp;|&nbsp; '.join(meta_parts), s_subtitle))
        story.append(HRFlowable(width='100%', thickness=1, color=INDIGO, spaceAfter=12))

        # ── Content parsen ────────────────────────────────────
        def clean(t):
            """Escape XML-Sonderzeichen für ReportLab."""
            return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        def md_inline(t):
            """Markdown inline → ReportLab XML."""
            import re
            t = clean(t)
            t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
            t = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', t)
            t = re.sub(r'`(.+?)`',       r'<font name="Courier">\1</font>', t)
            return t

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]

            # Tabelle erkennen
            if '|' in line and i + 1 < len(lines) and '|' in lines[i+1] and '---' in lines[i+1]:
                table_lines = [line]
                i += 2  # Separator überspringen
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i])
                    i += 1

                table_data = []
                for tl in table_lines:
                    cells = [c.strip() for c in tl.strip('|').split('|')]
                    table_data.append(cells)

                if table_data:
                    col_count = len(table_data[0])
                    col_width = doc.width / col_count
                    rl_table = Table(
                        [[Paragraph(md_inline(c), s_body) for c in row] for row in table_data],
                        colWidths=[col_width] * col_count,
                        repeatRows=1,
                    )
                    ts = TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), INDIGO),
                        ('TEXTCOLOR', (0,0), (-1,0), white),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,-1), 9),
                        ('BACKGROUND', (0,1), (-1,-1), SLATE_100),
                        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, SLATE_100]),
                        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#cbd5e1')),
                        ('TOPPADDING', (0,0), (-1,-1), 5),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                        ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ])
                    rl_table.setStyle(ts)
                    story.append(Spacer(1, 6))
                    story.append(rl_table)
                    story.append(Spacer(1, 6))
                continue

            # Überschriften
            if line.startswith('#### '):
                story.append(Paragraph(md_inline(line[5:]), s_h3))
            elif line.startswith('### '):
                story.append(Paragraph(md_inline(line[4:]), s_h3))
            elif line.startswith('## '):
                story.append(HRFlowable(width='100%', thickness=0.5, color=HexColor('#e2e8f0'), spaceBefore=8, spaceAfter=4))
                story.append(Paragraph(md_inline(line[3:]), s_h1))
            elif line.startswith('# '):
                story.append(Paragraph(md_inline(line[2:]), s_h1))

            # Listen
            elif line.startswith('- [ ] ') or line.startswith('* [ ] '):
                story.append(Paragraph(f'☐ {md_inline(line[6:])}', s_bullet))
            elif line.startswith('- [x] ') or line.startswith('* [x] '):
                story.append(Paragraph(f'☑ {md_inline(line[6:])}', s_bullet))
            elif line.startswith('- ') or line.startswith('* '):
                story.append(Paragraph(f'• {md_inline(line[2:])}', s_bullet))
            elif line.strip() and line[0].isdigit() and '. ' in line[:4]:
                num, rest = line.split('. ', 1)
                story.append(Paragraph(f'<b>{num}.</b> {md_inline(rest)}', s_bullet))

            # Horizontale Linie
            elif line.strip().startswith('---'):
                story.append(HRFlowable(width='100%', thickness=0.5, color=HexColor('#e2e8f0'), spaceAfter=4))

            # Leerzeile
            elif not line.strip():
                story.append(Spacer(1, 5))

            # Normaler Text
            else:
                story.append(Paragraph(md_inline(line), s_body))

            i += 1

        # ── Footer ────────────────────────────────────────────
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width='100%', thickness=0.5, color=HexColor('#e2e8f0')))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f'Erstellt von <b>JDS Business AI</b> · {datetime.now().strftime("%d.%m.%Y %H:%M")} · '
            'Dieses Dokument ist eine KI-generierte Vorlage und ersetzt keine professionelle Beratung.',
            s_footer
        ))

        doc.build(story)
        return buffer.getvalue()

    except ImportError:
        logger.error("reportlab nicht installiert: pip install reportlab")
        raise
    except Exception as e:
        logger.error(f"PDF Fehler: {e}", exc_info=True)
        raise


def is_pdf_worthy(text: str) -> bool:
    """Entscheidet ob eine Antwort als PDF angeboten werden soll."""
    keywords = [
        'businessplan', 'business plan', 'executive summary',
        'swot', 'finanzplan', 'gründungsplan', 'marketingplan',
        'geschäftsplan', 'checkliste', 'gründungs-checkliste',
        'pitch deck', 'unternehmenskonzept',
    ]
    text_lower = text.lower()
    return any(k in text_lower for k in keywords) and len(text) > 500
