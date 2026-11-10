"""Private, read-only Google Sheets inventory adapter for the Python server."""
import hashlib,json,os,re,uuid
from datetime import datetime,timedelta,timezone
import inventory
import inventory_integration

SCOPE='https://www.googleapis.com/auth/spreadsheets.readonly'
API='https://sheets.googleapis.com/v4/spreadsheets/'

class SheetsError(Exception):pass

def sheet_category(title):
    title=inventory.norm(title)
    return title=='NOTEBOOKS COPA DO MUNDO' or any(title.startswith(p) for p in ('001 -','002 -','003 -','004 -','006 -','008 -'))

def authorized_session():
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        credentials,_=google.auth.default(scopes=[SCOPE])
        return AuthorizedSession(credentials,refresh_timeout=15)
    except Exception as error:
        raise SheetsError('Configure a credencial Google aprovada no servidor e instale requirements-google-sheets.txt.') from error

def read_inventory(spreadsheet_id,session=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{20,150}',spreadsheet_id):
        raise SheetsError('Configure GOOGLE_SHEETS_ID com o ID da planilha Google.')
    own=session is None
    session=session or authorized_session()
    def get(suffix='',**params):
        try:
            response=session.get(API+spreadsheet_id+suffix,params=params,timeout=(5,15),allow_redirects=False)
            if response.status_code in (401,403,404):raise SheetsError('O servidor não tem acesso à planilha. Confira a credencial, a API Google Sheets e a permissão de leitura.')
            if response.status_code==429:raise SheetsError('Limite de consultas ao Google atingido. Tente novamente mais tarde.')
            if response.status_code!=200:raise SheetsError('A API Google Sheets não respondeu com sucesso. A última base foi preservada.')
            if len(response.content)>8388608:raise SheetsError('Resposta maior que 8 MB; divida a fonte antes de sincronizar.')
            return response.json()
        except SheetsError:raise
        except Exception as error:raise SheetsError('Falha ao consultar Google Sheets. A última base foi preservada.') from error
    try:
        metadata=get(fields='spreadsheetId,sheets.properties.title')
        titles=[s['properties']['title'] for s in metadata.get('sheets',[]) if sheet_category(s['properties']['title'])]
        if not titles or len(titles)>20:raise SheetsError('Nenhuma aba compatível encontrada, ou mais de 20 abas de inventário.')
        # Whole columns avoid silently truncating a complete snapshot at a row limit.
        ranges=["'"+title.replace("'","''")+"'!A:AZ" for title in titles]
        values=get('/values:batchGet',ranges=ranges,valueRenderOption='FORMATTED_VALUE')
        returned=values.get('valueRanges',[])
        if len(returned)!=len(titles):raise SheetsError('Leitura incompleta das abas. Nenhuma alteração foi aplicada.')
        if sum(len(v.get('values',[])) for v in returned)>10001:raise SheetsError('Mais de 10000 linhas na fonte. Nenhuma alteração foi aplicada.')
        records,report=inventory.parse_rows([(title,v.get('values',[])) for title,v in zip(titles,returned)])
        if not records:raise SheetsError('Nenhum equipamento elegível encontrado. Nenhuma alteração foi aplicada.')
        if any(not r['serial'] and not r['external_id'] for r in records):
            raise SheetsError('Mouse ou teclado sem serial precisa de uma coluna ID estável para sincronizar sem duplicações.')
        return records,report
    finally:
        if own:session.close()

def current(db):
    spreadsheet_id=os.getenv('GOOGLE_SHEETS_ID','').strip()
    try:interval=max(30,min(3600,int(os.getenv('GOOGLE_SHEETS_REFRESH_SECONDS','60'))))
    except ValueError:interval=60
    with inventory.LOCK:
        with db() as c:
            inventory.schema(c)
            saved=c.execute('SELECT * FROM inventory_meta WHERE id=1').fetchone()
        previous=json.loads(saved['report']) if saved else {'connected':False,'items':0,'issues':[]}
        now=datetime.now(timezone.utc)
        try:checked=datetime.fromisoformat(previous.get('google_checked_at',''))
        except (ValueError,TypeError):checked=None
        if previous.get('google_spreadsheet_id')==spreadsheet_id and checked and timedelta(0)<=now-checked<timedelta(seconds=interval):return previous
        try:
            records,parsed=read_inventory(spreadsheet_id)
            items=[{'external_id':hashlib.sha256((('serial:'+r['serial'].casefold()) if r['serial'] else 'id:'+r['external_id']).encode()).hexdigest(),
                    'category':r['category'],'model':r['model'],'serial':r['serial'],
                    'status':'available' if r['state']=='available' else 'unknown','location':r['location']} for r in records]
            payload={'source':'google_sheets','site':os.getenv('INVENTORY_SITE','BRSP26'),'batch_id':'sheets-'+uuid.uuid4().hex,
                     'observed_at':now.isoformat(),'mode':'snapshot','complete':True,'items':items}
            inventory_integration.ingest(db,payload,expected_source='google_sheets')
            with db() as c:report=json.loads(c.execute('SELECT report FROM inventory_meta WHERE id=1').fetchone()['report'])
            report.update(source='Inventário via Google Sheets',issues=parsed['issues'],duplicates=parsed['duplicates'],sheets=parsed['sheets'],excluded_sheets=parsed['excluded_sheets'])
            report['error']=None
        except (SheetsError,inventory_integration.SyncError) as error:
            report=dict(previous)
            report['error']=str(error) if isinstance(error,SheetsError) else 'A atualização não foi aplicada por conflito de identidade ou validação. Confira os registros da origem.'
        report.update(google_spreadsheet_id=spreadsheet_id,google_checked_at=datetime.now(timezone.utc).isoformat(),refresh_seconds=interval)
        with db() as c:
            c.execute('INSERT INTO inventory_meta(id,fingerprint,report) VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET report=excluded.report',
                      (saved['fingerprint'] if saved else None,json.dumps(report,ensure_ascii=False)))
        return report
