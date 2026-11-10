"""Recepção autenticada de inventário normalizado; sem dependência da API do fornecedor."""
import hashlib,hmac,json,os,re
from collections import Counter
from datetime import datetime,timedelta,timezone
import inventory

class SyncError(Exception):
    def __init__(self,message,code=400):self.message,self.code=message,code
def require(condition,message,code=400):
    if not condition:raise SyncError(message,code)
def authorize(header):
    token=os.getenv('INVENTORY_SYNC_TOKEN','')
    require(len(token)>=32,'A integração ainda não foi configurada no servidor.',503)
    require(hmac.compare_digest(header.encode(),('Bearer '+token).encode()),'Credencial de integração inválida.',401)
def schema(c):
    c.executescript('''CREATE TABLE IF NOT EXISTS inventory_external_ids(source TEXT NOT NULL,site TEXT NOT NULL,external_id TEXT NOT NULL,asset INTEGER NOT NULL UNIQUE REFERENCES assets(id),PRIMARY KEY(source,site,external_id));
    CREATE TABLE IF NOT EXISTS inventory_sync_batches(batch_id TEXT PRIMARY KEY,digest TEXT NOT NULL,source TEXT NOT NULL,site TEXT NOT NULL,observed_at TEXT NOT NULL,result TEXT NOT NULL);''')
def field(value,name,limit=150,optional=False):
    require(isinstance(value,str),f'{name}: informe texto.')
    value=value.strip();require((optional or bool(value)) and len(value)<=limit,f'{name}: valor vazio ou muito longo.')
    return value
