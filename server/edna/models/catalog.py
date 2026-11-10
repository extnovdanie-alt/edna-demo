"""Durable, audited local inventory edits, independent of source synchronization."""
import json
import inventory
from edna.errors import require

STATES={'available':'Disponível (ajuste TI)','maintenance':'Em manutenção (ajuste TI)','blocked':'Bloqueado (ajuste TI)','retired':'Baixado (ajuste TI)'}

def schema(c):
    c.executescript('''CREATE TABLE IF NOT EXISTS asset_overrides(asset INTEGER PRIMARY KEY REFERENCES assets(id),model TEXT NOT NULL,location TEXT NOT NULL,state TEXT NOT NULL,revision INTEGER NOT NULL,updated_at TEXT NOT NULL,updated_by TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS asset_changes(id INTEGER PRIMARY KEY,asset INTEGER NOT NULL REFERENCES assets(id),at TEXT NOT NULL,actor TEXT NOT NULL,before_json TEXT NOT NULL,after_json TEXT NOT NULL);''')

def available(c,asset,connected):
    row=c.execute('SELECT * FROM asset_overrides WHERE asset=?',(asset['id'],)).fetchone()
    if not row:return inventory.available(c,asset,connected)
    source=c.execute('SELECT * FROM inventory_records WHERE asset=?',(asset['id'],)).fetchone()
    if source and (not source['active'] or 'Duplicidade' in source['source_status']):return False
    return row['state']=='available'

def present(c,asset,connected=False,source_error=False):
    result=dict(asset);row=c.execute('SELECT * FROM asset_overrides WHERE asset=?',(asset['id'],)).fetchone()
    result.update(edit_revision=row['revision'] if row else 0,local_override=bool(row))
    if row:result.update(model=row['model'],location=row['location'],source_status=STATES[row['state']],local_state=row['state'])
    active=c.execute("SELECT 1 FROM assignments WHERE asset=? AND status NOT IN ('returned','detached')",(asset['id'],)).fetchone()
    result['available']=int(not active and not source_error and available(c,asset,connected))
    result['inventory_blocked']=not available(c,asset,connected)
    return result

def edit(context,env,data,user,inventory_report):
    require(type(data.get('id')) is int and type(data.get('revision')) is int,'Identificador e revisão inválidos.')
    require(not set(data)-{'id','revision','model','location','state'},'Serial e categoria não podem ser alterados por esta operação.')
    model=str(data.get('model','')).strip();location=str(data.get('location','')).strip();state=data.get('state')
    require(0<len(model)<=150 and len(location)<=250,'Informe modelo (até 150 caracteres) e local (até 250).')
    require(state in STATES,'Selecione um status válido.')
    with context.db() as c:
        c.execute('BEGIN IMMEDIATE')
        asset=c.execute('SELECT * FROM assets WHERE id=?',(data['id'],)).fetchone();require(asset is not None,'Equipamento não encontrado.',404)
        before=present(c,asset,bool(inventory_report))
        require(before['edit_revision']==data['revision'],'O equipamento foi editado em outra sessão. Atualize os dados antes de salvar.',409)
        source=c.execute('SELECT * FROM inventory_records WHERE asset=?',(asset['id'],)).fetchone()
        require(not(state=='available' and source and (not source['active'] or 'Duplicidade' in source['source_status'])),'Corrija o conflito ou a remoção na origem antes de liberar este equipamento.',409)
        updated=context.now();revision=before['edit_revision']+1
        c.execute('INSERT INTO asset_overrides VALUES (?,?,?,?,?,?,?) ON CONFLICT(asset) DO UPDATE SET model=excluded.model,location=excluded.location,state=excluded.state,revision=excluded.revision,updated_at=excluded.updated_at,updated_by=excluded.updated_by',(asset['id'],model,location,state,revision,updated,user['id']))
        after=present(c,asset,bool(inventory_report))
        c.execute('INSERT INTO asset_changes(asset,at,actor,before_json,after_json) VALUES (?,?,?,?,?)',(asset['id'],updated,user['id'],json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False)))
        context.event(c,user['id'],'asset_edited',asset['id'])
        return {'ok':True,'revision':revision}
