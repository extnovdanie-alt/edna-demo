import base64,hashlib,hmac,io,json,os,re,secrets,sqlite3,ssl,threading,time
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from pathlib import Path
from xml.sax.saxutils import escape
import notifications,inventory,inventory_integration
from edna.errors import HTTPError,require
from edna.models import operations,identity,catalog
from edna.views import static
from edna.views.responses import json_response

def dispatch(env, context):
    path, method = (env.get('PATH_INFO', '/'), env['REQUEST_METHOD'])
    if path == '/api/integrations/inventory':
        require(method == 'POST', 'Método não permitido.', 405)
        try:
            inventory_integration.authorize(env.get('HTTP_AUTHORIZATION', ''))
            try:
                length = int(env.get('CONTENT_LENGTH') or 0)
            except ValueError:
                raise HTTPError(400, 'Tamanho de requisição inválido.')
            require(0 < length <= 4194304, 'Envie um JSON de até 4 MB.', 413)
            require(env.get('CONTENT_TYPE', '').split(';')[0].strip() == 'application/json', 'Use Content-Type application/json.', 400)
            try:
                payload = json.loads(env['wsgi.input'].read(length))
            except Exception:
                raise HTTPError(400, 'JSON inválido.')
            require(isinstance(payload, dict), 'Envie um objeto JSON.')
            return json_response(inventory_integration.ingest(context.db, payload))
        except inventory_integration.SyncError as error:
            raise HTTPError(error.code, error.message)
    cookies = SimpleCookie()
    try:
        cookies.load(env.get('HTTP_COOKIE', ''))
    except Exception:
        pass
    sid = cookies.get('session')
    with context.LOCK:
        sess = context.SESSIONS.get(sid.value if sid else '')
        if sess and sess['expires'] < time.time():
            context.SESSIONS.pop(sid.value, None)
            sess = None
    data = {}
    if method == 'POST':
        length = int(env.get('CONTENT_LENGTH') or 0)
        require(0 < length <= 16384, 'Requisição inválida.')
        try:
            data = json.loads(env['wsgi.input'].read(length))
        except Exception:
            raise HTTPError(400, 'JSON inválido.')
        require(isinstance(data, dict), 'Requisição inválida.')
    static_response = static.serve(context, path, method)
    if static_response is not None:
        return static_response
    if path == '/api/login' and method == 'POST':
        ip = (env.get('REMOTE_ADDR', ''), str(data.get('login', '')).casefold()[:100])
        with context.LOCK:
            context.ATTEMPTS[ip] = [t for t in context.ATTEMPTS.get(ip, []) if t > time.time() - 900]
            require(len(context.ATTEMPTS[ip]) < 8, 'Muitas tentativas. Aguarde 15 minutos.', 429)
            context.ATTEMPTS[ip].append(time.time())
        try:
            user = context.authenticate(str(data.get('login', '')), str(data.get('password', '')))
        except Exception:
            raise HTTPError(401, 'Não foi possível autenticar. Verifique sua conta ou contate a TI.')
        with context.LOCK:
            context.ATTEMPTS.pop(ip, None)
        identity.register_login(context, user)
        token = secrets.token_urlsafe(32)
        with context.LOCK:
            for key in list(context.SESSIONS):
                if context.SESSIONS[key]['expires'] < time.time():
                    del context.SESSIONS[key]
            if sid:
                context.SESSIONS.pop(sid.value, None)
            context.SESSIONS[token] = {'user': user, 'csrf': secrets.token_urlsafe(32), 'expires': time.time() + 28800}
        cookie = 'session=' + token + '; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800' + ('' if context.DEMO else '; Secure')
        return json_response({'ok': True}, headers=[('Set-Cookie', cookie)])
    if path == '/api/session' and method == 'GET':
        current = None
        if sess:
            profile = identity.profile(context, sess['user']['id'])
            current = {**sess['user'], 'email': profile['email'] if profile else None}
        return json_response({'user': current, 'csrf': sess['csrf'] if sess else None, 'demo': context.DEMO, 'capabilities': {'email_profile': False, 'directory_email': True, 'serial_identity': True, 'signature_email': True, 'api_version': 3}})
    require(sess is not None, 'Entre para continuar.', 401)
    user = sess['user']
    if method == 'POST':
        require(hmac.compare_digest(env.get('HTTP_X_CSRF_TOKEN', ''), sess['csrf']), 'Sessão inválida. Atualize a página.', 403)
    if path == '/api/logout' and method == 'POST':
        with context.LOCK:
            context.SESSIONS.pop(sid.value, None)
        return json_response({'ok': True}, headers=[('Set-Cookie', 'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')])
    inventory_report = inventory.current(context.db, context.DATA, os.getenv('INVENTORY_XLSX')) if path in ('/api/state', '/api/assign') else None
    if path == '/api/profile':
        raise HTTPError(404, 'O cadastro manual de e-mail foi removido.')
    if path == '/api/state' and method == 'GET':
        return json_response(operations.read_state(context, env, data, user, inventory_report))
    if re.fullmatch('/api/terms/(\\d+)/pdf', path) and method == 'GET':
        return (200, [('Content-Type', 'application/pdf'), ('Content-Disposition', 'attachment; filename="termo-' + path.split('/')[3] + '.pdf"')], operations.pdf_document(context, env, data, user, inventory_report))
    if method == 'POST' and path in ('/api/request-return', '/api/accept'):
        action = operations.request_return if path == '/api/request-return' else operations.accept_term
        return json_response(action(context, env, data, user, inventory_report))
    require(user['admin'], 'Acesso reservado à TI.', 403)
    actions = {'/api/retry-email': operations.retry_email, '/api/assets': operations.create_asset, '/api/assign': operations.assign_assets, '/api/return': operations.receive_return, '/api/unlink': operations.unlink_asset, '/api/edit-asset': catalog.edit}
    if method == 'POST' and path in actions:
        return json_response(actions[path](context, env, data, user, inventory_report))
    raise HTTPError(404, 'Página não encontrada.')
