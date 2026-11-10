"""Restore the already-published visual assets when cloning the GitHub source."""
import base64,json,re
from pathlib import Path

def ensure_assets(root):
    required=('edna-ti-frente.png','mercado-livre-logo@2x.png')
    dest=root/'dist/assets'
    if all((dest/name).exists() for name in required):return
    bundle=root.parent/'index.html'
    if not bundle.exists():raise RuntimeError('Recursos visuais ausentes: mantenha server/ junto do index.html do repositório.')
    match=re.search(r'const EDNA_ASSETS=(\{.*?\});document\.querySelectorAll',bundle.read_text(encoding='utf-8'),re.S)
    if not match:raise RuntimeError('Mapa de imagens não encontrado no index.html.')
    assets=json.loads(match.group(1));dest.mkdir(parents=True,exist_ok=True)
    for name in required:
        value=assets[name];assert value.startswith('data:image/png;base64,')
        raw=base64.b64decode(value.split(',',1)[1],validate=True);assert raw.startswith(b'\x89PNG\r\n\x1a\n')
        (dest/name).write_bytes(raw)
    (dest/'mercado-livre-logo.png').write_bytes((dest/'mercado-livre-logo@2x.png').read_bytes())
