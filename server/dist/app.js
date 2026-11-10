'use strict';
let session,state,tab='assignments',query='',filter='open',categoryFilter='all',toastTimer,linkOpened=false,menuCollapsed=false;
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const localSimulation=location.protocol==='file:'||new URLSearchParams(location.search).get('demo')==='1';
const browserDemo=localSimulation?TermoDemo.create():null;
const pdfUrls=new Map();
const labels={pending:'Aguardando aceite',active:'Em uso',return_pending:'Aguardando aceite da devolução',returned:'Devolvido',accepted:'Aceito',detached:'Desvinculado pela TI',cancelled:'Cancelado',open:'Aguardando TI',processing:'Recebido pela TI',completed:'Concluída'};
const mailLabels={simulated:'Envio simulado',queued:'Na fila de envio',not_configured:'Configuração de e-mail pendente',sending:'Enviando',sent:'Enviado ao servidor de e-mail',failed:'Falha no envio',expired:'Prazo vencido',cancelled:'Solicitação encerrada'};
const isExpired=t=>t.status==='pending'&&(t.overdue||!!t.sign_due_at&&new Date()>new Date(t.sign_due_at));
const eventLabels={assigned:'Equipamento atribuído',responsibility_accepted:'Termo de responsabilidade aceito',return_requested:'Devolução solicitada',return_received:'Equipamento recebido pela TI',return_accepted:'Termo de devolução aceito',unlinked:'Equipamento desvinculado pela TI'};
const categories={
 mouse:{label:'Mouse',icon:'mouse',serial:false,example:'Ex.: Logitech M170'},
 teclado:{label:'Teclado',icon:'keyboard',serial:false,example:'Ex.: Logitech K120'},
 notebook:{label:'Notebook',icon:'laptop',serial:true,example:'Ex.: Dell Latitude 5440'},
 ring_scanner:{label:'Ring scanner',icon:'ring',serial:true,example:'Ex.: Zebra RS5100'},
 handheld:{label:'Handheld',icon:'handheld',serial:true,example:'Ex.: Honeywell CT45'},
 leitor_2d:{label:'Leitor 2D',icon:'scanner',serial:true,example:'Ex.: Zebra DS4308'},
 impressora_zebra:{label:'Impressora Zebra',icon:'printer',serial:true,example:'Ex.: Zebra ZT411'}
};
const categoryInfo=value=>categories[value]||{label:'Equipamento',icon:'laptop',serial:true};
const assetIdentity=a=>a.serial?'Serial: '+a.serial:'Sem serial · item #'+(a.asset||a.id);
const categoryOptions=selected=>Object.entries(categories).map(([value,c])=>`<option value="${value}" ${value===selected?'selected':''}>${c.label}</option>`).join('');
const paths={
 dashboard:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
 printer:'M6 8V3h12v5 M6 17H3V9h18v8h-3 M6 14h12v7H6z M17 11h.01',
 laptop:'M5 4h14v11H5z M3 19h18l-2-4H5z',
 mouse:'M12 3a6 6 0 0 0-6 6v6a6 6 0 0 0 12 0V9a6 6 0 0 0-6-6z M12 3v7 M6 10h12',
 keyboard:'M3 6h18v12H3z M6 9h1 M10 9h1 M14 9h1 M18 9h.01 M6 12h1 M10 12h1 M14 12h1 M18 12h.01 M8 15h8',
 ring:'M6 4h12v9H6z M9 7v3 M12 7v3 M15 7v3 M8 13v4a4 4 0 0 0 8 0v-4',
 handheld:'M7 2h10a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z M9 5h6v8H9z M9 16h.01 M12 16h.01 M15 16h.01 M10 19h4',
 scanner:'M5 3h13l2 9H7z M8 12l1 9h5l1-9 M9 6v3 M12 6v3 M15 6v3 M3 6H1 M3 9H1',
 document:'M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6',
 return:'M9 5 4 10l5 5 M4 10h11a5 5 0 0 1 0 10h-3',
 history:'M3 11a9 9 0 1 1 2 7 M3 5v6h6 M12 7v5l3 2',
 bell:'M18 8a6 6 0 0 0-12 0c0 8-3 8-3 9h18c0-1-3-1-3-9 M10 21h4',
 plus:'M12 5v14 M5 12h14',search:'M21 21l-6-6 M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0',
 refresh:'M20 10a8 8 0 0 0-14-5L3 8 M3 3v5h5 M4 14a8 8 0 0 0 14 5l3-3 M21 21v-5h-5',
 arrow:'M5 12h14 M14 7l5 5-5 5',close:'M6 6l12 12 M18 6 6 18',
 shield:'M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z M8 12l3 3 5-6',
 info:'M12 10v7 M12 7h.01 M22 12A10 10 0 1 1 2 12a10 10 0 0 1 20 0',
 download:'M12 3v12 M7 10l5 5 5-5 M4 17v4h16v-4',unlink:'M8 8l-2 2a4 4 0 0 0 6 6l2-2 M16 16l2-2a4 4 0 0 0-6-6l-2 2 M3 3l18 18',
 check:'M5 12l4 4L19 6',user:'M20 21a8 8 0 0 0-16 0 M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0'
};
const icon=name=>`<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.document}"/></svg>`;
const badge=status=>`<span class="badge ${esc(status)}">${esc(labels[status]||status)}</span>`;
const initials=name=>String(name||'').split(' ').slice(0,2).map(p=>p[0]).join('').toUpperCase();
const isClosed=a=>['returned','detached'].includes(a.status);
const date=value=>value?new Date(value.length===10?value+'T12:00:00':value).toLocaleDateString('pt-BR'):'Sem prazo';
const datetime=value=>value?new Date(value).toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}):'—';
const pendingRequests=()=>state.requests.filter(r=>['open','processing'].includes(r.status));
const requestFor=id=>pendingRequests().find(r=>r.assignment===id);
function toast(message){clearTimeout(toastTimer);$('#toast').textContent=message;$('#toast').hidden=false;toastTimer=setTimeout(()=>$('#toast').hidden=true,6500)}
async function api(path,data){
  if(browserDemo)return browserDemo.request(path,data);
  let response;
  try{response=await fetch('/api/'+path,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json','X-CSRF-Token':session?.csrf||''}:{},body:data?JSON.stringify(data):undefined})}
  catch(_){throw Error('Não foi possível conectar ao portal. Verifique se o serviço está em execução.')}
  const result=await response.json();
  if(!response.ok)throw Error(result.error||'Não foi possível concluir esta operação.');
  return result;
}
function pdfHref(term){
  if(!browserDemo)return '/api/terms/'+term.id+'/pdf';
  if(!pdfUrls.has(term.id)){
    const bytes=Uint8Array.from(atob(term.pdfData),c=>c.charCodeAt(0));
    pdfUrls.set(term.id,URL.createObjectURL(new Blob([bytes],{type:'application/pdf'})));
  }
  return pdfUrls.get(term.id);
}
function pdfLink(term,label='PDF'){return `<a href="${esc(pdfHref(term))}" download="termo-${term.id}.pdf" target="_blank" rel="noopener">${icon('download')}${label}</a>`}
async function loadState(){state=await api('state');state.requests ||= [];state.history ||= [];state.mail ||= []}
async function boot(){
  try{
    session=await api('session');
    if(!browserDemo&&!session.capabilities?.serial_identity){
      $('#sidebar').hidden=true;
      $('#app').innerHTML=`<section class="profile-card"><div class="login-kicker">Atualização do serviço</div><h1>A E.D.N.A. precisa ser reiniciada.</h1><p>A tela já foi atualizada, mas o serviço aberto ainda está em uma versão anterior. As novas funções estarão disponíveis depois de reiniciar o serviço.</p><ol class="subtle"><li>Feche a janela do iniciador da E.D.N.A.</li><li>Abra novamente <strong>INICIAR-DEMO.cmd</strong>.</li><li>Atualize esta página e entre com sua conta de teste.</li></ol><p class="subtle">Seus registros permanecem salvos.</p></section>`;
      return;
    }
    if(!session.user)return login();
    await loadState();render();
    const target=Number(new URLSearchParams(location.search).get('termo'));
    if(!linkOpened&&target){linkOpened=true;if(state.terms.some(t=>t.id===target)){navigate('terms');term(target)}else toast('Este termo não está disponível para sua conta.');}
  }
  catch(error){$('#app').innerHTML=`<div class="panel empty">${icon('info')}<strong>Não foi possível abrir o portal</strong><p>${esc(error.message)}</p></div>`}
}
function deadlineField(){return '<label for="signDays">Prazo para assinatura</label><select id="signDays" name="sign_days">'+[1,2,3,4,5].map(n=>`<option value="${n}" ${n===5?'selected':''}>${n} ${n===1?'dia corrido':'dias corridos'}</option>`).join('')+'</select><p class="subtle">Quando disponível no diretório corporativo, o e-mail será usado para a solicitação. O termo também fica no portal. Prazo máximo: 5 dias corridos.</p>'}
function mailFor(id){return state.mail.find(m=>m.term===id)}
function mailBadge(status){return `<span class="mail-status ${esc(status)}">${esc(mailLabels[status]||status)}</span>`}
function invitationPreview(id){
  const t=state.terms.find(t=>t.id===id),m=mailFor(id);if(!m)return toast('Não há e-mail corporativo disponível para este termo. A assinatura pode ser feita pelo portal.');
  const actionable=session.user.admin&&t.status==='pending'&&!isExpired(t);
  let link=m.link;
  if(session.local){const url=new URL(location.href||'file:///index.html');url.searchParams.set('termo',id);link=url.href}
  const canLink=link.startsWith('https://')||session.local&&link.startsWith('file:');
  modal('Solicitação de assinatura',`<p class="dialog-intro"><strong>Para:</strong> ${esc(m.recipient)}<br><strong>Assinar até:</strong> ${datetime(t.sign_due_at)}</p>${mailBadge(m.status)}${m.status==='simulated'?'<div class="callout">Esta é uma prévia do envio simulado. Nenhum e-mail foi enviado.</div>':m.status==='not_configured'?'<div class="callout warning">O envio real aguarda a configuração do servidor de e-mail corporativo.</div>':m.status==='failed'?'<div class="callout danger">O envio não foi confirmado. A TI pode tentar novamente enquanto o prazo estiver aberto.</div>':''}<h3 class="email-subject">${esc(m.subject)}</h3><pre class="email-body">${esc(m.body)}</pre>${canLink?`<a href="${esc(link)}">Abrir termo no portal →</a>`:''}<p class="subtle">Reenviar mantém o prazo original. O link exige acesso à conta do responsável.</p>`,actionable?'Reenviar solicitação':null);
  if(actionable)save('retry-email',()=>({id}),session.demo?'Novo envio simulado registrado.':'Solicitação atualizada. Consulte o status do envio.');
}
function applyMenuState(){document.body.classList.toggle('menu-collapsed',menuCollapsed);const button=$('#toggleMenu');button.ariaExpanded=String(!menuCollapsed);button.ariaLabel=menuCollapsed?'Expandir menu lateral':'Recolher menu lateral';button.title=button.ariaLabel}
function login(){
  $('#toggleMenu').hidden=true;
  document.body.classList.remove('authenticated');$('#sidebar').hidden=true;
  $('#identity').innerHTML='<span class="environment">Portal de TI · '+(session.demo?'Demonstração':'Acesso corporativo')+'</span>';
  $('#app').innerHTML=`<section class="login-wrap"><div class="login-hero"><div class="login-kicker">Seu portal de equipamentos</div><h1>Oi, eu sou<br>a E.D.N.A.</h1><p><strong>E</strong>mitente de <strong>D</strong>eclarações<br>e <strong>N</strong>ormas de <strong>A</strong>cordo.<br>Tudo organizado, do recebimento à devolução.</p><figure class="login-operation"><img src="assets/edna-ti-frente.png" alt="Edna de frente com uniforme MELI e os equipamentos de TI" width="1698" height="926" fetchpriority="high"><figcaption>Da operação à TI. Nossa mascote cuida dos detalhes.</figcaption></figure><div class="hero-footnote">${icon('check')}Estilo na entrega. Controle na devolução.</div></div><div class="login-form"><h2>${session.demo?'Vamos testar?':'Bem-vindo ao portal'}</h2><p>${session.demo?'Escolha seu perfil para conhecer a plataforma.':'Entre com sua conta corporativa.'}</p><form id="loginForm">${session.demo?`<div class="profile-choice"><button type="button" data-demo-account="ti.demo">${icon('shield')}Sou da TI</button><button type="button" data-demo-account="colaborador.demo">${icon('user')}Sou colaborador</button></div>`:''}<label for="login">${session.demo?'Usuário de teste':'Usuário de rede'}</label><input id="login" name="login" required autocomplete="username" placeholder="${session.demo?'ti.demo ou colaborador.demo':'nome.sobrenome'}"><label for="password">Senha</label><input id="password" name="password" type="password" autocomplete="current-password" required placeholder="Sua senha"><div class="error" id="loginError" role="alert"></div><button type="submit" class="full">Entrar no portal ${icon('arrow')}</button></form>${session.demo?`<div class="callout">Login simulado · Senha de teste: <strong>demonstracao</strong><br>${session.local?'Os registros ficam apenas neste navegador.':'Os registros de exemplo ficam no servidor.'}</div><div class="demo-note">Use dados fictícios. A integração com o AD será configurada depois.</div>`:''}</div></section>`;
  document.querySelectorAll('[data-demo-account]').forEach(button=>button.onclick=()=>{
    $('#login').value=button.dataset.demoAccount;$('#password').value='demonstracao';$('#loginError').textContent='';
    document.querySelectorAll('[data-demo-account]').forEach(b=>b.classList.toggle('selected',b===button));
  });
  $('#loginForm').onsubmit=async event=>{
    event.preventDefault();const button=event.target.querySelector('button[type="submit"]');button.disabled=true;
    try{await api('login',Object.fromEntries(new FormData(event.target)));tab='assignments';filter='open';categoryFilter='all';query='';await boot()}
    catch(error){$('#loginError').textContent=error.message}finally{button.disabled=false}
  };
}
function navigate(value){tab=value;query='';categoryFilter='all';filter=['assignments','returns'].includes(tab)?'open':'all';render()}
function categoryCatalog(){
  const rows=tab==='assets'?state.assets:state.assignments.filter(a=>filter==='all'||!isClosed(a));
  return `<section class="category-section" aria-label="Categorias de equipamentos"><div class="section-heading"><div><span class="eyebrow">${tab==='assets'?'INVENTÁRIO':'EQUIPAMENTOS'}</span><h2>${tab==='assets'?'Um lugar para cada equipamento.':'O que acompanha a sua rotina.'}</h2></div><button class="ghost category-reset" data-category="all" aria-pressed="${categoryFilter==='all'}">Ver todos ${icon('arrow')}</button></div><div class="category-grid">${Object.entries(categories).map(([id,c])=>{const count=rows.filter(a=>a.category===id).length;return `<button class="category-card ${categoryFilter===id?'selected':''}" data-category="${id}" aria-pressed="${categoryFilter===id}"><span class="category-icon">${icon(c.icon)}</span><span class="category-label">${c.label}</span><span class="category-count">${count} ${count===1?'item':'itens'}</span><span class="category-serial">${c.serial?'Com serial':'Serial opcional'}</span></button>`}).join('')}</div></section>`;
}
function inventoryBanner(){const i=state.inventory,integrated=i.source_kind==='integration';return `<div class="inventory-banner ${i.error?'inventory-error':''}">${icon(i.error?'info':'document')}<div><strong>${esc(integrated?i.source:'Carga inicial do inventário')}</strong><span>${i.error?esc(i.error):`${i.items} equipamentos · ${integrated?'Sincronizado':'Carregado'} em ${datetime(i.synced_at)} · ${integrated?'Integração recebendo dados':'Aguardando integração Arturito / n8n'}`}</span></div><button class="ghost" id="inventoryDetails">Ver detalhes</button></div>`}
function inventoryDetails(){const i=state.inventory,integrated=i.source_kind==='integration';modal('Fonte do inventário',`<p class="dialog-intro">${integrated?'O inventário recebe atualizações pela integração.':'A planilha foi usada como carga inicial. A conexão com Arturito ou n8n ainda não está ativa.'} Empréstimos, responsáveis e termos continuam registrados na E.D.N.A.</p><div class="callout">${i.items} equipamentos elegíveis.<br>${integrated?'Último recebimento: '+datetime(i.synced_at)+'. '+(i.sync_mode==='upsert'?'Atualização parcial; os demais registros foram mantidos.':'Carga completa recebida.'):'A planilha não será relida automaticamente. A base inicial permanece disponível enquanto a integração é configurada.'}</div><h3>Registros para conferir</h3><div class="inventory-issues">${i.issues?.length?i.issues.map(r=>`<p><strong>${esc(r.sheet||'Integração')}${r.row?' · linha '+r.row:''}</strong><br>${esc(r.reason)}</p>`).join(''):'<p>Nenhuma pendência identificada.</p>'}</div><p class="subtle">Atualizações do inventário não encerram empréstimos nem alteram termos já assinados.</p>`,null)}
function welcomeBanner(){return `<section class="welcome-banner welcome-banner-art"><div class="welcome-copy"><span class="eyebrow">E.D.N.A. + TECNOLOGIA MELI</span><h2>Tudo no seu lugar.<br><span>Do empréstimo à devolução.</span></h2><p>Equipamentos, termos e pessoas. Pode deixar comigo.</p><span class="welcome-signature">${icon('check')} Mais controle. Menos papel.</span></div><div class="welcome-art"><img src="assets/edna-ti-frente.png" alt="Edna olhando para a frente, com uniforme Mercado Livre, cercada de notebook, mouse, teclado, coletores, scanners e impressora Zebra em uma bancada de TI." width="1698" height="926" fetchpriority="high"></div></section>`}

function render(){
  if(!session.user)return login();
  document.body.classList.add('authenticated');$('#sidebar').hidden=false;
  const menuButton=$('#toggleMenu');menuButton.hidden=false;menuButton.onclick=()=>{menuCollapsed=!menuCollapsed;applyMenuState()};applyMenuState();
  const admin=session.user.admin,unseen=state.requests.filter(r=>r.status==='open').length;
  $('#identity').innerHTML=`<div class="identity"><button class="bell-button" id="notifications" aria-label="${admin?unseen+' solicitações aguardando TI':'Minhas devoluções'}">${icon('bell')}${admin&&unseen?`<span class="notification-count">${unseen}</span>`:''}</button><span class="avatar">${esc(initials(session.user.name))}</span><div class="identity-text">${esc(session.user.name)}<small>${admin?'Administração de TI':'Colaborador'}</small></div><button class="signout" id="logout">Sair</button></div>`;
  $('#notifications').onclick=()=>navigate('returns');
  $('#logout').onclick=async()=>{try{await api('logout',{});pdfUrls.forEach(url=>URL.revokeObjectURL(url));pdfUrls.clear();tab='assignments';categoryFilter='all';query='';await boot()}catch(error){toast(error.message)}};
  const links=[['assignments','dashboard',admin?'Visão geral':'Meus equipamentos'],['terms','document','Termos e aceites'],['returns','return',admin?'Devoluções':'Minhas devoluções'],...(admin?[['assets','laptop','Inventário']]:[]),['history','history','Histórico']];
  $('#navigation').innerHTML=links.map(([id,glyph,title])=>`<button class="nav-button ${tab===id?'active':''}" data-nav="${id}" title="${esc(title)}" aria-label="${esc(title)}" ${tab===id?'aria-current="page"':''}>${icon(glyph)}<span class="nav-label">${title}</span>${id==='returns'&&pendingRequests().length?`<span class="nav-count">${pendingRequests().length}</span>`:''}</button>`).join('');
  document.querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>navigate(b.dataset.nav));
  $('#environmentNote').innerHTML=session.demo?'Login de demonstração<br>Integração AD em breve':'Portal corporativo';
  const heading={assignments:admin?'Equipamentos e termos':'Meus equipamentos',terms:'Termos e aceites',returns:admin?'Central de devoluções':'Minhas devoluções',assets:'Inventário de equipamentos',history:'Histórico de movimentações'}[tab];
  const descriptions={assignments:admin?'Acompanhe os vínculos, os aceites e as devoluções da sua equipe.':'Confira seus equipamentos, aceite termos e solicite a devolução.',terms:'Consulte documentos, acompanhe aceites e baixe os comprovantes.',returns:admin?'Solicitações dos colaboradores e conferência dos equipamentos.':'Acompanhe suas solicitações e o recebimento pela TI.',assets:'Cadastre equipamentos e acompanhe sua disponibilidade.',history:'Cada movimentação com data, responsável e motivo.'};
  const live=state.assignments.filter(a=>!isClosed(a)).length,awaiting=state.terms.filter(t=>t.status==='pending').length,accepted=state.terms.filter(t=>t.status==='accepted').length,available=state.assets.filter(a=>a.available).length;
  const metrics=[['Vínculos ativos',live,'Equipamentos com responsável','laptop'],['Aceites pendentes',awaiting,'Documentos aguardando confirmação','document'],['Devoluções solicitadas',pendingRequests().length,'Solicitações em aberto','return'],[admin?'Equipamentos disponíveis':'Termos aceitos',admin?available:accepted,admin?'Prontos para nova atribuição':'Com comprovante em PDF',admin?'check':'shield']];
  $('#app').innerHTML=`<div class="breadcrumb">Mercado Livre <span>›</span> Tecnologia <span>›</span> ${esc(heading)}</div><div class="page-heading"><div><h1>${esc(heading)}</h1><p>${descriptions[tab]}</p></div><div class="heading-actions"><button class="refresh" id="refresh" aria-label="Atualizar dados">${icon('refresh')}</button>${admin?`<button id="primaryAction">${icon('plus')}${tab==='assets'?'Cadastrar equipamento':'Atribuir equipamento'}</button>`:''}</div></div>${tab==='assignments'?welcomeBanner():''}${admin&&state.inventory?inventoryBanner():''}${session.demo?`<div class="notice-strip">${icon('info')}Simulação de acesso ${session.local?'· Dados '+(session.storage==='memory'?'temporários nesta página':'salvos neste navegador'):''} · Sem conexão ao AD</div>`:''}<section class="stats" aria-label="Resumo dos equipamentos">${metrics.map(([title,number,note,glyph],i)=>`<div class="stat"><span class="stat-icon">${icon(glyph)}</span><div class="stat-label">${title}</div><div class="stat-number ${i===2&&number?'attention':''}">${number}</div><span class="stat-note">${note}</span></div>`).join('')}</section>${admin&&unseen?`<section class="attention-panel" role="status"><div class="attention-icon">${icon('bell')}</div><div class="attention-text"><strong>${unseen===1?'Uma solicitação de devolução aguarda a TI':unseen+' solicitações de devolução aguardam a TI'}</strong><p>Confira o motivo e combine o recebimento do equipamento com o colaborador.</p></div><button class="secondary" id="viewRequests">Ver solicitações ${icon('arrow')}</button></section>`:''}${['assignments','assets'].includes(tab)?categoryCatalog():''}<section class="panel"><div class="panel-head"><div><h2 id="tableTitle"></h2><p id="tableSubtitle"></p></div><div class="filters">${['assignments','returns'].includes(tab)?`<select id="filter" class="filter-select" aria-label="Filtrar status"><option value="open" ${filter==='open'?'selected':''}>${tab==='assignments'?'Vínculos em aberto':'Solicitações em aberto'}</option><option value="all" ${filter==='all'?'selected':''}>Todos os registros</option></select>`:''}<div class="search-field">${icon('search')}<input id="search" value="${esc(query)}" aria-label="Buscar registros" placeholder="Buscar por nome ou serial"></div></div></div><div class="table-wrap" id="table"></div><div class="table-footer"><span id="rowCount"></span><span>${session.demo?'Ambiente de demonstração':'Portal de TI'}</span></div></section><div class="hint">${icon('info')}${admin?'Desvincule equipamentos a qualquer momento. O histórico e os termos já aceitos são preservados.':'Solicitar a devolução avisa a TI. O encerramento do vínculo fica registrado no histórico.'}</div>`;
  if($('#inventoryDetails'))$('#inventoryDetails').onclick=inventoryDetails;
  $('#refresh').onclick=async()=>{try{await loadState();render();toast('Dados atualizados.')}catch(e){toast(e.message)}};
  if(admin)$('#primaryAction').onclick=()=>tab==='assets'?asset():assign();
  document.querySelectorAll('[data-category]').forEach(button=>button.onclick=()=>{categoryFilter=categoryFilter===button.dataset.category?'all':button.dataset.category;render()});
  if($('#viewRequests'))$('#viewRequests').onclick=()=>navigate('returns');
  $('#search').oninput=event=>{query=event.target.value;table()};
  if($('#filter'))$('#filter').onchange=event=>{filter=event.target.value;render()};
  table();
}
function equipment(machine){return `<div class="equipment-cell"><span class="equipment-icon">${icon(categoryInfo(machine.category).icon)}</span><div><strong>${esc(machine.model)}</strong><small>${esc(assetIdentity(machine))}</small></div></div>`}
function person(name){return `<div class="person-cell"><span class="avatar">${esc(initials(name))}</span><span>${esc(name)}</span></div>`}
function assignmentActions(a){
  if(isClosed(a))return `<button class="ghost" data-history="${a.id}">${icon('history')}Histórico</button>`;
  if(session.user.admin)return `${a.status==='active'?`<button class="secondary" data-return="${a.id}">Receber devolução</button>`:''}<button class="danger" data-unlink="${a.id}">${icon('unlink')}Desvincular</button>`;
  const request=requestFor(a.id);
  if(request)return `<span class="subtle">Solicitação enviada</span>`;
  if(['pending','active'].includes(a.status))return `<button class="secondary" data-request="${a.id}">${icon('return')}Solicitar devolução</button>`;
  return '<span class="subtle">Confira o termo de devolução</span>';
}
function table(){
  const match=value=>(JSON.stringify(value)+' '+categoryInfo(value.category).label).toLocaleLowerCase().includes(query.toLocaleLowerCase());
  const inCategory=value=>categoryFilter==='all'||value.category===categoryFilter;
  let rows=[],head='';
  if(tab==='assignments'){
    $('#tableTitle').textContent=session.user.admin?'Vínculos de equipamentos':'Equipamentos vinculados a você';
    $('#tableSubtitle').textContent='Fixos e empréstimos, com acompanhamento do início ao fim.';
    head='<th>Equipamento</th><th>Responsável</th><th>Modalidade</th><th>Status</th><th>Ações</th>';
    rows=state.assignments.filter(a=>(filter==='all'||!isClosed(a))&&inCategory(a)&&match(a)).slice().reverse().map(a=>`<tr><td>${equipment(a)}<span class="equipment-category">${esc(categoryInfo(a.category).label)}</span></td><td>${person(a.name)}</td><td>${esc(a.kind)}<small>${a.due?'Até '+date(a.due):'Uso contínuo'}</small></td><td>${badge(a.status)}${requestFor(a.id)?'<small class="requested-note">Devolução solicitada</small>':''}</td><td><div class="row-actions">${assignmentActions(a)}</div></td></tr>`);
  } else if(tab==='terms'){
    $('#tableTitle').textContent='Documentos e comprovantes';$('#tableSubtitle').textContent='Termos de responsabilidade e de devolução.';
    head='<th>Documento</th><th>Colaborador / equipamento</th><th>Assinar até</th><th>Status</th><th>Solicitação por e-mail</th><th>Ações</th>';
    rows=state.terms.filter(match).map(t=>{const s=JSON.parse(t.snapshot),mail=mailFor(t.id),expired=isExpired(t);return `<tr><td><strong>Termo #${String(t.id).padStart(5,'0')}</strong><small>${t.kind==='responsabilidade'?'Responsabilidade':'Devolução'}</small></td><td>${esc(s.name)}<small>${esc(assetIdentity(s))} · ${esc(s.model)}</small></td><td>${t.sign_due_at?datetime(t.sign_due_at):'<span class="muted">Aguardando cadastro</span>'}</td><td>${expired?'<span class="badge cancelled">Prazo vencido</span>':badge(t.status)}</td><td>${mail?mailBadge(mail.status):'<span class="subtle">Disponível no portal</span>'}</td><td><div class="row-actions"><button class="${t.status==='pending'&&!expired&&t.person===session.user.id?'secondary':'ghost'}" data-term="${t.id}">${t.status==='pending'&&!expired&&t.person===session.user.id?'Ler e aceitar':'Ver termo'}</button>${t.status==='accepted'?pdfLink(t):''}${mail?`<button class="ghost" data-email="${t.id}">E-mail</button>`:''}</div></td></tr>`});
  } else if(tab==='returns'){
    $('#tableTitle').textContent=session.user.admin?'Solicitações de devolução':'Suas solicitações';$('#tableSubtitle').textContent='O vínculo permanece em aberto até a conclusão ou o desvínculo pela TI.';
    head='<th>Equipamento / colaborador</th><th>Motivo da solicitação</th><th>Solicitado em</th><th>Status</th><th>Ações</th>';
    rows=state.requests.filter(r=>(filter==='all'||['open','processing'].includes(r.status))&&match(r)).map(r=>{
      const a=state.assignments.find(a=>a.id===r.assignment);
      const actions=session.user.admin&&['open','processing'].includes(r.status)?`${a?.status==='active'?`<button class="secondary" data-return="${r.assignment}">Receber e gerar termo</button>`:''}<button class="danger" data-unlink="${r.assignment}">Desvincular</button>${a?.status==='pending'?'<span class="subtle">Termo inicial ainda sem aceite</span>':''}`:`<button class="ghost" data-history="${r.assignment}">Ver histórico</button>`;
      return `<tr><td><strong>${esc(assetIdentity(r))} · ${esc(r.model)}</strong><small>${esc(r.name)}</small></td><td class="reason">${esc(r.reason)}</td><td>${datetime(r.created)}</td><td>${badge(r.status)}</td><td><div class="row-actions">${actions}</div></td></tr>`;
    });
  } else if(tab==='assets'){
    $('#tableTitle').textContent='Inventário';$('#tableSubtitle').textContent='Serial, categoria e disponibilidade de cada equipamento.';
    head='<th>Equipamento</th><th>Categoria</th><th>Número de série</th><th>Status de origem / local</th><th>Disponibilidade</th><th>Ações</th>';
    rows=state.assets.filter(a=>inCategory(a)&&match(a)).map(a=>`<tr><td>${equipment(a)}</td><td><span class="category-tag">${esc(categoryInfo(a.category).label)}</span></td><td>${a.serial?esc(a.serial):'<span class="serial-optional">Não informado<small>Opcional nesta categoria</small></span>'}</td><td>${esc(a.source_status||'Cadastro local')}<small>${esc(a.location||'')}</small></td><td><span class="badge ${a.available?'active':'pending'}">${a.available?'Disponível':a.inventory_blocked?'Bloqueado no inventário':'Indisponível'}</span>${a.local_override?'<small>Ajuste local salvo</small>':''}</td><td><button class="secondary" data-edit-asset="${a.id}">Editar</button></td></tr>`);
  } else if(tab==='history'){
    $('#tableTitle').textContent='Rastreabilidade das movimentações';$('#tableSubtitle').textContent='Solicitações, aceites, recebimentos e desvínculos registrados.';
    head='<th>Movimentação</th><th>Equipamento / colaborador</th><th>Quem registrou</th><th>Data</th><th>Detalhes</th>';
    rows=state.history.filter(match).map(h=>`<tr><td><strong>${esc(eventLabels[h.action]||h.action)}</strong></td><td>${esc(assetIdentity(h))} · ${esc(h.model)}<small>${esc(h.name)}</small></td><td>${esc(h.actor_name)}</td><td>${datetime(h.at)}</td><td class="reason">${esc(h.detail)}</td></tr>`);
  }
  $('#table').innerHTML=rows.length?`<table><thead><tr>${head}</tr></thead><tbody>${rows.join('')}</tbody></table>`:`<div class="empty">${icon(tab==='returns'?'return':'laptop')}<strong>${tab==='returns'?'Nenhuma solicitação por aqui':'Nenhum registro encontrado'}</strong><p>${query?'Tente buscar com outro nome ou serial.':tab==='returns'?'As solicitações de devolução aparecerão nesta central.':'Os registros deste fluxo aparecerão aqui.'}</p></div>`;
  $('#rowCount').textContent=rows.length+' '+(rows.length===1?'registro':'registros')+(categoryFilter!=='all'?' · '+categoryInfo(categoryFilter).label:'');
  document.querySelectorAll('[data-edit-asset]').forEach(b=>b.onclick=()=>editAsset(+b.dataset.editAsset));
  document.querySelectorAll('[data-email]').forEach(b=>b.onclick=()=>invitationPreview(+b.dataset.email));
  document.querySelectorAll('[data-term]').forEach(b=>b.onclick=()=>term(+b.dataset.term));
  document.querySelectorAll('[data-return]').forEach(b=>b.onclick=()=>returned(+b.dataset.return));
  document.querySelectorAll('[data-request]').forEach(b=>b.onclick=()=>requestReturn(+b.dataset.request));
  document.querySelectorAll('[data-unlink]').forEach(b=>b.onclick=()=>unlink(+b.dataset.unlink));
  document.querySelectorAll('[data-history]').forEach(b=>b.onclick=()=>showHistory(+b.dataset.history));
}
function modal(title,body,submit,kind=''){
  $('#modal').innerHTML=`<div class="dialog-header"><h2 id="modalTitle">${title}</h2><button type="button" class="close" aria-label="Fechar">${icon('close')}</button></div><div class="dialog-content"><form id="modalForm">${body}<div class="error" id="formError" role="alert"></div>${submit?`<div class="actions"><button type="button" class="secondary close">Cancelar</button><button type="submit" class="${kind}">${submit}</button></div>`:''}</form></div>`;
  $('#modal').showModal();$('#modal').querySelectorAll('.close').forEach(b=>b.onclick=()=>$('#modal').close());
}
function save(path,transform=x=>x,message='Registro salvo com sucesso.'){
  $('#modalForm').onsubmit=async event=>{
    event.preventDefault();const button=event.target.querySelector('button[type="submit"]');button.disabled=true;
    try{await api(path,transform(Object.fromEntries(new FormData(event.target))));$('#modal').close();await loadState();render();toast(message)}
    catch(error){if($('#modal').open)$('#formError').textContent=error.message;else toast(error.message)}finally{button.disabled=false}
  };
}
function asset(){
  const selected=Object.hasOwn(categories,categoryFilter)?categoryFilter:'notebook';
  modal('Cadastrar equipamento',`<p class="dialog-intro">Do mouse ao coletor: cada item tem seu lugar no inventário.</p><label for="assetCategory">Categoria do equipamento</label><select id="assetCategory" name="category" required>${categoryOptions(selected)}</select><label for="assetModel">Marca e modelo</label><input id="assetModel" name="model" maxlength="150" required><label for="assetSerial" id="assetSerialLabel">Número de série</label><input id="assetSerial" name="serial" maxlength="150" aria-describedby="serialHint"><div class="serial-hint" id="serialHint"></div>`,'Cadastrar equipamento');
  const updateSerial=()=>{const c=categories[$('#assetCategory').value];$('#assetSerial').required=c.serial;$('#assetSerialLabel').textContent='Número de série'+(c.serial?' *':' (opcional)');$('#assetModel').placeholder=c.example;$('#assetSerial').placeholder=c.serial?'Leia ou digite o serial do equipamento':'Preencha apenas se o item possuir serial';$('#serialHint').innerHTML=icon(c.serial?'shield':'info')+(c.serial?'O serial identifica este equipamento e é obrigatório.':'Mouse e teclado podem ser cadastrados sem serial. Cada unidade recebe uma referência interna automática.')};
  $('#assetCategory').onchange=updateSerial;updateSerial();
  save('assets');
}
function assign(){
  const available=state.assets.filter(a=>a.available&&Object.hasOwn(categories,a.category));
  if(!available.length)return toast('Nenhum equipamento disponível nas categorias permitidas. Confira o inventário.');
  const selected=[];
  const peopleOptions=()=>state.people.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');
  modal('Emprestar equipamentos',`<p class="dialog-intro">Informe a quantidade e adicione os itens pela lista. Você pode entregar o lote a uma pessoa ou definir um responsável por equipamento.</p><div class="form-grid"><div><label for="loanQuantity">Quantos equipamentos?</label><input id="loanQuantity" type="number" min="1" max="100" step="1" value="1" required></div><div><label for="person">Colaborador principal</label><select id="person" name="person"><option value="">Selecione o responsável</option>${peopleOptions()}</select></div></div><div class="loan-picker"><div class="form-grid"><div><label for="assignCategory">Categoria</label><select id="assignCategory"><option value="all">Todas as categorias</option>${categoryOptions(categoryFilter)}</select></div><div><label for="loanSearch">Buscar equipamento</label><input id="loanSearch" type="search" placeholder="Digite o modelo ou serial" autocomplete="off"></div></div><label for="loanPicker">Equipamentos disponíveis</label><select id="loanPicker" size="5" aria-describedby="pickerHelp"></select><div class="picker-actions"><small id="pickerHelp">Selecione um item e clique em Adicionar.</small><button id="addEquipment" type="button" class="secondary">${icon('plus')}Adicionar</button></div></div><div class="selection-heading"><strong>Equipamentos selecionados</strong><span id="selectionCount" aria-live="polite"></span></div><div id="selectedEquipment" class="selected-equipment"></div><div class="form-grid"><div><label for="kind">Modalidade</label><select name="kind" id="kind"><option>Empréstimo</option><option>Fixa</option></select></div><div id="dueField"><label for="due">Devolução prevista</label><input type="date" name="due" id="due" required></div></div>${deadlineField()}<label for="notes">Condições e acessórios entregues</label><textarea id="notes" name="notes" maxlength="2000" required placeholder="Descreva as condições dos itens e os acessórios entregues."></textarea><div class="callout">Cada equipamento terá seu termo e responsável. Todo o lote é conferido antes de confirmar o empréstimo.</div>`,'Gerar termos do empréstimo');
  const quantity=()=>Number($('#loanQuantity').value);
  const submit=$('#modalForm button[type="submit"]');
  function updateSelection(){
    $('#selectionCount').textContent=selected.length+' de '+(quantity()||0);
    submit.disabled=!Number.isInteger(quantity())||quantity()<1||quantity()>100||selected.length!==quantity();
    $('#person').required=selected.some(item=>!item.person);
    $('#selectedEquipment').innerHTML=selected.length?selected.map(item=>{const a=available.find(a=>a.id===item.asset);return `<div class="selected-item"><span class="equipment-icon">${icon(categoryInfo(a.category).icon)}</span><div class="selected-item-info"><strong>${esc(a.model)}</strong><small>${esc(assetIdentity(a))}</small><label class="sr-only" for="recipient-${a.id}">Responsável por ${esc(assetIdentity(a))}</label><select id="recipient-${a.id}" data-item-person="${a.id}"><option value="">Usar colaborador principal</option>${state.people.map(p=>`<option value="${esc(p.id)}" ${item.person===p.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></div><button type="button" class="ghost" data-remove-item="${a.id}" aria-label="Remover ${esc(assetIdentity(a))}">${icon('close')}</button></div>`}).join(''):'<div class="selection-empty">Os itens adicionados aparecerão aqui.</div>';
    $('#selectedEquipment').querySelectorAll('[data-remove-item]').forEach(b=>b.onclick=()=>{selected.splice(selected.findIndex(i=>i.asset===+b.dataset.removeItem),1);updateSelection();updatePicker()});
    $('#selectedEquipment').querySelectorAll('[data-item-person]').forEach(select=>select.onchange=()=>{selected.find(i=>i.asset===+select.dataset.itemPerson).person=select.value;$('#person').required=selected.some(i=>!i.person)});
  }
  function updatePicker(){
    const search=$('#loanSearch').value.toLocaleLowerCase().trim(),cat=$('#assignCategory').value;
    const rows=available.filter(a=>!selected.some(i=>i.asset===a.id)&&(cat==='all'||a.category===cat)&&(`${a.model} ${a.serial||''} ${categoryInfo(a.category).label}`).toLocaleLowerCase().includes(search));
    $('#loanPicker').innerHTML=rows.length?rows.slice(0,200).map(a=>`<option value="${a.id}">${esc(assetIdentity(a))} · ${esc(a.model)}</option>`).join(''):'<option value="" disabled>Nenhum equipamento disponível para esta busca</option>';
    if(rows.length)$('#loanPicker').selectedIndex=0;
    $('#addEquipment').disabled=!rows.length||selected.length>=quantity();
    $('#pickerHelp').textContent=rows.length>200?'Mostrando 200 itens. Refine a busca pelo serial.':'Selecione um item e clique em Adicionar.';
  }
  function addItem(){
    const id=+$('#loanPicker').value;
    if(!id||selected.some(i=>i.asset===id)||selected.length>=quantity())return;
    selected.push({asset:id,person:''});updateSelection();updatePicker();
  }
  $('#addEquipment').onclick=addItem;$('#loanPicker').ondblclick=addItem;
  $('#loanPicker').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();addItem()}};
  $('#loanSearch').oninput=updatePicker;$('#assignCategory').onchange=updatePicker;
  $('#loanQuantity').oninput=()=>{updateSelection();updatePicker()};
  $('#kind').onchange=event=>{const loan=event.target.value==='Empréstimo';$('#dueField').hidden=!loan;$('#due').required=loan};
  const today=new Date();$('#due').min=today.getFullYear()+'-'+String(today.getMonth()+1).padStart(2,'0')+'-'+String(today.getDate()).padStart(2,'0');
  $('#assignCategory').value=available.some(a=>a.category===categoryFilter)?categoryFilter:'all';
  updateSelection();updatePicker();
  save('assign',data=>({...data,quantity:quantity(),items:selected.map(i=>({asset:i.asset,person:i.person||data.person}))}),'Empréstimo registrado. Os termos estão disponíveis para cada responsável.');
}

function equipmentSummary(a){return `<div class="dialog-equipment"><span class="equipment-icon">${icon(categoryInfo(a.category).icon)}</span><div><strong>${esc(assetIdentity(a))} · ${esc(a.model)}</strong><small>${esc(categoryInfo(a.category).label)} · ${a.serial?'Serial: '+esc(a.serial):'Serial não informado (opcional)'}</small><small>Responsável: ${esc(a.name)}</small></div></div>`}
function requestReturn(id){
  const a=state.assignments.find(a=>a.id===id);
  modal('Solicitar devolução',`${equipmentSummary(a)}<p class="dialog-intro">Sua solicitação aparecerá como alerta para a equipe de TI. Aguarde a orientação para entregar o equipamento e os acessórios.</p><label for="returnReason">Motivo ou observações</label><textarea id="returnReason" name="reason" required maxlength="2000" placeholder="Ex.: troca de equipamento, fim do empréstimo ou encerramento das atividades."></textarea><div class="callout">O equipamento continua vinculado a você enquanto a TI organiza a devolução.</div>`,'Enviar solicitação');
  save('request-return',data=>({...data,id}),'Solicitação enviada. A TI já pode visualizá-la na central de devoluções.');
}
function returned(id){
  const a=state.assignments.find(a=>a.id===id),request=requestFor(id);
  modal('Receber devolução',`${equipmentSummary(a)}${request?`<div class="callout"><strong>Solicitação do colaborador</strong><br>${esc(request.reason)}</div>`:''}<p class="dialog-intro">Confira o equipamento recebido antes de emitir o termo de devolução.</p>${deadlineField()}<label for="returnNotes">Condições e acessórios recebidos</label><textarea id="returnNotes" name="notes" maxlength="2000" required placeholder="Descreva o estado e os acessórios conferidos pela TI."></textarea><label class="check"><input type="checkbox" name="received" required>Confirmo que a TI recebeu fisicamente e conferiu o equipamento.</label><p class="subtle">O colaborador receberá o termo para aceite. O vínculo será encerrado após essa confirmação.</p>`,'Gerar termo de devolução');
  save('return',data=>({...data,id,received:data.received==='on'}),'Recebimento registrado. Solicitação de assinatura gerada para o e-mail cadastrado.');
}
function unlink(id){
  const a=state.assignments.find(a=>a.id===id);
  modal('Desvincular equipamento',`${equipmentSummary(a)}<div class="callout warning">O vínculo será encerrado imediatamente pela TI e o equipamento ficará disponível para nova atribuição. Esta ação registra um desvínculo administrativo; o recebimento físico é registrado pelo fluxo de devolução.</div><label for="unlinkReason">Motivo do desvínculo</label><textarea id="unlinkReason" name="reason" required maxlength="2000" placeholder="Ex.: substituição de equipamento ou correção de atribuição."></textarea><label class="check"><input type="checkbox" name="confirm" required>Confirmo que desejo encerrar este vínculo agora.</label><p class="subtle">Termos já aceitos serão mantidos. Termos pendentes serão cancelados. Seu nome, a data e o motivo ficarão no histórico.</p>`,'Desvincular agora','danger-solid');
  save('unlink',data=>({...data,id,confirm:data.confirm==='on'}),'Equipamento desvinculado. O histórico foi preservado.');
}
function term(id){
  const t=state.terms.find(t=>t.id===id),s=JSON.parse(t.snapshot),can=t.status==='pending'&&!isExpired(t)&&t.person===session.user.id;
  let after='';
  if(can)after=`<label class="check"><input name="agree" type="checkbox" required>Li e concordo com o termo acima e confirmo as informações deste registro.</label><label for="signer">Digite seu nome: ${esc(session.user.name)}</label><input name="name" id="signer" required autocomplete="name"><p class="subtle">O comprovante registrará o nome digitado, a conta e a data do aceite.${session.demo?' Este é um aceite de demonstração.':''}</p>`;
  else if(t.status==='accepted')after=`<p class="subtle">Aceito em ${datetime(t.accepted)}</p><div class="row-actions">${pdfLink(t,'Baixar comprovante PDF')}</div>${session.local?'<p class="subtle">Documento de simulação salvo no navegador.</p>':`<p class="subtle">SHA-256: ${esc(t.digest)}</p>`}`;
  else if(isExpired(t))after='<div class="callout danger">O prazo de assinatura venceu. Contate a TI para emissão de um novo termo.</div>';
  else if(t.status==='cancelled')after='<div class="callout danger">Este termo foi cancelado pelo desvínculo administrativo. O texto original permanece no histórico.</div>';
  else after='<p class="subtle">O aceite deve ser realizado pelo colaborador responsável.</p>';
  modal(t.kind==='responsabilidade'?'Termo de responsabilidade':'Termo de devolução',`<p class="dialog-intro">Documento #${String(id).padStart(5,'0')} · Versão 1<br><strong>${esc(s.name)}</strong> · ${esc(assetIdentity(s))} / ${esc(s.model)}<br>${esc(categoryInfo(s.category).label)} · ${s.serial?'Serial: '+esc(s.serial):'Serial não informado (opcional nesta categoria)'}</p>${t.sign_due_at?`<div class="callout"><strong>Prazo para assinatura:</strong> ${datetime(t.sign_due_at)}<br>Solicitação direcionada a ${esc(t.recipient_email||'Disponível no portal; e-mail não informado pelo diretório')}.</div>`:''}<div class="term-body">${esc(t.body)}</div>${after}`,can?'Confirmar e gerar PDF':null);
  if(can)save('accept',data=>({...data,id,agree:data.agree==='on'}),'Aceite registrado. Seu comprovante PDF está disponível.');
}
function showHistory(id){
  const a=state.assignments.find(a=>a.id===id),entries=state.history.filter(h=>h.assignment===id);
  modal('Histórico do equipamento',`${equipmentSummary(a)}${badge(a.status)}${a.closure_reason?`<p class="dialog-intro"><strong>Motivo do desvínculo:</strong> ${esc(a.closure_reason)}</p>`:''}<div class="timeline">${entries.length?entries.map(h=>`<div class="timeline-item"><strong>${esc(eventLabels[h.action]||h.action)}</strong><small>${datetime(h.at)} · ${esc(h.actor_name)}</small><p>${esc(h.detail)}</p></div>`).join(''):'<p class="subtle">Este vínculo foi criado antes do histórico de movimentações. Os termos associados continuam disponíveis.</p>'}</div>`,null);
}
async function refreshInBackground(){
  if(!session?.user||!state||$('#modal').open||document.hidden)return;
  try{
    const previous=JSON.stringify(state),count=state.requests.filter(r=>r.status==='open').length;
    await loadState();
    if(previous!==JSON.stringify(state)){
      render();
      if(session.user.admin&&state.requests.filter(r=>r.status==='open').length>count)toast('Nova solicitação de devolução recebida.');
    }
  }catch(_){}
}
window.addEventListener('storage',event=>{if(event.key==='termo.browser-demo.v1')refreshInBackground()});
window.addEventListener('focus',refreshInBackground);
setInterval(refreshInBackground,20000);
boot();

function editAsset(id){
 const item=state.assets.find(a=>a.id===id);if(!item)return;
 const states={available:'Disponível',maintenance:'Em manutenção',blocked:'Bloqueado',retired:'Baixado'};
 const selected=item.local_state||(item.inventory_blocked?'blocked':'available');
 modal('Editar equipamento',`<p class="dialog-intro">${esc(assetIdentity(item))} · ${esc(categoryInfo(item.category).label)}</p><label for="editModel">Marca e modelo</label><input id="editModel" name="model" maxlength="150" value="${esc(item.model)}" required><label for="editLocation">Local</label><input id="editLocation" name="location" maxlength="250" value="${esc(item.location||'')}"><label for="editState">Situação no inventário</label><select id="editState" name="state">${Object.entries(states).map(([value,label])=>`<option value="${value}" ${value===selected?'selected':''}>${label}</option>`).join('')}</select><p class="callout">${session.local?'Esta prévia salva alterações somente neste navegador.':'Alterações salvas no banco do servidor, com histórico e proteção contra edições simultâneas.'} Serial e categoria são mantidos. A edição não encerra empréstimos nem altera termos assinados.</p>`,'Salvar alterações');
 save('edit-asset',data=>({...data,id,revision:item.edit_revision||0}),'Equipamento atualizado.');
}
