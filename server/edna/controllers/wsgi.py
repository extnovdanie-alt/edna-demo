import base64,hashlib,hmac,io,json,os,re,secrets,sqlite3,ssl,threading,time
from datetime import datetime,timedelta,timezone
from http.cookies import SimpleCookie
from pathlib import Path
from xml.sax.saxutils import escape
import notifications,inventory,inventory_integration
from edna.errors import HTTPError,require
from edna.controllers.portal import dispatch
from edna.views.responses import json_response

def application(env, start_response, context):
    try:
        code, headers, body = dispatch(env, context)
    except HTTPError as e:
        code = e.code
        _, headers, body = json_response({'error': e.message})
    except sqlite3.IntegrityError:
        code = 409
        _, headers, body = json_response({'error': 'Registro duplicado ou operação conflitante. Atualize a página.'})
    except Exception:
        import logging
        logging.exception('Falha ao processar operação')
        code = 500
        _, headers, body = json_response({'error': 'Não foi possível concluir a operação. Contate a TI.'})
    headers += [('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'), ('X-Frame-Options', 'DENY'), ('Referrer-Policy', 'no-referrer'), ('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")]
    start_response(str(code) + ' ' + {200: 'OK', 400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found', 405: 'Method Not Allowed', 409: 'Conflict', 413: 'Payload Too Large', 429: 'Too Many Requests', 500: 'Internal Server Error', 503: 'Service Unavailable'}.get(code, 'Error'), headers)
    return [body]
