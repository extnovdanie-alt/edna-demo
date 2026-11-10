# Google Sheets no servidor

A consulta contínua ainda depende da configuração de uma identidade Google aprovada pela empresa. A carga pública é inicial, sem sincronização automática.

1. Habilitar a API Google Sheets no projeto aprovado e conceder à identidade do servidor somente leitura da planilha.
2. Instalar requirements-google-sheets.txt no mesmo ambiente Python.
3. Configurar Application Default Credentials; manter qualquer arquivo de credencial fora do Git e da pasta pública.
4. Preencher config.google-sheets.example.ps1 com o ID da planilha e ativar INVENTORY_MODE=google_sheets.
5. Reiniciar o serviço e conferir provider=google_sheets, source_kind=integration e error=null em /api/state com sessão TI.

A consulta ocorre sob demanda, com cache de 60 segundos. Falhas preservam a última base e bloqueiam novos empréstimos. As edições locais têm prioridade; não são gravadas de volta na planilha. O GitHub Pages não executa esse adaptador.
