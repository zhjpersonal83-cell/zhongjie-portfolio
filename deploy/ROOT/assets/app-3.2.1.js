
document.documentElement.classList.add('js');
(() => {
  const root = document.documentElement;
  const saved = localStorage.getItem('portfolio-theme');
  const preferredDark = matchMedia('(prefers-color-scheme: dark)').matches;
  root.dataset.theme = saved || (preferredDark ? 'dark' : 'light');
  document.querySelectorAll('[data-theme-toggle]').forEach(btn => btn.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('portfolio-theme', root.dataset.theme);
    btn.setAttribute('aria-label', root.dataset.theme === 'dark' ? 'Use light theme' : 'Use dark theme');
  }));

  const menuBtn = document.querySelector('[data-menu-button]');
  const nav = document.querySelector('[data-nav-links]');
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', String(open));
    });
    nav.addEventListener('click', e => { if (e.target.closest('a')) { nav.classList.remove('open'); menuBtn.setAttribute('aria-expanded','false'); } });
  }

  const updateProgress = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    root.style.setProperty('--progress', `${max > 0 ? (scrollY / max) * 100 : 0}%`);
  };
  addEventListener('scroll', updateProgress, {passive:true}); updateProgress();

  const finePointer = matchMedia('(pointer:fine)').matches;
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const revealItems = [...document.querySelectorAll('[data-reveal]')];
  if ('IntersectionObserver' in window && !reduceMotion && revealItems.length) {
    root.classList.add('reveal-enabled');
    const reveal = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        reveal.unobserve(entry.target);
      }
    }), {threshold:.01, rootMargin:'0px 0px -3% 0px'});
    revealItems.forEach(el => reveal.observe(el));
    // Fail-safe: content must never remain invisible because of browser timing or restored scroll position.
    setTimeout(() => revealItems.forEach(el => el.classList.add('visible')), 1400);
  } else {
    revealItems.forEach(el => el.classList.add('visible'));
  }
  if (finePointer && !reduceMotion) {
    const glow = document.querySelector('.cursor-glow');
    addEventListener('pointermove', e => { if(glow){ glow.style.left=`${e.clientX}px`; glow.style.top=`${e.clientY}px`; } }, {passive:true});
    document.querySelectorAll('[data-tilt]').forEach(card => {
      card.addEventListener('pointermove', e => {
        const r=card.getBoundingClientRect(), x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5;
        card.style.transform=`perspective(900px) rotateX(${-y*4}deg) rotateY(${x*4}deg) translateY(-3px)`;
      });
      card.addEventListener('pointerleave',()=>card.style.transform='');
    });
  }

  document.querySelectorAll('[data-copy]').forEach(btn => btn.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(btn.dataset.copy); const old=btn.textContent; btn.textContent=btn.dataset.copied || 'Copied'; setTimeout(()=>btn.textContent=old,1600); }
    catch { location.href=`mailto:${btn.dataset.copy}`; }
  }));

  const dialog = document.querySelector('[data-command-dialog]');
  const openDialog = () => { if(dialog){ dialog.showModal(); dialog.querySelector('input')?.focus(); } };
  document.querySelectorAll('[data-command-open]').forEach(btn => btn.addEventListener('click', openDialog));
  addEventListener('keydown', e => { if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openDialog()} if(e.key==='Escape'&&dialog?.open)dialog.close(); });
  if(dialog){
    dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});
    const search=dialog.querySelector('input');
    search?.addEventListener('input',()=>{const q=search.value.toLowerCase();dialog.querySelectorAll('li').forEach(li=>li.hidden=!li.textContent.toLowerCase().includes(q));});
  }

  const moduleCards=[...document.querySelectorAll('[data-module]')];
  if(moduleCards.length){
    const q=document.querySelector('#module-search'), programme=document.querySelector('#programme-filter'), level=document.querySelector('#level-filter'), area=document.querySelector('#area-filter'), empty=document.querySelector('#module-empty'), count=document.querySelector('#module-count'), reset=document.querySelector('#module-reset');
    const normalise=value=>String(value||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/&/g,' and ').replace(/[^a-z0-9\u3400-\u9fff]+/g,' ').trim().replace(/\s+/g,' ');
    const aliases={
      ai:['artificial intelligence','adaptive intelligence'],ml:['machine learning','adaptive intelligence'],nlp:['text processing','language technology','natural language'],gpu:['graphical processing units','parallel computing'],cs:['computer science','software engineering'],
      data:['data science','data statistics','python'],security:['cybersecurity','computer misuse'],web:['web engineering','html','css','javascript'],mobile:['mobile engineering','android'],robot:['robotics'],systems:['distributed systems','operating systems'],
      '人工智能':['artificial intelligence','adaptive intelligence'],'机器学习':['machine learning','adaptive intelligence'],'自然语言':['text processing','language technology'],'数据':['data science','data statistics','python'],'安全':['cybersecurity','computer misuse'],'网页':['web engineering','html','css','javascript'],'软件':['software engineering','programming'],'机器人':['robotics'],'系统':['systems','distributed systems','operating systems'],'项目':['project','professional practice']
    };
    const indexFor=card=>normalise([card.textContent,card.dataset.programme,card.dataset.level,card.dataset.area].join(' '));
    moduleCards.forEach(card=>card.dataset.searchIndex=indexFor(card));
    const matchesTerm=(index,term)=>{
      const phrase=normalise(term); if(!phrase)return true;
      const tokens=phrase.split(' ').filter(Boolean);
      return tokens.every(token=>[token,...(aliases[token]||[])].some(candidate=>index.includes(normalise(candidate))));
    };
    const params=new URLSearchParams(location.search);
    if(q&&params.has('q'))q.value=params.get('q')||'';
    if(programme&&params.has('programme'))programme.value=params.get('programme')||'';
    if(level&&params.has('level'))level.value=params.get('level')||'';
    if(area&&params.has('area'))area.value=params.get('area')||'';
    const filter=()=>{
      const selectedProgramme=programme?.value||'', selectedLevel=level?.value||'', selectedArea=area?.value||'', term=q?.value||''; let visible=0;
      moduleCards.forEach(card=>{
        const ok=matchesTerm(card.dataset.searchIndex,term)&&(!selectedProgramme||card.dataset.programme===selectedProgramme)&&(!selectedLevel||card.dataset.level===selectedLevel)&&(!selectedArea||card.dataset.area===selectedArea);
        card.hidden=!ok; card.setAttribute('aria-hidden',String(!ok)); if(ok)visible++;
      });
      if(empty)empty.style.display=visible?'none':'block'; if(count)count.textContent=String(visible);
      const active=Boolean(term.trim()||selectedProgramme||selectedLevel||selectedArea); if(reset)reset.hidden=!active;
      const next=new URLSearchParams(); if(term.trim())next.set('q',term.trim()); if(selectedProgramme)next.set('programme',selectedProgramme); if(selectedLevel)next.set('level',selectedLevel); if(selectedArea)next.set('area',selectedArea);
      history.replaceState(null,'',`${location.pathname}${next.size?`?${next}`:''}${location.hash}`);
    };
    [q,programme,level,area].forEach(el=>el?.addEventListener(el.tagName==='INPUT'?'input':'change',filter));
    q?.addEventListener('keydown',event=>{if(event.key==='Escape'&&q.value){q.value='';filter();}});
    reset?.addEventListener('click',()=>{if(q)q.value='';if(programme)programme.value='';if(level)level.value='';if(area)area.value='';filter();q?.focus();});
    filter();
  }

  document.querySelectorAll('[role=tablist]').forEach(tablist => {
    const tabs=[...tablist.querySelectorAll('[role=tab]')];
    tabs.forEach(tab=>tab.addEventListener('click',()=>{
      tabs.forEach(t=>t.setAttribute('aria-selected','false')); tab.setAttribute('aria-selected','true');
      const wrap=tablist.parentElement; wrap.querySelectorAll('[role=tabpanel]').forEach(p=>p.hidden=p.id!==tab.getAttribute('aria-controls'));
    }));
  });

  // Lightweight decorative network; core content never depends on it.
  const canvas=document.querySelector('.network-canvas');
  if(canvas && !reduceMotion){
    const ctx=canvas.getContext('2d'); let points=[],raf;
    const resize=()=>{const d=Math.min(devicePixelRatio,2);canvas.width=canvas.clientWidth*d;canvas.height=canvas.clientHeight*d;ctx.setTransform(d,0,0,d,0,0);const n=Math.min(65,Math.max(24,Math.floor(canvas.clientWidth/22)));points=Array.from({length:n},()=>({x:Math.random()*canvas.clientWidth,y:Math.random()*canvas.clientHeight,vx:(Math.random()-.5)*.18,vy:(Math.random()-.5)*.18}));};
    const draw=()=>{ctx.clearRect(0,0,canvas.clientWidth,canvas.clientHeight);const color=getComputedStyle(root).getPropertyValue('--accent-2').trim();points.forEach((p,i)=>{p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>canvas.clientWidth)p.vx*=-1;if(p.y<0||p.y>canvas.clientHeight)p.vy*=-1;ctx.fillStyle=color;ctx.globalAlpha=.45;ctx.beginPath();ctx.arc(p.x,p.y,1.4,0,Math.PI*2);ctx.fill();for(let j=i+1;j<points.length;j++){const b=points[j],dx=p.x-b.x,dy=p.y-b.y,dist=Math.hypot(dx,dy);if(dist<105){ctx.globalAlpha=(1-dist/105)*.2;ctx.strokeStyle=color;ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(b.x,b.y);ctx.stroke();}}});ctx.globalAlpha=1;raf=requestAnimationFrame(draw)};
    new ResizeObserver(resize).observe(canvas); resize(); draw(); document.addEventListener('visibilitychange',()=>{if(document.hidden)cancelAnimationFrame(raf);else draw()});
  }
})();
