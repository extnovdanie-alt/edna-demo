"""Atualiza o código da demonstração local sem perder as sessões abertas."""
import hashlib
import importlib.util
import json
import logging
import sys
import threading
from pathlib import Path


def load_source(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    # Compilar a fonte evita reutilizar um .pyc com a mesma data/mesmo tamanho.
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module


class ReloadingDemoApplication:
    def __init__(self,module):
        if not module.DEMO:raise ValueError('Atualização automática disponível somente na demonstração.')
        self.module=module
        self.root=Path(module.__file__).resolve().parent
        self.lock=threading.Lock()
        self.version=self.fingerprint()

    def fingerprint(self):
        paths=[self.root/name for name in ('app.py','notifications.py','inventory.py','inventory_integration.py','inventory_google_sheets.py')]
        paths+=sorted((self.root/'edna').rglob('*.py'))
        return tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.exists())

    def refresh(self):
        latest=self.fingerprint()
        if latest==self.version:return
        with self.lock:
            latest=self.fingerprint()
            if latest==self.version:return
            old=self.module
            saved={name:getattr(old,name) for name in ('SESSIONS','ATTEMPTS','LOCK')}
            previous_notifications=sys.modules.get('notifications')
            previous_inventory=sys.modules.get('inventory')
            previous_integration=sys.modules.get('inventory_integration')
            previous_sheets=sys.modules.get('inventory_google_sheets')
            previous_mvc={k:v for k,v in sys.modules.items() if k=='edna' or k.startswith('edna.')}
            for name in previous_mvc:sys.modules.pop(name,None)
            try:
                updated_notifications=load_source('notifications',self.root/'notifications.py')
                sys.modules['notifications']=updated_notifications
                if (self.root/'inventory.py').exists():sys.modules['inventory']=load_source('inventory',self.root/'inventory.py')
                if (self.root/'inventory_integration.py').exists():sys.modules['inventory_integration']=load_source('inventory_integration',self.root/'inventory_integration.py')
                if (self.root/'inventory_google_sheets.py').exists():sys.modules['inventory_google_sheets']=load_source('inventory_google_sheets',self.root/'inventory_google_sheets.py')
                updated=load_source(old.__name__,self.root/'app.py')
                if not updated.DEMO:raise ValueError('Não é permitido trocar a demonstração para produção por recarga.')
                for name,value in saved.items():setattr(updated,name,value)
            except Exception:
                for name in list(sys.modules):
                    if name=='edna' or name.startswith('edna.'):sys.modules.pop(name,None)
                sys.modules.update(previous_mvc)
                if previous_notifications is not None:sys.modules['notifications']=previous_notifications
                else:sys.modules.pop('notifications',None)
                if previous_inventory is not None:sys.modules['inventory']=previous_inventory
                else:sys.modules.pop('inventory',None)
                if previous_integration is not None:sys.modules['inventory_integration']=previous_integration
                else:sys.modules.pop('inventory_integration',None)
                if previous_sheets is not None:sys.modules['inventory_google_sheets']=previous_sheets
                else:sys.modules.pop('inventory_google_sheets',None)
                raise
            sys.modules[old.__name__]=updated
            self.module=updated
            self.version=latest
            print('E.D.N.A.: demonstração atualizada; sessões preservadas.',flush=True)

    def __call__(self,environ,start_response):
        try:self.refresh()
        except Exception:
            logging.exception('Não foi possível carregar a atualização da demonstração.')
            body=json.dumps({'error':'A atualização do serviço ainda não foi concluída. Aguarde e tente novamente.'}).encode()
            start_response('503 Service Unavailable',[('Content-Type','application/json; charset=utf-8'),('Cache-Control','no-store')])
            return [body]
        return self.module.application(environ,start_response)
