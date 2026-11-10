# Usar somente no servidor Python, depois de aprovar a identidade Google de leitura.
# Não executar no GitHub Pages. Não publicar credenciais ou a planilha no GitHub.
$env:INVENTORY_MODE = 'google_sheets'
$env:GOOGLE_SHEETS_ID = 'ID_DA_PLANILHA'
$env:GOOGLE_SHEETS_REFRESH_SECONDS = '60'
$env:INVENTORY_SITE = 'BRSP26'
# Configure Application Default Credentials da aplicação com autorização corporativa.
# Se a TI fornecer um arquivo, guarde-o fora da pasta pública e do repositório:
# $env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\Segredos\edna-google.json'
# Não há senha, token ou chave neste exemplo. Não torne a planilha pública.
