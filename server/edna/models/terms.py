import base64,hashlib,hmac,io,json,os,re,secrets,sqlite3,ssl,threading,time
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from pathlib import Path
from xml.sax.saxutils import escape
import notifications,inventory,inventory_integration
from edna.errors import HTTPError,require
from edna.models import catalog


def parse_sign_days(context, value=5):
    try:
        return notifications.signing_days(value)
    except ValueError as e:
        raise HTTPError(400, str(e))

def make_term(context, c, aid, kind, notes, sign_days=5):
    sign_days = context.parse_sign_days(sign_days)
    a = c.execute('SELECT a.*,s.tag,s.model,s.serial,s.category,u.name,u.email FROM assignments a JOIN assets s ON s.id=a.asset JOIN users u ON u.id=a.person WHERE a.id=?', (aid,)).fetchone()
    snapshot = dict(a)
    effective=catalog.present(c,c.execute('SELECT * FROM assets WHERE id=?',(a['asset'],)).fetchone())
    snapshot['model']=effective['model']
    snapshot['notes'] = notes
    body = context.TEXT[kind] + '\n\nModalidade: ' + a['kind'] + '. Prazo: ' + (a['due'] or 'sem prazo definido') + '.\nObservações e acessórios: ' + notes
    due = (datetime.now(timezone.utc) + timedelta(days=sign_days)).isoformat(timespec='seconds')
    cur = c.execute('INSERT INTO terms(assignment,kind,body,snapshot,status,created,sign_due_at,sign_days,recipient_email) VALUES (?,?,?,?,?,?,?,?,?)', (aid, kind, body, json.dumps(snapshot, ensure_ascii=False), 'pending', context.now(), due, sign_days, a['email']))
    if a['email']:
        notifications.enqueue(c, c.execute('SELECT * FROM terms WHERE id=?', (cur.lastrowid,)).fetchone(), a['email'], context.DEMO)
    return cur.lastrowid
