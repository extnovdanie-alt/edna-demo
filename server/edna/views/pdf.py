import base64,hashlib,hmac,io,json,os,re,secrets,sqlite3,ssl,threading,time
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from pathlib import Path
from xml.sax.saxutils import escape
import notifications,inventory,inventory_integration
from edna.errors import HTTPError,require


def pdf_bytes(context, term, evidence):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.pagesizes import A4
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48)
    styles = getSampleStyleSheet()
    styles['Title'].textColor = colors.HexColor('#2968c8')
    story = [Paragraph('E.D.N.A. | GESTÃO DE EQUIPAMENTOS', styles['Title']), Paragraph('Emitente de Declarações e Normas de Acordo', styles['Normal']), Paragraph('Comprovante de aceite eletrônico' + (' - DEMONSTRAÇÃO' if evidence['demo'] else ''), styles['Normal']), Spacer(1, 22)]
    snap = json.loads(term['snapshot'])
    for title, value in [('Documento', f"#{term['id']:05d} · {term['kind']} · versão 1"), ('Colaborador', snap['name']), ('Identidade no diretório', snap['person']), ('Categoria', context.CATEGORIES.get(snap.get('category'), 'Equipamento')), ('Equipamento', snap['model']), ('Número de série', snap.get('serial') or 'Não informado — serial opcional para esta categoria'), ('Tipo de uso', snap['kind']), ('Prazo', snap['due'] or 'Sem prazo definido')]:
        story.append(Paragraph('<b>' + escape(title) + ':</b> ' + escape(value), styles['BodyText']))
    story += [Spacer(1, 18), Paragraph('Declaração aceita', styles['Heading2'])]
    for para in term['body'].split('\n'):
        if para:
            story.append(Paragraph(escape(para), styles['BodyText']))
    story += [Spacer(1, 18), Paragraph('Registro do aceite', styles['Heading2'])]
    for key, label in [('name', 'Nome informado'), ('at', 'Data e hora (UTC)'), ('user', 'Conta autenticada'), ('ip', 'Endereço de origem'), ('auth', 'Autenticação'), ('text_sha256', 'SHA-256 do texto')]:
        story.append(Paragraph('<b>' + label + ':</b> ' + escape(str(evidence[key])), styles['BodyText']))
    story += [Spacer(1, 14), Paragraph('A pessoa confirmou a leitura e a concordância com o texto acima. Registro de aceite eletrônico por conta autenticada e nome digitado. Não contém assinatura com certificado digital.', styles['BodyText'])]

    def footer(canvas, document):
        canvas.setFillColor(colors.HexColor('#ffe600'))
        canvas.rect(0, A4[1] - 18, A4[0], 18, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor('#555555'))
        canvas.setFont('Helvetica', 8)
        canvas.drawString(48, 28, 'E.D.N.A. | Registro interno de equipamentos')
        canvas.drawRightString(A4[0] - 48, 28, str(document.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
