import base64,hashlib,hmac,io,json,os,re,secrets,sqlite3,ssl,threading,time
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from pathlib import Path
from xml.sax.saxutils import escape
import notifications,inventory,inventory_integration
from edna.errors import HTTPError,require
from edna.models import catalog


def read_state(context, env, data, user, inventory_report):
    with context.db() as c:
        terms = [dict(r) for r in c.execute('SELECT t.id,t.assignment,t.kind,t.body,t.snapshot,t.status,t.created,t.accepted,t.digest,t.sign_due_at,t.sign_days,t.recipient_email,a.person FROM terms t JOIN assignments a ON a.id=t.assignment' + ('' if user['admin'] else ' WHERE a.person=?') + ' ORDER BY t.id DESC', () if user['admin'] else (user['id'],))]
        for term in terms:
            term['overdue'] = bool(term['status'] == 'pending' and term['sign_due_at'] and (datetime.now(timezone.utc) > datetime.fromisoformat(term['sign_due_at'])))
        assignments = [dict(r) for r in c.execute('SELECT a.*,s.tag,s.model,s.serial,s.category,u.name FROM assignments a JOIN assets s ON s.id=a.asset JOIN users u ON u.id=a.person' + ('' if user['admin'] else ' WHERE a.person=?'), () if user['admin'] else (user['id'],))]
        assets = [dict(r) for r in c.execute("SELECT s.*,CASE WHEN EXISTS(SELECT 1 FROM assignments a WHERE a.asset=s.id AND a.status NOT IN ('returned','detached')) THEN 0 ELSE 1 END AS available FROM assets s")] if user['admin'] else []
        if user['admin']:
            for asset in assets:
                source = c.execute('SELECT * FROM inventory_records WHERE asset=?', (asset['id'],)).fetchone()
                asset['available'] = int(bool(asset['available']) and inventory.available(c, asset, bool(inventory_report)) and (not (inventory_report or {}).get('error')))
                asset['source_status'] = source['source_status'] if source else 'Cadastro local'
                asset['location'] = source['location'] if source else ''
                asset['source_sheet'] = source['source_sheet'] if source else None
                asset['source_row'] = source['source_row'] if source else None
                asset['inventory_blocked'] = bool(source and (not source['active'] or source['state'] != 'available'))
                asset.update(catalog.present(c,asset,bool(inventory_report),bool((inventory_report or {}).get('error'))))
            if inventory_report:
                assets = [a for a in assets if not str(a['serial'] or '').startswith('DEMO-')]
        people = [dict(r) for r in c.execute('SELECT * FROM users ORDER BY name')] if user['admin'] else []
        args = () if user['admin'] else (user['id'],)
        person_filter = '' if user['admin'] else ' WHERE a.person=?'
        requests = [dict(r) for r in c.execute('SELECT r.*,s.tag,s.serial,s.id AS asset,s.model,u.name,a.status AS assignment_status FROM return_requests r JOIN assignments a ON a.id=r.assignment JOIN assets s ON s.id=a.asset JOIN users u ON u.id=a.person' + person_filter + ' ORDER BY r.id DESC', args)]
        entries = [dict(r) for r in c.execute('SELECT h.*,s.tag,s.serial,s.id AS asset,s.model,u.name,COALESCE(actor.name,h.actor) AS actor_name FROM assignment_history h JOIN assignments a ON a.id=h.assignment JOIN assets s ON s.id=a.asset JOIN users u ON u.id=a.person LEFT JOIN users actor ON actor.id=h.actor' + person_filter + ' ORDER BY h.id DESC', args)]
        mail = [dict(r) for r in c.execute('SELECT q.*,a.person FROM email_outbox q JOIN terms t ON t.id=q.term JOIN assignments a ON a.id=t.assignment' + person_filter + ' ORDER BY q.id DESC', args)]
        return {'terms': terms, 'assignments': assignments, 'assets': assets, 'people': people, 'requests': requests, 'history': entries, 'mail': mail, 'inventory': inventory_report if user['admin'] else None, 'mail_mode': notifications.delivery_mode(context.DEMO)}

