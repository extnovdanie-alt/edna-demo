"""WSGI composition root. MVC implementation lives in edna/."""
import os,threading
from pathlib import Path
from datetime import datetime,timezone
import notifications,inventory,inventory_integration
from edna.config import CATEGORIES,OPTIONAL_SERIAL,TEXT
from edna.context import RuntimeContext
from edna.errors import HTTPError,require
from edna.models import database,terms
from edna.services import authentication
from edna.views import pdf
from edna.views.responses import json_response
from edna.controllers import portal,wsgi
ROOT=Path(__file__).parent
from prepare_assets import ensure_assets
ensure_assets(ROOT)
DATA=Path(os.getenv('DATA_DIR',str(ROOT/'data')))
DEMO=os.getenv('DEMO_MODE')=='1'
SESSIONS,ATTEMPTS={},{}
LOCK=threading.RLock()
context=RuntimeContext(globals())
def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def db():return database.db(context)
def migrate_assets(c):return database.migrate_assets(context, c)
def init():return database.init(context)
def event(c, user, action, ref):return database.event(context, c, user, action, ref)
def history(c, user, aid, action, detail):return database.history(context, c, user, aid, action, detail)
def authenticate(login, password):return authentication.authenticate(context, login, password)
def parse_sign_days(value=5):return terms.parse_sign_days(context, value)
def make_term(c, aid, kind, notes, sign_days=5):return terms.make_term(context, c, aid, kind, notes, sign_days)
def pdf_bytes(term, evidence):return pdf.pdf_bytes(context, term, evidence)
def dispatch(env):return portal.dispatch(env,context)
def application(env,start_response):return wsgi.application(env,start_response,context)
init()
notifications.start_worker(db,DEMO)
if __name__=='__main__':
    if not DEMO:raise SystemExit('Produção: execute pelo Waitress conforme README.md.')
    from wsgiref.simple_server import make_server
    print('Demonstração local: http://127.0.0.1:8080',flush=True)
    make_server('127.0.0.1',8080,application).serve_forever()
