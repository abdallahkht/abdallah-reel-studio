const examples=[
{id:'adobe',title:'Adobe · النسخة الأولى',description:'المونتاج الأصلي الذي شاركه عبدالله.',src:'examples/silent/adobe.mp4',poster:'examples/adobe/after.jpg'},
{id:'meta-ads',title:'Meta Ads · Claude',src:'examples/silent/meta-ads.mp4',poster:'examples/meta-ads-claude.jpg'},
{id:'dots',title:'Dots · Muse · Grok',description:'مثال آخر من ريلز عبدالله.',src:'examples/silent/dots.mp4',poster:'examples/dots-muse-grok.jpg'},
{id:'find-skills',title:'Find Skills · النسخة الأولى',src:'examples/silent/find-skills.mp4',poster:'examples/find-skills.jpg'},
{id:'find-skills-alternative',title:'Find Skills · ستايل جديد',src:'examples/silent/find-skills-corrected.mp4',poster:'examples/find-skills-corrected.jpg'},
{id:'seven-ways-roi',title:'7 Ways + ROI · OS',src:'examples/silent/seven-ways-roi.mp4',poster:'examples/seven-ways-roi.jpg'}];
const raw={id:'before',title:'Adobe · قبل الموشن والكابشن',src:'examples/silent/before.mp4'};
const gallery=document.querySelector('#gallery');
const dialog=document.querySelector('#video-dialog');
const video=document.querySelector('#demo-video');
const hero=document.querySelector('#hero-video');
const reduceMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
const visiblePlayers=new Set();
function playVisible(){
  if(reduceMotion||dialog.open||document.hidden)return;
  for(const player of visiblePlayers)player.play().catch(()=>{});
}
function show(item){
  hero.pause();
  for(const player of gallery.querySelectorAll('video'))player.pause();
  document.querySelector('#video-title').textContent=item.title;
  video.muted=true;video.defaultMuted=true;video.src=item.src;
  dialog.showModal();video.play().catch(()=>{});
}
const observer=new IntersectionObserver(entries=>{
  for(const entry of entries){
    const player=entry.target;
    if(entry.isIntersecting)visiblePlayers.add(player);
    else{visiblePlayers.delete(player);player.pause();}
  }
  playVisible();
},{threshold:0.15});
for(const item of examples){
  const card=document.createElement('article');card.className='demo-card';card.id=item.id;
  card.innerHTML=`<button class="preview-button" type="button" aria-label="${item.title}"><span class="poster-wrap"><video muted loop playsinline preload="metadata" poster="${item.poster}" aria-hidden="true" tabindex="-1"><source src="${item.src}" type="video/mp4"></video></span></button><h3>${item.title}</h3>`;
  card.querySelector('button').addEventListener('click',()=>show(item));
  gallery.append(card);observer.observe(card.querySelector('video'));
}
document.querySelector('#close-video').onclick=()=>dialog.close();
dialog.addEventListener('close',()=>{video.pause();playVisible();});
dialog.addEventListener('click',event=>{
  if(event.target!==dialog)return;
  const r=dialog.getBoundingClientRect();
  if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();
});
document.addEventListener('visibilitychange',()=>{
  if(document.hidden){for(const player of visiblePlayers)player.pause();video.pause();}
  else playVisible();
});
const selected=new URLSearchParams(location.search).get('demo');
const chosen=[...examples,raw].find(item=>item.id===(selected==='alternative'?'meta-ads':selected));
if(chosen)show(chosen);
