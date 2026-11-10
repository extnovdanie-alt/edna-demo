import base64,hashlib,hmac,io,json,os,re,secrets,sqlite3,ssl,threading,time
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from pathlib import Path
from xml.sax.saxutils import escape
import notifications,inventory,inventory_integration
from edna.errors import HTTPError,require


def authenticate(context, login, password):
    if context.DEMO:
        if login in ('ti.demo', 'colaborador.demo') and password == 'demonstracao':
            return {'id': login, 'name': 'Equipe de TI' if login == 'ti.demo' else 'Ana Souza', 'admin': login == 'ti.demo', 'email': login + '@example.com'}
        raise ValueError('Conta de demonstração inválida.')
    from ldap3 import Server, Connection, Tls, SUBTREE
    from ldap3.utils.conv import escape_filter_chars
    if not re.fullmatch('[A-Za-z0-9._-]{1,100}', login) or not password:
        raise ValueError('Use seu usuário de rede, sem domínio.')
    host, domain, base, group = (os.environ[k] for k in ('LDAP_HOST', 'LDAP_DOMAIN', 'LDAP_BASE_DN', 'LDAP_ADMIN_GROUP_DN'))
    tls = Tls(validate=ssl.CERT_REQUIRED, version=ssl.PROTOCOL_TLS_CLIENT, ca_certs_file=os.getenv('LDAP_CA_FILE') or None)
    server = Server(host, port=636, use_ssl=True, tls=tls, connect_timeout=8)
    with Connection(server, user=login + '@' + domain, password=password, auto_bind=True, receive_timeout=10, raise_exceptions=True) as conn:
        conn.search(base, '(&(objectClass=user)(sAMAccountName=' + escape_filter_chars(login) + '))', SUBTREE, attributes=['displayName', 'sAMAccountName', 'objectGUID', 'mail'])
        if len(conn.entries) != 1:
            raise ValueError('Usuário não encontrado no diretório.')
        entry = conn.entries[0]
        identity = str(entry.objectGUID.value)
        name = str(entry.displayName.value or login)
        try:
            email = notifications.valid_email(str(entry.mail.value or ''))
        except ValueError:
            email = None
        conn.search(group, '(member:1.2.840.113556.1.4.1941:=' + escape_filter_chars(entry.entry_dn) + ')', search_scope='BASE', attributes=['cn'])
        return {'id': identity, 'name': name, 'admin': bool(conn.entries), 'email': email}
