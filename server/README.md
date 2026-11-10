# E.D.N.A. — servidor MVC

Python 3.11 ou superior. A interface e a mascote são mantidas.

## Testar localmente

1. Criar e ativar um ambiente virtual Python.
2. Executar `python -m pip install -r requirements.txt`.
3. Executar `python iniciar_demo.py` e abrir http://127.0.0.1:8080/.
4. Selecionar TI ou colaborador. Contas `ti.demo` e `colaborador.demo`, senha `demonstracao`.

O inventário é carregado uma vez do catálogo real em data-seed/inventory.json. Edições no servidor ficam em SQLite, inclusive após reiniciar. A pasta data-demo/ é privada e não entra no Git. O servidor não grava de volta no Google Sheets.

## Produção interna

Configurar as variáveis de config.example.ps1, autenticação corporativa, HTTPS e DATA_DIR em armazenamento persistente privado. Usar `waitress-serve --host=127.0.0.1 --port=8080 app:application` atrás do proxy aprovado, com DEMO_MODE=0. O endereço de escuta/proxy deve seguir a implantação corporativa. Autenticação simulada não deve ser usada como proteção para uma implantação operacional.

O modo Google Sheets exige instalar requirements-google-sheets.txt e configurar uma identidade de leitura aprovada. Preencher GOOGLE_SHEETS_ID e Application Default Credentials somente no servidor; não publicar chaves. IMPORTANTE: disco efêmero de contêiner ou múltiplas réplicas com bancos SQLite diferentes não garantem persistência compartilhada. Configurar o volume/banco aprovado antes da produção.

Consulte MVC.md para estrutura e regras de edição. A demonstração em GitHub Pages salva somente no navegador de cada visitante; ela não executa este servidor Python.
