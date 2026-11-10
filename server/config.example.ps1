# Copie para um arquivo de configuração privado no servidor. Não coloque senhas aqui.
$env:DEMO_MODE = '0'
$env:LDAP_HOST = 'dc01.empresa.local'
$env:LDAP_DOMAIN = 'empresa.local'
$env:LDAP_BASE_DN = 'DC=empresa,DC=local'
$env:LDAP_ADMIN_GROUP_DN = 'CN=TI-Termos-Admins,OU=Grupos,DC=empresa,DC=local'
$env:LDAP_CA_FILE = 'C:\certificados\ca-corporativa.pem'
$env:DATA_DIR = 'C:\Dados\Termo'

# Inventário: planilha somente como carga inicial. Futuras cargas chegam pela API.
$env:INVENTORY_MODE = 'seed'
# Google Sheets ao vivo no servidor: ver GOOGLE-SHEETS.md e config.google-sheets.example.ps1.
$env:INVENTORY_PROVIDER = 'n8n'
$env:INVENTORY_SITE = 'BRSP26'
# Defina INVENTORY_SYNC_TOKEN no ambiente protegido do serviço (mínimo 32 caracteres).
# Não grave a credencial neste arquivo. Sem ela, o recebimento fica desativado.

# E-mail: mantenha disabled até preencher os dados reais do servidor.
# DEMO_MODE=1 sempre simula o envio, mesmo quando SMTP está configurado.
$env:MAIL_MODE = 'disabled' # alterar para smtp ao ativar produção
$env:SMTP_HOST = 'smtp-relay.gmail.com'
$env:SMTP_PORT = '587'
$env:SMTP_TLS = 'starttls' # ou ssl para TLS direto, normalmente na porta 465
$env:MAIL_FROM = 'edna@empresa.com'
$env:PORTAL_BASE_URL = 'https://edna.empresa.local'
# Opcional: CA corporativa para validar o certificado do SMTP.
# $env:SMTP_CA_FILE = 'C:\certificados\ca-corporativa.pem'
# Se o relay exigir autenticação, configure SMTP_USERNAME e SMTP_PASSWORD
# no ambiente protegido do serviço. Não grave senhas neste arquivo.
# Google Workspace: este exemplo usa o relay com IP público do servidor
# autorizado pelo administrador no Google Admin. Nesse modo, não defina
# SMTP_USERNAME/SMTP_PASSWORD. O remetente precisa ser aprovado no domínio.
