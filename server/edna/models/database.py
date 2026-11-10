import base64,hashlib,hmac,io,json,os,re,secrets,sqlite3,ssl,threading,time
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from pathlib import Path
from xml.sax.saxutils import escape
import notifications,inventory,inventory_integration
from edna.errors import HTTPError,require
from edna.models import catalog


def db(context):
    context.DATA.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(context.DATA / 'portal.sqlite3', timeout=20)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def migrate_assets(context, c):
    columns = {r['name']: r for r in c.execute('PRAGMA table_info(assets)')}
    if 'category' in columns and (not columns['serial']['notnull']):
        return
    c.execute('PRAGMA foreign_keys=OFF')
    try:
        c.execute('BEGIN IMMEDIATE')
        c.execute("CREATE TABLE assets_category_upgrade(id INTEGER PRIMARY KEY,tag TEXT UNIQUE NOT NULL,model TEXT NOT NULL,serial TEXT UNIQUE,category TEXT NOT NULL DEFAULT 'outro')")
        for row in c.execute('SELECT * FROM assets').fetchall():
            category = row['category'] if 'category' in columns else 'notebook' if re.search('notebook|latitude|thinkpad|macbook|elitebook|probook', row['model'], re.I) else 'outro'
            c.execute('INSERT INTO assets_category_upgrade(id,tag,model,serial,category) VALUES (?,?,?,?,?)', (row['id'], row['tag'], row['model'], row['serial'] or None, category))
        c.execute('DROP TABLE assets')
        c.execute('ALTER TABLE assets_category_upgrade RENAME TO assets')
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('A migração do inventário encontrou referências inválidas.')
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.execute('PRAGMA foreign_keys=ON')

def init(context):
    with context.db() as c:
        c.executescript("\n        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL);\n        CREATE TABLE IF NOT EXISTS assets(id INTEGER PRIMARY KEY,tag TEXT UNIQUE NOT NULL,model TEXT NOT NULL,serial TEXT UNIQUE,category TEXT NOT NULL DEFAULT 'outro');\n        CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY,asset INTEGER NOT NULL REFERENCES assets(id),person TEXT NOT NULL REFERENCES users(id),kind TEXT NOT NULL,due TEXT,notes TEXT NOT NULL,status TEXT NOT NULL);\n        CREATE TABLE IF NOT EXISTS terms(id INTEGER PRIMARY KEY,assignment INTEGER NOT NULL REFERENCES assignments(id),kind TEXT NOT NULL,body TEXT NOT NULL,snapshot TEXT NOT NULL,status TEXT NOT NULL,created TEXT NOT NULL,accepted TEXT,signer TEXT,evidence TEXT,digest TEXT,pdf BLOB);\n        CREATE UNIQUE INDEX IF NOT EXISTS one_term_type ON terms(assignment,kind);\n        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,at TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,ref TEXT NOT NULL);\n        CREATE TABLE IF NOT EXISTS return_requests(id INTEGER PRIMARY KEY,assignment INTEGER NOT NULL REFERENCES assignments(id),person TEXT NOT NULL REFERENCES users(id),reason TEXT NOT NULL,created TEXT NOT NULL,status TEXT NOT NULL,closed_at TEXT,handled_at TEXT,handled_by TEXT,closed_by TEXT);\n        CREATE UNIQUE INDEX IF NOT EXISTS one_open_return_request ON return_requests(assignment) WHERE status IN ('open','processing');\n        CREATE TABLE IF NOT EXISTS assignment_history(id INTEGER PRIMARY KEY,assignment INTEGER NOT NULL REFERENCES assignments(id),at TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL);\n        CREATE TABLE IF NOT EXISTS email_outbox(id INTEGER PRIMARY KEY,term INTEGER UNIQUE NOT NULL REFERENCES terms(id),recipient TEXT NOT NULL,subject TEXT NOT NULL,body TEXT NOT NULL,link TEXT NOT NULL,status TEXT NOT NULL,created TEXT NOT NULL,sent_at TEXT,error TEXT,attempts INTEGER NOT NULL DEFAULT 0,claim_until TEXT,message_id TEXT NOT NULL);\n        DROP INDEX IF EXISTS one_open_assignment;\n        CREATE UNIQUE INDEX one_open_assignment ON assignments(asset) WHERE status NOT IN ('returned','detached');\n        ")
        context.migrate_assets(c)
        inventory.schema(c)
        catalog.schema(c)
        columns = {r['name'] for r in c.execute('PRAGMA table_info(assignments)')}
        for column in ('closed_at', 'closed_by', 'closure_reason'):
            if column not in columns:
                c.execute('ALTER TABLE assignments ADD COLUMN ' + column + ' TEXT')
        user_columns = {r['name'] for r in c.execute('PRAGMA table_info(users)')}
        if 'email' not in user_columns:
            c.execute('ALTER TABLE users ADD COLUMN email TEXT')
        term_columns = {r['name'] for r in c.execute('PRAGMA table_info(terms)')}
        for column, kind in (('sign_due_at', 'TEXT'), ('sign_days', 'INTEGER'), ('recipient_email', 'TEXT')):
            if column not in term_columns:
                c.execute('ALTER TABLE terms ADD COLUMN ' + column + ' ' + kind)
        if context.DEMO:
            c.execute('INSERT OR IGNORE INTO users(id,name) VALUES (?,?)', ('colaborador.demo', 'Ana Souza'))
            c.execute('INSERT OR IGNORE INTO users(id,name) VALUES (?,?)', ('ti.demo', 'Equipe de TI'))
            c.execute('INSERT OR IGNORE INTO assets(tag,model,serial,category) VALUES (?,?,?,?)', ('PAT-001', 'Dell Latitude 5440', 'DEMO-001', 'notebook'))
            c.execute('INSERT OR IGNORE INTO assets(tag,model,serial,category) VALUES (?,?,?,?)', ('PAT-002', 'Lenovo ThinkPad E14', 'DEMO-002', 'notebook'))

def event(context, c, user, action, ref):
    c.execute('INSERT INTO events(at,actor,action,ref) VALUES (?,?,?,?)', (context.now(), user, action, str(ref)))

def history(context, c, user, aid, action, detail):
    c.execute('INSERT INTO assignment_history(assignment,at,actor,action,detail) VALUES (?,?,?,?,?)', (aid, context.now(), user, action, detail))