def pdf_document(context, env, data, user, inventory_report):
    with context.db() as c:
        match = re.fullmatch('/api/terms/(\\d+)/pdf', env['PATH_INFO'])
        term = c.execute('SELECT t.*,a.person FROM terms t JOIN assignments a ON a.id=t.assignment WHERE t.id=?', (match[1],)).fetchone()
        require(term is not None, 'Documento não encontrado.', 404)
        require(user['admin'] or term['person'] == user['id'], 'Acesso negado.', 403)
        require(term['status'] == 'accepted', 'O termo ainda não foi aceito.')
        return bytes(term['pdf'])

def request_return(context, env, data, user, inventory_report):
    with context.db() as c:
        c.execute('BEGIN IMMEDIATE')
        a = c.execute('SELECT * FROM assignments WHERE id=?', (data.get('id'),)).fetchone()
        require(a is not None and a['person'] == user['id'], 'Somente o responsável pode solicitar esta devolução.', 403)
        require(a['status'] in ('pending', 'active'), 'Este vínculo não permite uma nova solicitação.', 409)
        require(not c.execute("SELECT 1 FROM return_requests WHERE assignment=? AND status IN ('open','processing')", (a['id'],)).fetchone(), 'Já existe uma solicitação para este equipamento.', 409)
        reason = str(data.get('reason', '')).strip()
        require(0 < len(reason) <= 2000, 'Informe o motivo ou as observações da devolução.')
        cur = c.execute('INSERT INTO return_requests(assignment,person,reason,created,status) VALUES (?,?,?,?,?)', (a['id'], user['id'], reason, context.now(), 'open'))
        context.history(c, user['id'], a['id'], 'return_requested', reason)
        context.event(c, user['id'], 'return_requested', a['id'])
        return {'ok': True, 'id': cur.lastrowid}

def accept_term(context, env, data, user, inventory_report):
    with context.db() as c:
        c.execute('BEGIN IMMEDIATE')
        term = c.execute('SELECT t.*,a.person FROM terms t JOIN assignments a ON a.id=t.assignment WHERE t.id=?', (data.get('id'),)).fetchone()
        require(term is not None, 'Termo não encontrado.', 404)
        require(term['person'] == user['id'], 'Somente o responsável pode aceitar este termo.', 403)
        require(term['status'] == 'pending', 'Este termo foi cancelado pelo desvínculo.' if term['status'] == 'cancelled' else 'Este termo já foi aceito.', 409)
        require(term['sign_due_at'] and datetime.now(timezone.utc) <= datetime.fromisoformat(term['sign_due_at']), 'O prazo de assinatura deste termo venceu. Contate a TI.', 409)
        a = c.execute('SELECT * FROM assignments WHERE id=?', (term['assignment'],)).fetchone()
        require(a['status'] == ('return_pending' if term['kind'] == 'devolucao' else 'pending'), 'O vínculo foi encerrado ou alterado. Atualize a página.', 409)
        name = str(data.get('name', '')).strip()
        require(data.get('agree') is True and name.casefold() == user['name'].strip().casefold(), 'Confirme a concordância e digite seu nome como exibido.')
        evidence = {'name': name, 'user': user['id'], 'at': context.now(), 'ip': env.get('REMOTE_ADDR', ''), 'auth': 'Demonstração' if context.DEMO else 'AD via LDAPS', 'demo': context.DEMO, 'text_sha256': hashlib.sha256(term['body'].encode()).hexdigest(), 'agent': env.get('HTTP_USER_AGENT', '')[:500]}
        pdf = context.pdf_bytes(term, evidence)
        digest = hashlib.sha256(pdf).hexdigest()
        c.execute("UPDATE terms SET status='accepted',accepted=?,signer=?,evidence=?,digest=?,pdf=? WHERE id=?", (evidence['at'], name, json.dumps(evidence, ensure_ascii=False), digest, pdf, term['id']))
        status = 'active' if term['kind'] == 'responsabilidade' else 'returned'
        c.execute('UPDATE assignments SET status=? WHERE id=?', (status, term['assignment']))
        if status == 'returned':
            c.execute('UPDATE assignments SET closed_at=?,closed_by=? WHERE id=?', (evidence['at'], user['id'], term['assignment']))
            c.execute("UPDATE return_requests SET status='completed',closed_at=? WHERE assignment=? AND status IN ('open','processing')", (evidence['at'], term['assignment']))
        context.history(c, user['id'], term['assignment'], 'return_accepted' if status == 'returned' else 'responsibility_accepted', 'Termo #' + str(term['id']) + ' aceito por ' + name + '.')
        context.event(c, user['id'], 'accepted', term['id'])
        c.execute("UPDATE email_outbox SET status='cancelled' WHERE term=? AND status IN ('queued','not_configured','failed')", (term['id'],))
        return {'ok': True, 'id': term['id']}

