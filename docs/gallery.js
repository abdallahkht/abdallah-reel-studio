const examples=[
{id:'adobe',title:'Adobe · النسخة الأولى',description:'المونتاج الأصلي الذي شاركه عبدالله.',src:'examples/adobe/after.mp4',poster:'examples/adobe/after.jpg'},
{id:'alternative',title:'Adobe · ستايل مختلف',description:'نفس الكلام، بموشن أبيض وأزرق وشرح بصري جديد.',src:'examples/adobe/alternative.mp4',poster:'examples/adobe/alternative.jpg'},
{id:'dots',title:'Dots · Muse · Grok',description:'مثال آخر من ريلز عبدالله.',src:'examples/dots-muse-grok.mp4',poster:'examples/dots-muse-grok.jpg'}];
const raw={id:'before',title:'Adobe · قبل الموشن والكابشن',src:'examples/adobe/before.mp4'};
const gallery=document.querySelector('#gallery'),dialog=document.querySelector('#video-dialog'),video=document.querySelector('#demo-video');
function show(item){document.querySelector('#video-title').textContent=item.title;video.src=item.src;document.querySelector('#template-link').href=item.src;dialog.showModal();video.play().catch(()=>{});}
for(const item of examples){const card=document.createElement('button');card.className='demo-card';card.innerHTML=`<div class="poster-wrap"><img src="${item.poster}" alt="" loading="lazy"><span class="play-icon" aria-hidden="true">▶</span></div><h3>${item.title}</h3><p>${item.description}</p>`;card.setAttribute('aria-label',`شاهد: ${item.title}`);card.onclick=()=>show(item);gallery.append(card);}
document.querySelector('#close-video').onclick=()=>dialog.close();dialog.addEventListener('close',()=>video.pause());dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
const selected=new URLSearchParams(location.search).get('demo');const chosen=[...examples,raw].find(item=>item.id===selected);if(chosen)show(chosen);
const hero=document.querySelector('#hero-video'),toggle=document.querySelector('#hero-toggle');
function label(){toggle.textContent=hero.paused?'تشغيل المعاينة':'إيقاف المعاينة';toggle.setAttribute('aria-label',toggle.textContent);}
hero.addEventListener('play',label);hero.addEventListener('pause',label);toggle.onclick=()=>hero.paused?hero.play().catch(label):hero.pause();
if(!matchMedia('(prefers-reduced-motion: reduce)').matches)hero.play().catch(label);label();
