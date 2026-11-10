"""Inventário Excel como fonte; reservas e documentos permanecem transacionais no SQLite."""
import hashlib,io,json,re,threading,unicodedata
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

LOCK=threading.RLock()
ALLOWED={'mouse','teclado','notebook','ring_scanner','handheld','leitor_2d','impressora_zebra'}
def source_path(data):
    config=data/'inventory-source.json'
    if config.exists():return Path(json.loads(config.read_text(encoding='utf-8'))['source_file'])
    local=data/'inventario.xlsx'
    import os
    configured=os.getenv('INVENTORY_SEED_FILE',str(Path(__file__).parent/'data-seed/inventory.json'))
    seed=Path(configured) if configured else None
    return local if local.exists() or not seed or not seed.exists() else seed
def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(value or '')) if not unicodedata.combining(c)).strip().upper()
def text(value):
    if value is None:return ''
    if isinstance(value,float) and value.is_integer():return str(int(value))
    return str(value).strip()
def schema(c):
    c.executescript('''CREATE TABLE IF NOT EXISTS inventory_records(asset INTEGER UNIQUE NOT NULL REFERENCES assets(id),source_key TEXT UNIQUE NOT NULL,source_sheet TEXT NOT NULL,source_row INTEGER NOT NULL,source_status TEXT,location TEXT,state TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS inventory_meta(id INTEGER PRIMARY KEY CHECK(id=1),fingerprint TEXT,report TEXT NOT NULL);''')
def parse(content):
    from openpyxl import load_workbook
    book=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
    return parse_book(book)

def parse_rows(tabs):
    """Read Sheets API values through the same rules used for the Excel seed."""
    class Tab:
        def __init__(self,title,rows):self.title,self.rows=title,rows
        def iter_rows(self,values_only=True):return iter(self.rows)
    class Book(list):
        def close(self):pass
    return parse_book(Book(Tab(title,rows) for title,rows in tabs))

def parse_book(book):
    records={};issues=[];sheets=[];excluded=[];duplicates=0;read=0
    try:
        for sheet in book:
            title=norm(sheet.title)
            if title.startswith('001 -'):fixed='notebook'
            elif title=='NOTEBOOKS COPA DO MUNDO':fixed='notebook'
            elif title.startswith('002 -'):fixed='ring_scanner'
            elif title.startswith('003 -'):fixed='impressora_zebra'
            elif title.startswith('004 -'):fixed='leitor_2d'
            elif title.startswith('006 -'):fixed='handheld'
            elif title.startswith('008 -'):fixed=None
            else:excluded.append(sheet.title);continue
            iterator=iter(sheet.iter_rows(values_only=True));headers=[norm(v) for v in next(iterator,())]
            def value(row,*names):
                for name in names:
                    if name in headers:
                        index=headers.index(name)
                        if index<len(row):return row[index]
                return None
            count=0
            for number,row in enumerate(iterator,2):
                if not any(v is not None and str(v).strip() for v in row):continue
                read+=1
                kind=norm(value(row,'DISPOSITIVO','TIPO'))
                category=fixed or {'MOUSE':'mouse','TECLADO':'teclado'}.get(kind)
                if category=='notebook' and kind!='NOTEBOOK':continue
                if category not in ALLOWED:continue
                if category=='leitor_2d' and 'BASE' in kind and 'SCANNER' not in kind:continue
                brand=text(value(row,'MARCA'));model=text(value(row,'MODELO'))
                if category=='impressora_zebra' and norm(brand)!='ZEBRA':continue
                raw=value(row,'S/N','SERIAL','SERIAL LEITOR','SN');serial=text(raw)
                if norm(serial) in ('','N/A','NA','SEM SERIAL','SEM SERIE','-','0','NONE'):serial=None
                if isinstance(raw,(float,int)) and len(serial or '')>15:
                    issues.append({'sheet':sheet.title,'row':number,'reason':'Serial numérico com mais de 15 dígitos; conferir no Excel.'});continue
                if not serial and category not in ('mouse','teclado'):
                    issues.append({'sheet':sheet.title,'row':number,'reason':'Serial obrigatório ausente.'});continue
                if not model:
                    issues.append({'sheet':sheet.title,'row':number,'reason':'Modelo ausente.'});continue
                status=text(value(row,'STATUS'));available=norm(status) in ('EM ESTOQUE','ESTOQUE','ESTOQUE IS','BACKUP','DISPONIVEL')
                location=text(value(row,'LOCAL/SETOR','LOCAL','LOCALIDADE\nBRSP26','LOCALIZACAO'))
                key='serial:'+serial.casefold() if serial else 'row:'+sheet.title+':'+str(number)
                record={'key':key,'external_id':text(value(row,'ID','ID_EQUIPAMENTO')) or None,'serial':serial,'category':category,'model':(brand+' '+model).strip(),'sheet':sheet.title,'row':number,'status':status or 'Não informado','location':location,'state':'available' if available else 'blocked'}
                if key in records:
                    duplicates+=1;previous=records[key]
                    if previous['category']!=category or norm(previous['model'])!=norm(record['model']):
                        previous['state']='blocked';previous['status']='Duplicidade com dados divergentes'
                        issues.append({'sheet':sheet.title,'row':number,'reason':'Serial repetido com categoria/modelo divergente.'})
                    elif not available:
                        if previous['state']=='available':previous['status']='Status divergentes entre registros'
                        previous['state']='blocked'
                    continue
                records[key]=record;count+=1
            sheets.append({'name':sheet.title,'items':count})
    finally:book.close()
    report={'source':'Inventário FBM Cotia BRSP26','rows_read':read,'items':len(records),'available':sum(r['state']=='available' for r in records.values()),'categories':dict(Counter(r['category'] for r in records.values())),'issues':issues,'duplicates':duplicates,'sheets':sheets,'excluded_sheets':excluded}
    return list(records.values()),report

