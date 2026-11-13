const examples=[
{id:'adobe',title:'Adobe · النسخة الأولى',description:'المونتاج الأصلي الذي شاركه عبدالله.',src:'examples/adobe/after.mp4',poster:'examples/adobe/after.jpg'},
{id:'meta-ads',title:'Meta Ads · Claude',src:'examples/meta-ads-claude.mp4',poster:'examples/meta-ads-claude.jpg'},
{id:'dots',title:'Dots · Muse · Grok',description:'مثال آخر من ريلز عبدالله.',src:'examples/dots-muse-grok.mp4',poster:'examples/dots-muse-grok.jpg'},
{id:'find-skills',title:'Find Skills · النسخة الأولى',src:'examples/find-skills.mp4',poster:'examples/find-skills.jpg'},
{id:'find-skills-alternative',title:'Find Skills · ستايل جديد',src:'examples/find-skills-alternative-v2.mp4',poster:'examples/find-skills-alternative.jpg'},
{id:'seven-ways-roi',title:'7 Ways + ROI · OS',src:'examples/seven-ways-roi.mp4',poster:'examples/seven-ways-roi.jpg'}];
const raw={id:'before',title:'Adobe · قبل الموشن والكابشن',src:'examples/adobe/before.mp4'};
const gallery=document.querySelector('#gallery'),dialog=document.querySelector('#video-dialog'),video=document.querySelector('#demo-video');
function show(item){document.querySelector('#video-title').textContent=item.title;video.muted=true;video.defaultMuted=true;video.src=item.src;dialog.showModal();video.play().catch(()=>{});}
for(const item of examples){const card=document.createElement('article');card.className='demo-card';card.id=item.id;card.innerHTML=`<div class="poster-wrap"><video controls muted playsinline preload="none" poster="${item.poster}" aria-label="${item.title}"><source src="${item.src}" type="video/mp4"></video></div><h3>${item.title}</h3>`;gallery.append(card);}
gallery.addEventListener('play',event=>{document.querySelector('#hero-video').pause();for(const other of gallery.querySelectorAll('video'))if(other!==event.target)other.pause();},true);
document.querySelector('#close-video').onclick=()=>dialog.close();dialog.addEventListener('close',()=>video.pause());dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
const selected=new URLSearchParams(location.search).get('demo');const chosen=[...examples,raw].find(item=>item.id===(selected==='alternative'?'meta-ads':selected));if(chosen)show(chosen);
const hero=document.querySelector('#hero-video');
hero.addEventListener('play',()=>{for(const player of gallery.querySelectorAll('video'))player.pause();video.pause();});
