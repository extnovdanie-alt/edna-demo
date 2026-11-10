/* Simulação no navegador. Não autentica contas reais nem consulta o AD. */
(function (root) {
  'use strict';
  const KEY = 'termo.browser-demo.v1';
  const SESSION_KEY = 'termo.browser-demo.session.v1';
  const CATEGORIES = {mouse:'Mouse',teclado:'Teclado',notebook:'Notebook',ring_scanner:'Ring scanner',handheld:'Handheld',leitor_2d:'Leitor 2D',impressora_zebra:'Impressora Zebra'};
  const ACCOUNTS = [
    {id:'ti.demo', name:'Equipe de TI', admin:true},
    {id:'colaborador.demo', name:'Ana Souza', admin:false}
  ];
  const TEXT = {
    responsabilidade:'Declaro que recebi o equipamento identificado neste termo e os acessórios descritos, nas condições informadas. Comprometo-me a utilizá-lo em atividades autorizadas pela empresa, zelar por sua conservação, não cedê-lo a terceiros sem autorização e comunicar à TI perdas, defeitos ou incidentes de segurança. Comprometo-me a devolvê-lo quando solicitado ou no término do empréstimo.',
    devolucao:'Declaro que devolvi à equipe de TI o equipamento e os acessórios identificados neste termo. Confirmo as condições e observações de recebimento registradas pela TI. Este aceite registra a devolução descrita e encerra a atribuição deste equipamento.'
  };
  const clone = value => JSON.parse(JSON.stringify(value));
  const check = (condition, message) => {if (!condition) throw Error(message);};
  const nextId = rows => Math.max(0,...rows.map(row=>row.id))+1;
  const closed = assignment => ['returned','detached'].includes(assignment.status);
  function signingDays(value=5) {
    check((typeof value==='number'&&Number.isInteger(value))||(typeof value==='string'&&/^[1-5]$/.test(value)),'O prazo de assinatura deve ser de 1 a 5 dias corridos.');
    const days=Number(value);check(days>=1&&days<=5,'O prazo de assinatura deve ser de 1 a 5 dias corridos.');return days;
  }
  function emailAddress(value) {
    const email=String(value||'').trim().toLowerCase();
    check(email.length<=254&&/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}$/.test(email)&&!email.includes('..'),'Informe um e-mail válido.');
    return email;
  }

  // PDF simples com fonte monoespaçada, quebra de linha e paginação.
  // WinAnsi preserva os acentos usados em português; os objetos são ASCII.
  function pdfLiteral(value) {
    const text=String(value).replace(/[“”]/g,'"').replace(/[‘’]/g,"'").replace(/[–—]/g,'-').replace(/\u00a0/g,' ');
    return '('+Array.from(text).map(ch=>{
      const n=ch.charCodeAt(0);
      if ('()\\'.includes(ch)) return '\\'+ch;
      if (n<32 || n>255) return '?';
      return n>126?'\\'+n.toString(8).padStart(3,'0'):ch;
    }).join('')+')';
  }
  function wrap(text, width=80) {
    const lines=[];
    for (const paragraph of String(text).split('\n')) {
      let line='';
      for (let word of paragraph.split(/\s+/).filter(Boolean)) {
        if (line && line.length+word.length+1>width) {lines.push(line);line='';}
        while (word.length>width) {lines.push(word.slice(0,width));word=word.slice(width);}
        if (word) line+=(line?' ':'')+word;
      }
      lines.push(line);
    }
    return lines;
  }
  function makePdf(term, name, accepted) {
    const s=JSON.parse(term.snapshot);
    const paragraphs=[
      'Emitente de Declarações e Normas de Acordo', '',
      'DOCUMENTO DE DEMONSTRAÇÃO - LOGIN SIMULADO, SEM AD', '',
      'Termo #'+String(term.id).padStart(5,'0')+' - '+(term.kind==='devolucao'?'Devolução':'Responsabilidade'),
      'Colaborador: '+s.name, 'Conta simulada: '+s.person,
      'Categoria: '+(CATEGORIES[s.category]||'Equipamento'), 'Equipamento: '+s.model, 'Número de série: '+(s.serial||'Não informado (opcional nesta categoria)'),
      'Modalidade: '+s.kind, 'Prazo: '+(s.due||'Uso contínuo'), '',
      'DECLARAÇÃO ACEITA', term.body, '', 'REGISTRO DO ACEITE SIMULADO',
      'Nome digitado: '+name, 'Data e hora (UTC): '+accepted,
      'Confirmação: leitura e concordância marcadas na demonstração.', '',
      'Este arquivo pertence a uma simulação local. A identidade não foi validada no AD. Não contém assinatura com certificado digital.'
    ];
    const lines=paragraphs.flatMap(p=>wrap(p));
    const pages=[];
    for (let i=0;i<lines.length;i+=44) pages.push(lines.slice(i,i+44));
    const objects=[null,null,null,
      '<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>',
      '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>'];
    const refs=[];
    for (let i=0;i<pages.length;i++) {
      const pageId=objects.length, streamId=pageId+1;
      refs.push(pageId+' 0 R');
      let content='q 1 0.902 0 rg 0 768 595.28 73.89 re f Q\n0.16 0.16 0.16 rg\nBT /F2 19 Tf 48 790 Td '+pdfLiteral('E.D.N.A. | EQUIPAMENTOS')+' Tj ET\n';
      content+='0.15 0.15 0.15 rg\nBT /F1 10 Tf 14 TL 48 750 Td\n';
      content+=pages[i].map((line,j)=>(j?'T*\n':'')+pdfLiteral(line)+' Tj').join('\n')+'\nET\n';
      content+='BT /F1 8 Tf 48 34 Td '+pdfLiteral('Demonstração local - página '+(i+1)+' de '+pages.length)+' Tj ET\n';
      objects.push('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents '+streamId+' 0 R >>');
      objects.push('<< /Length '+content.length+' >>\nstream\n'+content+'endstream');
    }
    objects[1]='<< /Type /Catalog /Pages 2 0 R >>';
    objects[2]='<< /Type /Pages /Count '+pages.length+' /Kids ['+refs.join(' ')+'] >>';
    let pdf='%PDF-1.4\n', offsets=[0];
    for (let i=1;i<objects.length;i++) {offsets[i]=pdf.length;pdf+=i+' 0 obj\n'+objects[i]+'\nendobj\n';}
    const xref=pdf.length;
    pdf+='xref\n0 '+objects.length+'\n0000000000 65535 f \n';
    for (let i=1;i<objects.length;i++) pdf+=String(offsets[i]).padStart(10,'0')+' 00000 n \n';
    pdf+='trailer\n<< /Size '+objects.length+' /Root 1 0 R >>\nstartxref\n'+xref+'\n%%EOF\n';
    return pdf;
  }

  function create(options={}) {
    const clock=options.now||(()=>new Date().toISOString());
    let storage, sessionStore;
    try {storage='storage' in options?options.storage:root.localStorage;storage.setItem(KEY+'.check','1');storage.removeItem(KEY+'.check');} catch (_) {storage=null;}
    try {sessionStore='sessionStorage' in options?options.sessionStorage:root.sessionStorage;} catch (_) {sessionStore=null;}
    let memory=null, identity=null;
    try {identity=ACCOUNTS.find(a=>a.id===sessionStore?.getItem(SESSION_KEY))||null;} catch (_) {}
    const mode=storage?'browser':'memory';
    function persist(value) {
      if (storage) {
        try {storage.setItem(KEY,JSON.stringify(value));} catch (_) {throw Error('Não foi possível salvar no navegador. Verifique o espaço e as permissões de armazenamento.');}
      } else memory=clone(value);
    }
    function invitation(data,term,days=5) {
      const person=data.people.find(p=>p.id===term.person);
      days=signingDays(days);
      term.sign_days=days;
      term.sign_due_at ||= new Date(new Date(clock()).getTime()+days*86400000).toISOString();
      term.recipient_email=person.email;
      const s=JSON.parse(term.snapshot),link='index.html?termo='+term.id;
      const subject='E.D.N.A. — Solicitação de assinatura do termo #'+String(term.id).padStart(5,'0');
      const body='Olá, '+person.name+'.\n\nHá um termo de '+(term.kind==='devolucao'?'devolução':'responsabilidade')+' para você assinar.\nEquipamento: '+(s.serial||'Sem serial')+' — '+s.model+'.\nPrazo: '+days+' dia(s) corrido(s).\nAssine até: '+term.sign_due_at+' (UTC).\n\nAcesse o portal e entre com sua própria conta:\n'+link+'\n\nE.D.N.A. — Emitente de Declarações e Normas de Acordo';
      const existing=data.mail.find(m=>m.term===term.id);
      if(existing){existing.status='simulated';existing.attempts++;return existing;}
      const mail={id:nextId(data.mail),term:term.id,person:term.person,recipient:person.email,subject,body,link,status:'simulated',created:clock(),sent_at:null,attempts:1,error:null};
      data.mail.push(mail);return mail;
    }
    function newTerm(data, assignment, kind, notes, days=5, seed=false) {
      days=signingDays(days);
      const machine=data.assets.find(a=>a.id===assignment.asset);
      const person=data.people.find(p=>p.id===assignment.person);
      const snapshot={...assignment,...machine,id:assignment.id,name:person.name,notes};
      const term={id:nextId(data.terms),assignment:assignment.id,person:assignment.person,kind,
        body:TEXT[kind]+'\n\nModalidade: '+assignment.kind+'. Prazo: '+(assignment.due||'uso contínuo')+'.\nCondições e acessórios: '+notes,
        snapshot:JSON.stringify(snapshot),status:'pending',created:clock(),accepted:null,digest:null,pdfData:null};
      data.terms.push(term);
      if(person.email)invitation(data,term,days);
      return term;
    }
    function history(data, assignment, action, detail) {
      data.history.push({id:nextId(data.history),assignment,at:clock(),actor:identity.id,action,detail});
    }
    function migrate(data) {
      data.requests ||= [];
      data.history ||= [];
      data.mail ||= [];
      for(const person of data.people)person.email ||= person.id+'@example.com';
      for(const term of data.terms.filter(t=>t.status==='pending'&&!t.sign_due_at))invitation(data,term,5);
      for(const asset of data.assets) {
        asset.category ||= /notebook|latitude|thinkpad|macbook|elitebook|probook/i.test(asset.model)?'notebook':'outro';
      }
      return data;
    }
    function load() {
      let raw;
      try {raw=storage?.getItem(KEY);} catch (_) {throw Error('Não foi possível ler os registros da demonstração.');}
      if (raw) {
        try {const saved=JSON.parse(raw);check(saved.version===1 && Array.isArray(saved.terms) && Array.isArray(saved.assets) && Array.isArray(saved.people) && Array.isArray(saved.assignments),'Formato inválido.');return migrate(saved);}
        catch (_) {throw Error('Os registros locais da demonstração não puderam ser lidos.');}
      }
      if (memory) return migrate(clone(memory));
      const data={version:1,people:ACCOUNTS.map(({id,name})=>({id,name,email:id+'@example.com'})),
        assets:[{id:1,tag:'PAT-001',model:'Dell Latitude 5440',serial:'DEMO-001',category:'notebook'},
          {id:2,tag:'PAT-002',model:'Lenovo ThinkPad E14',serial:'DEMO-002',category:'notebook'},
          {id:3,tag:'PAT-003',model:'Dell OptiPlex 7010',serial:'DEMO-003',category:'outro'}],
        assignments:[{id:1,asset:1,person:'colaborador.demo',kind:'Fixa',due:null,notes:'Bom estado. Carregador e mochila entregues.',status:'pending'}],terms:[],requests:[],history:[],mail:[]};
      newTerm(data,data.assignments[0],'responsabilidade',data.assignments[0].notes,5,true);
      persist(data);
      return data;
    }
    async function request(path, input) {
      if (path==='session') return {user:identity?{...clone(identity),email:load().people.find(p=>p.id===identity.id)?.email||null}:null,csrf:'simulated',demo:true,local:true,storage:mode};
      if (path==='login') {
        const account=ACCOUNTS.find(a=>a.id===String(input.login||'').trim().toLowerCase());
        check(account && input.password==='demonstracao','Use ti.demo ou colaborador.demo, com a senha demonstracao.');
        identity=account;
        try {sessionStore?.setItem(SESSION_KEY,account.id);} catch (_) {}
        return {ok:true};
      }
      check(identity,'Entre para continuar.');
      if (path==='logout') {
        identity=null;
        try {sessionStore?.removeItem(SESSION_KEY);} catch (_) {}
        return {ok:true};
      }
      const data=load();
      if(path==='profile')throw Error('O cadastro manual de e-mail foi removido.');
      if (path==='state') {
        const visible=data.assignments.filter(a=>identity.admin || a.person===identity.id);
        return clone({
          assignments:visible.map(a=>({...a,...data.assets.find(s=>s.id===a.asset),id:a.id,name:data.people.find(p=>p.id===a.person).name})),
          terms:data.terms.filter(t=>identity.admin||t.person===identity.id).map(t=>({...t,overdue:t.status==='pending'&&!!t.sign_due_at&&new Date(clock())>new Date(t.sign_due_at)})).slice().reverse(),
          assets:identity.admin?data.assets.map(s=>({...s,available:data.assignments.some(a=>a.asset===s.id&&!closed(a))?0:1})):[],
          people:identity.admin?data.people:[],
          mail:data.mail.filter(m=>identity.admin||m.person===identity.id).slice().reverse(),mail_mode:'simulation',
          requests:data.requests.filter(r=>identity.admin||r.person===identity.id).map(r=>{
            const a=data.assignments.find(a=>a.id===r.assignment), machine=data.assets.find(s=>s.id===a.asset);
            return {...r,tag:machine.tag,serial:machine.serial,asset:machine.id,model:machine.model,name:data.people.find(p=>p.id===a.person).name,assignment_status:a.status};
          }).slice().reverse(),
          history:data.history.filter(h=>visible.some(a=>a.id===h.assignment)).map(h=>{
            const a=data.assignments.find(a=>a.id===h.assignment), machine=data.assets.find(s=>s.id===a.asset);
            return {...h,tag:machine.tag,serial:machine.serial,asset:machine.id,model:machine.model,name:data.people.find(p=>p.id===a.person).name,actor_name:data.people.find(p=>p.id===h.actor)?.name||h.actor};
          }).slice().reverse()
        });
      }
      let id,issuedIds;
      if (path==='request-return') {
        const assignment=data.assignments.find(a=>a.id===+input.id);
        check(assignment?.person===identity.id,'Somente o responsável pode solicitar esta devolução.');
        check(['pending','active'].includes(assignment.status),'Este vínculo não permite uma nova solicitação.');
        check(!data.requests.some(r=>r.assignment===assignment.id&&['open','processing'].includes(r.status)),'Já existe uma solicitação para este equipamento.');
        const reason=String(input.reason||'').trim();
        check(reason.length>0&&reason.length<=2000,'Informe o motivo ou as observações da devolução.');
        id=nextId(data.requests);
        data.requests.push({id,assignment:assignment.id,person:identity.id,reason,created:clock(),status:'open',closed_at:null});
        history(data,assignment.id,'return_requested',reason);
        persist(data);
        return {ok:true,id};
      }
      if (path==='accept') {
        const term=data.terms.find(t=>t.id===+input.id);
        check(term,'Termo não encontrado.');
        check(term.person===identity.id,'Somente o responsável pode aceitar este termo.');
        check(term.status==='pending',term.status==='cancelled'?'Este termo foi cancelado pelo desvínculo.':'Este termo já foi aceito.');
        check(term.sign_due_at&&new Date(clock())<=new Date(term.sign_due_at),'O prazo de assinatura deste termo venceu. Contate a TI.');
        const assignment=data.assignments.find(a=>a.id===term.assignment);
        check(assignment && (term.kind==='devolucao'?assignment.status==='return_pending':assignment.status==='pending'),'O vínculo foi encerrado ou alterado. Atualize a página.');
        const name=String(input.name||'').trim();
        check(input.agree===true && name.toLocaleLowerCase()===identity.name.toLocaleLowerCase(),'Confirme a concordância e digite seu nome como exibido.');
        const accepted=clock();
        term.pdfData=root.btoa(makePdf(term,name,accepted));
        term.accepted=accepted;term.status='accepted';term.signer=name;
        assignment.status=term.kind==='devolucao'?'returned':'active';
        if(term.kind==='devolucao') {
          assignment.closed_at=accepted;assignment.closed_by=identity.id;
          data.requests.filter(r=>r.assignment===assignment.id&&['open','processing'].includes(r.status)).forEach(r=>{r.status='completed';r.closed_at=accepted;});
        }
        history(data,assignment.id,term.kind==='devolucao'?'return_accepted':'responsibility_accepted','Termo #'+term.id+' aceito por '+name+'.');
        id=term.id;
      } else {
        check(identity.admin,'Acesso reservado à TI.');
        if(path==='retry-email') {
          const term=data.terms.find(t=>t.id===+input.id);
          check(term?.status==='pending'&&term.sign_due_at&&new Date(clock())<=new Date(term.sign_due_at),'O termo não está disponível para uma nova solicitação.');
          invitation(data,term,term.sign_days);id=term.id;
        } else if (path==='assets') {
          const values={tag:String(input.tag||('EDNA-'+nextId(data.assets))).trim(),model:String(input.model||'').trim(),serial:String(input.serial||'').trim()||null,category:input.category??'notebook'};
          check(Object.hasOwn(CATEGORIES,values.category),'Selecione uma categoria válida de equipamento.');
          check([values.tag,values.model].every(v=>v.length>0&&v.length<=150),'Preencha o modelo (até 150 caracteres).');
          check((values.serial?.length||0)<=150,'O número de série deve ter até 150 caracteres.');
          check(values.serial||['mouse','teclado'].includes(values.category),'Informe o número de série para '+CATEGORIES[values.category]+'.');
          check(!data.assets.some(a=>a.tag.toLowerCase()===values.tag.toLowerCase()||values.serial&&a.serial?.toLowerCase()===values.serial.toLowerCase()),'Equipamento ou número de série já cadastrado.');
          id=nextId(data.assets);data.assets.push({...values,id});
        } else if (path==='assign') {
          const days=signingDays(input.sign_days??5);
          const items=input.items??(input.assets??[+input.asset]).map(asset=>({asset,person:input.person}));
          check(Array.isArray(items)&&items.length>=1&&items.length<=100,'Selecione de 1 a 100 equipamentos.');
          check(items.every(i=>i&&Number.isInteger(i.asset)&&data.people.some(p=>p.id===i.person)),'Seleção de equipamentos ou colaboradores inválida.');
          check(new Set(items.map(i=>i.asset)).size===items.length,'O mesmo equipamento não pode ser selecionado duas vezes.');
          check((input.quantity??items.length)===items.length,'A quantidade deve corresponder à seleção.');
          for(const item of items){
            const asset=data.assets.find(a=>a.id===item.asset);
            check(asset&&Object.hasOwn(CATEGORIES,asset.category),'Selecione um equipamento de categoria permitida.');
            check(!data.assignments.some(a=>a.asset===item.asset&&!closed(a)),'Equipamento já atribuído.');
          }
          check(['Fixa','Empréstimo'].includes(input.kind),'Modalidade inválida.');
          const notes=String(input.notes||'').trim();
          check(notes.length>0&&notes.length<=2000,'Informe as condições e acessórios.');
          let due=null;
          if (input.kind==='Empréstimo') {
            due=String(input.due||'');
            const today=new Date(clock()), value=new Date(due+'T12:00:00');
            today.setHours(0,0,0,0);
            check(/^\d{4}-\d{2}-\d{2}$/.test(due) && !isNaN(value) && value.toISOString().slice(0,10)===due && value>=today,'Informe uma data de devolução válida, de hoje em diante.');
          }
          issuedIds=[];
          for(const item of items){
            const assignment={id:nextId(data.assignments),asset:item.asset,person:item.person,kind:input.kind,due,notes,status:'pending'};
            data.assignments.push(assignment);
            issuedIds.push(newTerm(data,assignment,'responsabilidade',notes,days).id);
            history(data,assignment.id,'assigned',input.kind+' · '+notes);
          }
          id=issuedIds[0];
        } else if (path==='return') {
          const days=signingDays(input.sign_days??5);
          const assignment=data.assignments.find(a=>a.id===+input.id);
          check(assignment?.status==='active','A atribuição precisa estar em uso para iniciar a devolução.');
          const notes=String(input.notes||'').trim();
          check(input.received===true&&notes.length>0&&notes.length<=2000,'Confirme o recebimento físico e informe as condições.');
          id=newTerm(data,assignment,'devolucao',notes,days).id;
          assignment.status='return_pending';
          data.requests.filter(r=>r.assignment===assignment.id&&r.status==='open').forEach(r=>{r.status='processing';r.handled_at=clock();r.handled_by=identity.id;});
          history(data,assignment.id,'return_received',notes);
        } else if (path==='unlink') {
          const assignment=data.assignments.find(a=>a.id===+input.id);
          check(assignment&&!closed(assignment),'Este vínculo já está encerrado ou não existe.');
          const reason=String(input.reason||'').trim();
          check(input.confirm===true&&reason.length>0&&reason.length<=2000,'Confirme o desvínculo e informe o motivo.');
          assignment.status='detached';assignment.closed_at=clock();assignment.closed_by=identity.id;assignment.closure_reason=reason;
          data.terms.filter(t=>t.assignment===assignment.id&&t.status==='pending').forEach(t=>{t.status='cancelled';});
          data.mail.filter(m=>data.terms.some(t=>t.id===m.term&&t.assignment===assignment.id)&&m.status!=='sent').forEach(m=>{m.status='cancelled';});
          data.requests.filter(r=>r.assignment===assignment.id&&['open','processing'].includes(r.status)).forEach(r=>{r.status='cancelled';r.closed_at=clock();r.closed_by=identity.id;});
          history(data,assignment.id,'unlinked',reason);
          id=assignment.id;
        } else throw Error('Operação indisponível na demonstração.');
      }
      persist(data);
      return {ok:true,id,...(issuedIds?{ids:issuedIds,quantity:issuedIds.length}:{})};
    }
    return {request, storage:mode};
  }
  const exported={create};
  root.TermoDemo=exported;
  if (typeof module!=='undefined'&&module.exports) module.exports=exported;
})(globalThis);