def retry_email(context, env, data, user, inventory_report):
    with context.db() as c:
        c.execute('BEGIN IMMEDIATE')
        term = c.execute('SELECT * FROM terms WHERE id=?', (data.get('id'),)).fetchone()
        require(term is not None and term['status'] == 'pending' and term['sign_due_at'] and (datetime.now(timezone.utc) <= datetime.fromisoformat(term['sign_due_at'])), 'O termo não está disponível para uma nova solicitação.', 409)
        row = c.execute('SELECT * FROM email_outbox WHERE term=?', (term['id'],)).fetchone()
        require(row is not None, 'Solicitação não encontrada.', 404)
        require(row['status'] != 'sending', 'O envio já está em andamento.', 409)
        mode = notifications.delivery_mode(context.DEMO)
        c.execute('UPDATE email_outbox SET status=?,error=NULL,claim_until=NULL WHERE id=?', ('simulated' if context.DEMO else 'queued' if mode == 'smtp' else 'not_configured', row['id']))
        context.event(c, user['id'], 'signature_email_requeued', term['id'])
        return {'ok': True}

def create_asset(context, env, data, user, inventory_report):
    with context.db() as c:
        category = data.get('category', 'notebook')
        require(isinstance(category, str) and category in context.CATEGORIES, 'Selecione uma categoria válida de equipamento.')
        tag = str(data.get('tag') or 'EDNA-' + secrets.token_hex(12)).strip()
        model, serial = (str(data.get(k) or '').strip() for k in ('model', 'serial'))
        require(all((0 < len(v) <= 150 for v in (tag, model))), 'Preencha o modelo (até 150 caracteres).')
        require(len(serial) <= 150, 'O número de série deve ter até 150 caracteres.')
        require(serial or category in context.OPTIONAL_SERIAL, 'Informe o número de série para ' + context.CATEGORIES[category] + '.')
        c.execute('BEGIN IMMEDIATE')
        require(not c.execute('SELECT 1 FROM assets WHERE lower(tag)=lower(?) OR (? IS NOT NULL AND lower(serial)=lower(?))', (tag, serial or None, serial or None)).fetchone(), 'Equipamento ou número de série já cadastrado.', 409)
        cur = c.execute('INSERT INTO assets(tag,model,serial,category) VALUES (?,?,?,?)', (tag, model, serial or None, category))
        context.event(c, user['id'], 'asset_created', cur.lastrowid)
        return {'ok': True}

