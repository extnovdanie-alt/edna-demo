"""Convites por SMTP com fila persistida. Em DEMO_MODE, nenhum e-mail é enviado."""
import json
import os
import re
import secrets
import smtplib
import ssl
import threading
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from urllib.parse import urlsplit

_started=False
_start_lock=threading.Lock()

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def valid_email(value):
    address=str(value or '').strip().lower()
    if len(address)>254 or '..' in address or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}",address):
        raise ValueError('Informe um e-mail válido.')
    return address

def signing_days(value=5):
    if type(value) is int and 1<=value<=5:
        return value
    if isinstance(value,str) and re.fullmatch('[1-5]',value):
        return int(value)
    raise ValueError('O prazo de assinatura deve ser de 1 a 5 dias corridos.')

def settings():
    try:
        if os.getenv('MAIL_MODE')!='smtp':return None
        host=os.environ['SMTP_HOST'].strip()
        sender=valid_email(os.environ['MAIL_FROM'])
        base=os.environ['PORTAL_BASE_URL'].strip().rstrip('/')
        url=urlsplit(base)
        if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:return None
        transport=os.getenv('SMTP_TLS','starttls')
        if transport not in ('starttls','ssl'):return None
        port=int(os.getenv('SMTP_PORT','465' if transport=='ssl' else '587'))
        if not host or not 1<=port<=65535:return None
        user=os.getenv('SMTP_USERNAME','')
        password=os.getenv('SMTP_PASSWORD','')
        if bool(user)!=bool(password):return None
        return {'host':host,'sender':sender,'base':base,'transport':transport,'port':port,'user':user,'password':password}
    except (KeyError,ValueError):return None

def delivery_mode(demo):
    return 'simulation' if demo else 'smtp' if settings() else 'unconfigured'

def invitation_content(term,base=''):
    snapshot=json.loads(term['snapshot'])
    link=base+'/?termo='+str(term['id']) if base else '[Endereço do portal ainda não configurado]'
    due=datetime.fromisoformat(term['sign_due_at']).astimezone(timezone.utc).strftime('%d/%m/%Y às %H:%M (UTC)')
    kind='devolução' if term['kind']=='devolucao' else 'responsabilidade'
    subject='E.D.N.A. — Solicitação de assinatura do termo #'+str(term['id']).zfill(5)
    body=(f"Olá, {snapshot['name']}.\n\nHá um termo de {kind} para você assinar.\n"
          f"Equipamento: {snapshot.get('serial') or 'Sem serial'} — {snapshot['model']}.\n"
          f"Prazo de assinatura: {term['sign_days']} dia(s) corrido(s).\nAssine até: {due}.\n\n"
          f"Acesse o portal e entre com sua própria conta:\n{link}\n\n"
          "E.D.N.A. — Emitente de Declarações e Normas de Acordo\nEquipe de TI")
    return subject,body,link

def enqueue(c,term,recipient,demo):
    mode=delivery_mode(demo)
    config=settings() if mode=='smtp' else None
    subject,body,link=invitation_content(term,config['base'] if config else '')
    c.execute('''INSERT OR IGNORE INTO email_outbox(term,recipient,subject,body,link,status,created,message_id)
        VALUES (?,?,?,?,?,?,?,?)''',(term['id'],valid_email(recipient),subject,body,link,
        'simulated' if demo else 'queued' if config else 'not_configured',utcnow(),secrets.token_hex(16)))

def transmit(row,config):
    message=EmailMessage()
    message['From']=config['sender'];message['To']=row['recipient'];message['Subject']=row['subject']
    message['Date']=format_datetime(datetime.now(timezone.utc))
    message['Message-ID']='<edna-'+row['message_id']+'@'+config['sender'].split('@')[1]+'>'
    message.set_content(row['body'])
    context=ssl.create_default_context(cafile=os.getenv('SMTP_CA_FILE') or None)
    connection=(smtplib.SMTP_SSL(config['host'],config['port'],timeout=15,context=context)
                if config['transport']=='ssl' else smtplib.SMTP(config['host'],config['port'],timeout=15))
    with connection as smtp:
        smtp.ehlo()
        if config['transport']=='starttls':smtp.starttls(context=context);smtp.ehlo()
        if config['user']:smtp.login(config['user'],config['password'])
        refused=smtp.send_message(message,from_addr=config['sender'],to_addrs=[row['recipient']])
        if refused:raise RuntimeError('Recipient refused')

def process_one(db_factory,demo=False):
    # A configuração de demonstração nunca chama SMTP, mesmo com credenciais presentes.
    if demo:return False
    config=settings()
    if not config:return False
    with db_factory() as c:
        c.execute('BEGIN IMMEDIATE')
        # Uma queda durante a transmissão pode ter ocorrido após a aceitação pelo SMTP.
        # Marcar como incerto evita reenviar automaticamente uma mensagem já aceita.
        c.execute("UPDATE email_outbox SET status='failed',error='delivery_uncertain',claim_until=NULL WHERE status='sending' AND claim_until<?",(utcnow(),))
        row=c.execute("SELECT * FROM email_outbox WHERE status IN ('queued','not_configured') ORDER BY id LIMIT 1").fetchone()
        if row is None:return False
        term=c.execute('SELECT * FROM terms WHERE id=?',(row['term'],)).fetchone()
        if term is None or term['status']!='pending' or not term['sign_due_at'] or term['sign_due_at']<utcnow():
            c.execute("UPDATE email_outbox SET status=?,error=NULL WHERE id=?",('expired' if term and term['status']=='pending' else 'cancelled',row['id']))
            return True
        subject,body,link=invitation_content(term,config['base'])
        claim=(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat(timespec='seconds')
        c.execute("UPDATE email_outbox SET status='sending',subject=?,body=?,link=?,claim_until=?,attempts=attempts+1,error=NULL WHERE id=?",(subject,body,link,claim,row['id']))
        row=dict(c.execute('SELECT * FROM email_outbox WHERE id=?',(row['id'],)).fetchone())
    try:
        transmit(row,config)
    except Exception:
        with db_factory() as c:c.execute("UPDATE email_outbox SET status='failed',error='send_failed',claim_until=NULL WHERE id=?",(row['id'],))
    else:
        with db_factory() as c:c.execute("UPDATE email_outbox SET status='sent',sent_at=?,error=NULL,claim_until=NULL WHERE id=?",(utcnow(),row['id']))
    return True

def start_worker(db_factory,demo):
    global _started
    if demo:return
    with _start_lock:
        if _started:return
        _started=True
    def run():
        while True:
            try:
                if process_one(db_factory,False):continue
            except Exception:
                import logging
                logging.error('Falha ao processar fila de notificações da E.D.N.A.')
            time.sleep(5)
    threading.Thread(target=run,name='edna-email-outbox',daemon=True).start()