def ingest(db,payload,*,expected_source=None):
    source=field(payload.get('source'),'source',40)
    site=field(payload.get('site'),'site',40)
    require(source==(expected_source or os.getenv('INVENTORY_PROVIDER','n8n')),'Fonte de inventário não autorizada.',403)
    require(site==os.getenv('INVENTORY_SITE','BRSP26'),'Unidade de inventário não autorizada.',403)
    batch=field(payload.get('batch_id'),'batch_id',128)
    require(re.fullmatch(r'[A-Za-z0-9_.:-]+',batch),'batch_id inválido.')
    mode=payload.get('mode','upsert');require(mode in ('upsert','snapshot'),'mode deve ser upsert ou snapshot.')
    if mode=='snapshot':require(payload.get('complete') is True,'Uma carga completa exige complete=true e todas as páginas do inventário.')
    try:observed=datetime.fromisoformat(payload.get('observed_at','').replace('Z','+00:00'))
    except (ValueError,AttributeError,TypeError):raise SyncError('observed_at deve ser uma data ISO 8601 com fuso.')
    require(observed.tzinfo is not None,'observed_at precisa informar o fuso.')
    observed=observed.astimezone(timezone.utc)
    require(observed<=datetime.now(timezone.utc)+timedelta(minutes=5),'observed_at está no futuro.')
    items=payload.get('items');require(isinstance(items,list) and 1<=len(items)<=10000,'Envie de 1 a 10000 itens; cargas vazias não são aplicadas.')
    normalized=[];external_ids=set();serials=set()
    for item in items:
        require(isinstance(item,dict),'Item de inventário inválido.')
        eid=field(item.get('external_id'),'external_id');require(eid not in external_ids,'external_id repetido no lote.');external_ids.add(eid)
        category=item.get('category');require(isinstance(category,str) and category in inventory.ALLOWED,'Categoria não permitida.')
        serial=item.get('serial')
        if serial is not None:serial=field(serial,'serial',150,True) or None
        require(serial or category in ('mouse','teclado'),'Serial obrigatório para esta categoria.')
        if serial:require(serial.casefold() not in serials,'Serial repetido no lote.');serials.add(serial.casefold())
        status=item.get('status');require(status in ('available','in_use','maintenance','lost','retired','unknown'),'Status de inventário inválido.')
        normalized.append({'external_id':eid,'category':category,'serial':serial,'model':field(item.get('model'),'model'),'status':status,'location':field(item.get('location',''),'location',250,True)})
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    with inventory.LOCK:
        with db() as c:
            inventory.schema(c);schema(c);c.execute('BEGIN IMMEDIATE')
            previous=c.execute('SELECT * FROM inventory_sync_batches WHERE batch_id=?',(batch,)).fetchone()
            if previous:
                require(previous['digest']==digest,'batch_id já usado com outro conteúdo.',409)
                return {**json.loads(previous['result']),'already_processed':True}
            saved=c.execute('SELECT * FROM inventory_meta WHERE id=1').fetchone()
            old=json.loads(saved['report']) if saved else {}
            if old.get('source_kind')=='integration':
                require(observed>datetime.fromisoformat(old['observed_at']),'Lote anterior ou simultâneo à última sincronização.',409)
            if mode=='snapshot':c.execute('UPDATE inventory_records SET active=0')
            created=updated=0
            for item in normalized:
                mapping=c.execute('SELECT asset FROM inventory_external_ids WHERE source=? AND site=? AND external_id=?',(source,site,item['external_id'])).fetchone()
                asset=c.execute('SELECT * FROM assets WHERE id=?',(mapping['asset'],)).fetchone() if mapping else None
                if not asset and item['serial']:asset=c.execute('SELECT * FROM assets WHERE lower(serial)=lower(?)',(item['serial'],)).fetchone()
                if asset:
                    other=c.execute('SELECT * FROM inventory_external_ids WHERE asset=?',(asset['id'],)).fetchone()
                    require(not other or (other['source'],other['site'],other['external_id'])==(source,site,item['external_id']),'Serial vinculado a outro identificador externo.',409)
                    require(not asset['serial'] or asset['serial'].casefold()==(item['serial'] or '').casefold(),'O serial de um equipamento existente não pode ser trocado automaticamente.',409)
                    aid=asset['id'];updated+=1
                    c.execute('UPDATE assets SET model=?,category=?,serial=? WHERE id=?',(item['model'],item['category'],item['serial'],aid))
                else:
                    key=f'{source}:{site}:{item["external_id"]}'
                    aid=c.execute('INSERT INTO assets(tag,model,serial,category) VALUES (?,?,?,?)',('API-'+hashlib.sha256(key.encode()).hexdigest()[:24],item['model'],item['serial'],item['category'])).lastrowid;created+=1
                c.execute('INSERT OR IGNORE INTO inventory_external_ids(source,site,external_id,asset) VALUES (?,?,?,?)',(source,site,item['external_id'],aid))
                key=f'external:{source}:{site}:{item["external_id"]}'
                c.execute('INSERT INTO inventory_records(asset,source_key,source_sheet,source_row,source_status,location,state,active) VALUES (?,?,?,0,?,?,?,1) ON CONFLICT(asset) DO UPDATE SET source_key=excluded.source_key,source_sheet=excluded.source_sheet,source_row=0,source_status=excluded.source_status,location=excluded.location,state=excluded.state,active=1',(aid,key,'Integração '+source,item['status'],item['location'],'available' if item['status']=='available' else 'blocked'))
            rows=c.execute('SELECT a.category,i.state FROM inventory_records i JOIN assets a ON a.id=i.asset WHERE i.active=1').fetchall()
            now=datetime.now(timezone.utc).isoformat(timespec='seconds')
            report={'source':'Inventário via '+source,'source_kind':'integration','provider':source,'site':site,'sync_mode':mode,'batch_id':batch,'observed_at':observed.isoformat(),'synced_at':now,'connected':True,'error':None,'items':len(rows),'available':sum(r['state']=='available' for r in rows),'categories':dict(Counter(r['category'] for r in rows)),'issues':[] if mode=='snapshot' else old.get('issues',[]),'duplicates':0,'excluded_sheets':[],'sheets':[]}
            result={'ok':True,'batch_id':batch,'created':created,'updated':updated,'items':len(rows),'synced_at':now,'already_processed':False}
            c.execute('INSERT INTO inventory_meta(id,fingerprint,report) VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET fingerprint=excluded.fingerprint,report=excluded.report',('integration:'+digest,json.dumps(report,ensure_ascii=False)))
            c.execute('INSERT INTO inventory_sync_batches VALUES (?,?,?,?,?,?)',(batch,digest,source,site,observed.isoformat(),json.dumps(result)))
            c.execute('INSERT INTO events(at,actor,action,ref) VALUES (?,?,?,?)',(now,'integration:'+source,'inventory_synced',batch))
            return result
