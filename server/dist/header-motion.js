/* Rolagem leve: a foto cede lugar à mascote no centro do cabeçalho. */
(()=>{
  'use strict';
  const root=document.documentElement,header=document.querySelector('.topbar'),app=document.querySelector('#app');
  if(!header||!app)return;
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  let frame=0,current=0,target=0,measure=true;
  const clamp=n=>Math.max(0,Math.min(1,n));
  function update(){
    frame=0;
    if(measure){
      const y=Math.max(0,window.scrollY||0),hero=document.querySelector('.welcome-banner-art, .login-operation');
      const end=hero?Math.max(150,hero.getBoundingClientRect().bottom+y-header.getBoundingClientRect().height):180;
      target=clamp((y-16)/Math.max(1,end-16));
      if(reduced.matches)target=target>=.65?1:0;
      measure=false;
    }
    current=reduced.matches?target:current+(target-current)*.24;
    if(Math.abs(target-current)<.001)current=target;
    root.style.setProperty('--edna-progress',current.toFixed(4));
    root.style.setProperty('--edna-portrait-opacity',clamp((current-.18)/.82).toFixed(4));
    root.style.setProperty('--edna-name-opacity',(1-clamp(current*2.8)).toFixed(4));
    header.classList.toggle('is-scrolled',current>.12);
    if(current!==target)frame=requestAnimationFrame(update);
  }
  function schedule(){measure=true;if(!frame)frame=requestAnimationFrame(update)}
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',schedule,{passive:true});
  window.addEventListener('pageshow',schedule);
  reduced.addEventListener?.('change',schedule);
  new MutationObserver(schedule).observe(app,{childList:true});
  schedule();
})();
