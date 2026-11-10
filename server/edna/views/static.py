def serve(context, path, method):
    if path == '/' and method == 'GET':
        return (200, [('Content-Type', 'text/html; charset=utf-8')], (context.ROOT / 'dist/index.html').read_bytes())
    if path == '/demo.js' and method == 'GET':
        return (200, [('Content-Type', 'application/javascript; charset=utf-8')], (context.ROOT / 'dist/demo.js').read_bytes())
    if path in ('/app.js', '/style.css', '/meli.css', '/mascot.css', '/header-motion.js', '/header-motion.css', '/experience.css') and method == 'GET':
        return (200, [('Content-Type', 'application/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')], (context.ROOT / 'dist' / path[1:]).read_bytes())
    if path in ('/assets/edna-ti-frente.png', '/assets/edna-mode.webp', '/assets/edna-operacao-original.jpg') and method == 'GET':
        return (200, [('Content-Type', 'image/png')], (context.ROOT / 'dist/assets/edna-ti-frente.png').read_bytes())
    if path in ('/assets/mercado-livre-logo.png', '/assets/mercado-livre-logo@2x.png') and method == 'GET':
        return (200, [('Content-Type', 'image/png')], (context.ROOT / 'dist' / path.lstrip('/')).read_bytes())
    return None
