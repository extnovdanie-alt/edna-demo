# Organização MVC e persistência

`app.py` é o ponto de composição WSGI e mantém as funções de entrada compatíveis com as versões anteriores.

- `edna/controllers/`: rotas, sessão, CSRF, autorização TI/colaborador e tratamento HTTP.
- `edna/models/`: SQLite, catálogo, ajustes locais, termos e transações de empréstimo/devolução.
- `edna/views/`: respostas JSON, arquivos estáticos e apresentação dos PDFs. A interface permanece em `dist/`.
- `edna/services/`: autenticação corporativa ou simulada.
- `inventory*.py`: adaptadores de planilha, Google Sheets e recebimento de integração.

## Onde os dados ficam

O servidor salva o banco `portal.sqlite3` em `DATA_DIR`. Na demonstração local, iniciar_demo.py usa data-demo/. Esse diretório deve estar em disco/volume persistente, fora do Git e da pasta pública. No Fury, configurar armazenamento persistente aprovado; SQLite em disco efêmero de contêiner não garante retenção após reimplantar e não serve para múltiplas réplicas independentes.

O catálogo público em `data-seed/inventory.json` contém somente equipamentos. Ele é carregado na ausência de uma base importada e não substitui a base a cada reinício. Não contém usuários, documentos, IPs, MACs ou a planilha original.

## Editar e salvar

A TI pode editar modelo, local e situação na aba Inventário. Serial e categoria permanecem estáveis. O endpoint POST /api/edit-asset exige sessão TI, CSRF e a revisão lida. Uma edição concorrente retorna 409, em vez de sobrescrever silenciosamente.

Os ajustes são salvos em asset_overrides, com auditoria em asset_changes. Eles têm prioridade na apresentação e na disponibilidade do inventário. A sincronização da planilha atualiza a fonte sem apagar esses ajustes; não há gravação de volta no Google Sheets. Equipamento removido da fonte ou com conflito de identidade não pode ser liberado por um ajuste local. Empréstimos abertos continuam reservando o item, e PDFs já emitidos permanecem imutáveis.

## GitHub Pages e Grid

O GitHub Pages executa a demonstração estática: as edições ficam no navegador de cada visitante. O servidor MVC executa as operações compartilhadas e exige implantação separada. Commit no Git não salva movimentações de usuários.

O Grid pode servir a interface HTML/CSS/JavaScript e datasets JSON. Isso não executa automaticamente o backend Python, LDAPS, fila SMTP ou as transações SQLite. A migração de arquivos para Grid preserva a organização MVC, mas não transforma o documento em um servidor Python.

O acesso Google do conector do chat não é a credencial da aplicação. A sincronização automática precisa da identidade aprovada e das variáveis de GOOGLE-SHEETS.md no servidor. Configuração não preenchida permanece desativada.