def sync(db,path):
    with LOCK:
        with db() as c:
            schema(c);saved=c.execute('SELECT * FROM inventory_meta WHERE id=1').fetchone()
        if not path.exists() and saved is None:return None
        try:
            content=path.read_bytes();fingerprint=hashlib.sha256(content).hexdigest()
            if saved and saved['fingerprint']==fingerprint:return json.loads(saved['report'])
            if path.suffix.lower()=='.json':
                from edna.models.seed import parse as parse_catalog
                records,report=parse_catalog(content)
            else:records,report=parse(content)
            if not records:raise ValueError('Nenhum equipamento elegível encontrado na planilha.')
            report.update(synced_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),connected=True,error=None)
            with db() as c:
                c.execute('BEGIN IMMEDIATE');c.execute('UPDATE inventory_records SET active=0')
                for r in records:
                    existing=c.execute('SELECT asset FROM inventory_records WHERE source_key=?',(r['key'],)).fetchone()
                    if not existing and r['serial']:existing=c.execute('SELECT id AS asset FROM assets WHERE lower(serial)=lower(?)',(r['serial'],)).fetchone()
                    if existing:
                        aid=existing['asset'];c.execute('UPDATE assets SET model=?,category=? WHERE id=?',(r['model'],r['category'],aid))
                    else:
                        aid=c.execute('INSERT INTO assets(tag,model,serial,category) VALUES (?,?,?,?)',('XLSX-'+hashlib.sha256(r['key'].encode()).hexdigest()[:24],r['model'],r['serial'],r['category'])).lastrowid
                    c.execute('INSERT INTO inventory_records(asset,source_key,source_sheet,source_row,source_status,location,state,active) VALUES (?,?,?,?,?,?,?,1) ON CONFLICT(asset) DO UPDATE SET source_sheet=excluded.source_sheet,source_row=excluded.source_row,source_status=excluded.source_status,location=excluded.location,state=excluded.state,active=1',(aid,r['key'],r['sheet'],r['row'],r['status'],r['location'],r['state']))
                c.execute('INSERT INTO inventory_meta(id,fingerprint,report) VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET fingerprint=excluded.fingerprint,report=excluded.report',(fingerprint,json.dumps(report,ensure_ascii=False)))
            return report
        except Exception:
            report=json.loads(saved['report']) if saved else {'connected':True,'items':0}
            report['error']='Não foi possível atualizar a planilha. Novos empréstimos estão bloqueados até a atualização.'
            return report

def current(db,data,explicit_path=None):
    """Excel is a bootstrap; successful integrations are never overwritten by it."""
    import os
    if os.getenv('INVENTORY_MODE','seed')=='google_sheets':
        import inventory_google_sheets
        return inventory_google_sheets.current(db)
    with db() as c:
        schema(c);saved=c.execute('SELECT report FROM inventory_meta WHERE id=1').fetchone()
    report=json.loads(saved['report']) if saved else None
    if report and (report.get('source_kind')=='integration' or os.getenv('INVENTORY_MODE','seed')!='excel'):
        report.setdefault('source_kind','seed')
        return report
    report=sync(db,Path(explicit_path) if explicit_path else source_path(data))
    if report:report.setdefault('source_kind','seed')
    return report

def available(c,asset,connected):
    record=c.execute('SELECT * FROM inventory_records WHERE asset=?',(asset['id'],)).fetchone()
    if record:return bool(record['active'] and record['state']=='available')
    return not (connected and str(asset['serial'] or '').startswith('DEMO-'))
