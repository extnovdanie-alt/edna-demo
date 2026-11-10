import base64,hashlib,hmac,io,json,os,re,secrets,sqlite3,ssl,threading,time
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from pathlib import Path
from xml.sax.saxutils import escape
import notifications,inventory,inventory_integration
from edna.errors import HTTPError,require


def register_login(context, user):
    with context.db() as c:
        c.execute('INSERT INTO users(id,name,email) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,email=excluded.email', (user['id'], user['name'], user.get('email')))
        for pending in c.execute("SELECT t.* FROM terms t JOIN assignments a ON a.id=t.assignment WHERE a.person=? AND t.status='pending' AND t.sign_due_at IS NULL", (user['id'],)).fetchall():
            c.execute('UPDATE terms SET sign_due_at=?,sign_days=5,recipient_email=? WHERE id=?', ((datetime.now(timezone.utc) + timedelta(days=5)).isoformat(timespec='seconds'), user.get('email'), pending['id']))
            if user.get('email'):
                notifications.enqueue(c, c.execute('SELECT * FROM terms WHERE id=?', (pending['id'],)).fetchone(), user['email'], context.DEMO)
        context.event(c, user['id'], 'login', 'demo' if context.DEMO else 'ldaps')

def profile(context,user_id):
    with context.db() as c:
        row=c.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
        return dict(row) if row else None
