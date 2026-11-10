# E.D.N.A. — Demonstração

Emitente de Declarações e Normas de Acordo.

Demonstração estática com 604 equipamentos reais publicados com autorização do usuário. O catálogo inclui modelo, categoria, serial e status. Os locais foram omitidos porque esse campo contém nomes de pessoas na origem. Usuários são exemplos; credenciais, dados de pessoas, IPs, MACs e a planilha original não são publicados.

## Como testar

Abra o site e escolha **Sou da TI** ou **Sou colaborador**. A senha de teste é `demonstracao`.

- TI: `ti.demo`
- Colaborador: `colaborador.demo`

No GitHub Pages, alterações ficam somente no navegador de cada visitante e permanecem após atualizar a página. Elas não são compartilhadas entre visitantes. Login, e-mails e aceites são simulados. A leitura contínua do Google Sheets depende da API em um servidor autorizado.

O servidor MVC em server/ salva alterações e operações no SQLite definido por DATA_DIR. Ele mantém histórico e detecta edições simultâneas. O GitHub Pages não executa Python; hospedar o servidor em ambiente interno/Fury autorizado para dados compartilhados. Não colocar o banco SQLite ou credenciais no Git.

## Executar o servidor MVC

No diretório server/, criar um ambiente Python e instalar requirements.txt. Para demonstração local: executar python iniciar_demo.py. Para produção: seguir README.md e configurar autenticação e armazenamento persistente. Na primeira execução, os recursos visuais são extraídos do index.html desta publicação. O catálogo em data-seed/inventory.json é usado somente como carga inicial; reiniciar o servidor não apaga as alterações do banco.

Consulte server/MVC.md para estrutura, persistência e limites de hospedagem. A imagem da mascote e a identidade visual foram fornecidas ou solicitadas para esta apresentação; não indicam um produto oficial.

O arquivo index.html inclui os recursos necessários para funcionar no GitHub Pages, sem instalação de dependências.
