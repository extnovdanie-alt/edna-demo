"""Iniciador local de demonstracao; nao configura nem acessa o AD."""
import os
import sys
import threading
import webbrowser
import traceback
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    print('Iniciando E.D.N.A....', flush=True)
    try:
        import reportlab
    except ImportError:
        print('Falta a biblioteca para gerar PDFs. Execute no terminal:')
        print('"'+sys.executable+'" -m pip install -r "'+str(ROOT/'requirements.txt')+'"')
        return 1
    if '--check' in sys.argv:
        print('Iniciador pronto: Python e geracao de PDF disponiveis.')
        return 0
    os.environ['DEMO_MODE'] = '1'
    os.environ['DATA_DIR'] = str(ROOT/'data-demo')
    os.chdir(ROOT)
    import app
    from demo_server import ReloadingDemoApplication
    application=ReloadingDemoApplication(app)
    from wsgiref.simple_server import make_server
    if '--self-test' in sys.argv:
        import urllib.request
        server = make_server('127.0.0.1', 0, application)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = 'http://127.0.0.1:'+str(server.server_port)+'/api/session'
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(url, timeout=5) as response:
                state = json.load(response)
                assert response.status == 200 and state['demo'] is True
            print('TESTE OK: servico HTTP e API responderam corretamente.', flush=True)
        finally:
            server.shutdown()
            server.server_close()
        return 0
    try:
        server = make_server('127.0.0.1', 8080, application)
    except OSError:
        print('Nao foi possivel abrir a porta 8080. Verifique se o portal ja esta aberto:')
        print('http://127.0.0.1:8080')
        return 1
    print('E.D.N.A. - DEMONSTRACAO LOCAL', flush=True)
    print('Endereco: http://127.0.0.1:8080')
    print('Usuarios: ti.demo ou colaborador.demo | Senha: demonstracao')
    print('Mantenha esta janela aberta. Para encerrar, pressione Ctrl+C.')
    if '--no-browser' not in sys.argv:
        timer = threading.Timer(0.5, lambda: webbrowser.open('http://127.0.0.1:8080'))
        timer.daemon = True
        timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nPortal encerrado.')
    finally:
        server.server_close()
    return 0

class Tee:
    def __init__(self, console, log):
        self.console, self.log = console, log
    def write(self, text):
        self.console.write(text)
        self.log.write(text)
        self.flush()
    def flush(self):
        self.console.flush()
        self.log.flush()

if __name__ == '__main__':
    with (ROOT/'inicializacao.log').open('a', encoding='utf-8') as log:
        original_out, original_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = Tee(original_out, log), Tee(original_err, log)
        try:
            exit_code = main()
        except Exception:
            print('Falha ao iniciar. Detalhes em inicializacao.log:')
            traceback.print_exc()
            exit_code = 1
        finally:
            sys.stdout, sys.stderr = original_out, original_err
    sys.exit(exit_code)