def assign_assets(context, env, data, user, inventory_report):
    with context.db() as c:
        days = context.parse_sign_days(data.get('sign_days', 5))
        require(not (inventory_report or {}).get('error'), 'Atualize a planilha antes de emprestar equipamentos.', 409)
        raw = data.get('items')
        if raw is None:
            asset_ids = data.get('assets', [data.get('asset')])
            require(isinstance(asset_ids, list), 'Seleção de equipamentos inválida.')
            raw = [{'asset': aid, 'person': data.get('person')} for aid in asset_ids]
        require(isinstance(raw, list) and 1 <= len(raw) <= 100, 'Selecione de 1 a 100 equipamentos.')
        require(all((isinstance(item, dict) and type(item.get('asset')) is int and isinstance(item.get('person'), str) for item in raw)), 'Seleção de equipamentos ou colaboradores inválida.')
        ids = [item['asset'] for item in raw]
        require(len(set(ids)) == len(ids), 'O mesmo equipamento não pode ser selecionado duas vezes.')
        quantity = data.get('quantity', len(ids))
        require(type(quantity) is int and quantity == len(ids), 'A quantidade deve corresponder aos equipamentos selecionados.')
        c.execute('BEGIN IMMEDIATE')
        kind = data.get('kind')
        due = data.get('due') or None
        require(kind in ('Fixa', 'Empréstimo'), 'Modalidade inválida.')
        if kind == 'Empréstimo':
            try:
                valid = datetime.strptime(due or '', '%Y-%m-%d').date() >= datetime.now().date()
            except ValueError:
                valid = False
            require(valid, 'Informe uma data de devolução válida, de hoje em diante.')
        else:
            due = None
        notes = str(data.get('notes', '')).strip()
        require(0 < len(notes) <= 2000, 'Informe acessórios e condições dos equipamentos.')
        for item in raw:
            require(c.execute('SELECT 1 FROM users WHERE id=?', (item['person'],)).fetchone(), 'Selecione um colaborador que já acessou o portal.')
            asset = c.execute('SELECT * FROM assets WHERE id=?', (item['asset'],)).fetchone()
            require(asset is not None, 'Equipamento não encontrado.')
            require(asset['category'] in context.CATEGORIES, 'Esta categoria não pode ser emprestada.')
            require(asset['serial'] or asset['category'] in context.OPTIONAL_SERIAL, 'Este equipamento não possui serial válido.')
            require(catalog.available(c, asset, bool(inventory_report)), 'Equipamento indisponível conforme a planilha de inventário.', 409)
            require(not c.execute("SELECT 1 FROM assignments WHERE asset=? AND status NOT IN ('returned','detached')", (item['asset'],)).fetchone(), 'Equipamento já atribuído. Atualize a seleção.', 409)
        terms = []
        for item in raw:
            cur = c.execute('INSERT INTO assignments(asset,person,kind,due,notes,status) VALUES (?,?,?,?,?,?)', (item['asset'], item['person'], kind, due, notes, 'pending'))
            terms.append(context.make_term(c, cur.lastrowid, 'responsabilidade', notes, days))
            context.history(c, user['id'], cur.lastrowid, 'assigned', kind + ' · ' + notes)
            context.event(c, user['id'], 'assigned', cur.lastrowid)
        return {'ok': True, 'id': terms[0], 'ids': terms, 'quantity': len(terms)}

def receive_return(context, env, data, user, inventory_report):
    with context.db() as c:
        days = context.parse_sign_days(data.get('sign_days', 5))
        c.execute('BEGIN IMMEDIATE')
        a = c.execute('SELECT * FROM assignments WHERE id=?', (data.get('id'),)).fetchone()
        require(a is not None and a['status'] == 'active', 'A atribuição precisa ter o aceite confirmado para iniciar a devolução.', 409)
        notes = str(data.get('notes', '')).strip()
        require(data.get('received') is True and 0 < len(notes) <= 2000, 'Confirme o recebimento físico e informe as condições e acessórios.')
        tid = context.make_term(c, a['id'], 'devolucao', notes, days)
        c.execute("UPDATE assignments SET status='return_pending' WHERE id=?", (a['id'],))
        c.execute("UPDATE return_requests SET status='processing',handled_at=?,handled_by=? WHERE assignment=? AND status='open'", (context.now(), user['id'], a['id']))
        context.history(c, user['id'], a['id'], 'return_received', notes)
        context.event(c, user['id'], 'return_received', a['id'])
        return {'ok': True, 'id': tid}

def unlink_asset(context, env, data, user, inventory_report):
    with context.db() as c:
        c.execute('BEGIN IMMEDIATE')
        a = c.execute('SELECT * FROM assignments WHERE id=?', (data.get('id'),)).fetchone()
        require(a is not None and a['status'] not in ('returned', 'detached'), 'Este vínculo já está encerrado ou não existe.', 409)
        reason = str(data.get('reason', '')).strip()
        require(data.get('confirm') is True and 0 < len(reason) <= 2000, 'Confirme o desvínculo e informe o motivo.')
        c.execute("UPDATE assignments SET status='detached',closed_at=?,closed_by=?,closure_reason=? WHERE id=?", (context.now(), user['id'], reason, a['id']))
        c.execute("UPDATE terms SET status='cancelled' WHERE assignment=? AND status='pending'", (a['id'],))
        c.execute("UPDATE email_outbox SET status='cancelled' WHERE term IN (SELECT id FROM terms WHERE assignment=?) AND status NOT IN ('sent','sending')", (a['id'],))
        c.execute("UPDATE return_requests SET status='cancelled',closed_at=?,closed_by=? WHERE assignment=? AND status IN ('open','processing')", (context.now(), user['id'], a['id']))
        context.history(c, user['id'], a['id'], 'unlinked', reason)
        context.event(c, user['id'], 'unlinked', a['id'])
        return {'ok': True, 'id': a['id']}
