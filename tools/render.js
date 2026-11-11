// Renders feed (1080x1440) and story (1080x1920) images + captions for each question.
const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
const qs=JSON.parse(fs.readFileSync(process.argv[2]||'questions.json','utf8'));
const out=process.argv[3]||'out';fs.mkdirSync(out+'/feed',{recursive:true});fs.mkdirSync(out+'/story',{recursive:true});
const LOGO='<svg viewBox="0 0 40 40"><circle cx="17" cy="17" r="13" fill="none" stroke="#FFC93C" stroke-width="5"/><path d="M17 9v9h6" stroke="#FFC93C" stroke-width="3.5" fill="none" stroke-linecap="round"/><path d="M26 26l8 8" stroke="#FFC93C" stroke-width="5" stroke-linecap="round"/></svg>';
const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;');
function label(slot){const [d,t]=slot.split(' ');let h=+t.slice(0,2);const ap=h>=12?'PM':'AM';h=h%12||12;
 const dt=new Date(d+'T00:00:00');return {time:`${h} ${ap}`,day:dt.toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short'})};}
function drawNote(slot){const [d,t]=slot.split(' ');const h=+t.slice(0,2);
 const dd=new Date(d+'T00:00:00Z');if(h>=22)dd.setUTCDate(dd.getUTCDate()+1);
 const same=h<22; const name=dd.toLocaleDateString('en-IN',{day:'numeric',month:'short',timeZone:'UTC'});
 return {short: h<22?'tonight':'tomorrow', date:name};}
function html(q,i,W,H){const L=label(q.slot);const story=H>1500;const qlen=q.q.length;
 const qs=story?(qlen>80?66:76):(qlen>90?56:qlen>65?64:72);
 return `<!doctype html><html><head><link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet"><style>
*{box-sizing:border-box;margin:0;padding:0}body{width:${W}px;height:${H}px;background:#14123A;color:#fff;font-family:'DM Sans',Inter,sans-serif;padding:${story?'150px 80px 120px':H<1400?'64px 80px':'80px'};display:flex;flex-direction:column}
.top{display:flex;justify-content:space-between;align-items:center}.eb{color:#FFC93C;font-weight:700;letter-spacing:.14em;font-size:30px;text-transform:uppercase}
.logo{display:flex;align-items:center;gap:14px;font-family:'Bricolage Grotesque';font-weight:800;font-size:40px;letter-spacing:-.02em}.logo svg{width:50px;height:50px}.logo b{color:#FFC93C}
.meta{margin-top:${story?70:50}px;display:flex;gap:14px}.chip{background:#24215A;color:#C9C6F2;font-size:26px;font-weight:500;padding:10px 22px;border-radius:99px}.chip.y{background:#FFC93C;color:#14123A;font-weight:700}
h1{font-family:'Bricolage Grotesque';font-weight:800;font-size:${qs}px;line-height:1.08;letter-spacing:-.025em;margin:${story?50:34}px 0 ${story?60:40}px}
.opts{display:flex;flex-direction:column;gap:${story?26:20}px}.o{background:#24215A;border-radius:24px;padding:${story?30:24}px 30px;display:flex;align-items:center;gap:28px;font-size:${story?42:38}px;font-weight:500}
.o span{flex:none;width:${story?70:64}px;height:${story?70:64}px;border-radius:50%;background:#FFC93C;color:#14123A;font-family:'Bricolage Grotesque';font-weight:800;font-size:${story?38:34}px;display:flex;align-items:center;justify-content:center}
.foot{margin-top:auto;border-top:2px solid #3A3680;padding-top:28px}.cta{font-size:${story?36:32}px;font-weight:700}.cta b{color:#FFC93C}.small{color:#C9C6F2;font-size:${story?24:22}px;margin-top:12px;line-height:1.4}
</style></head><body><div class="top"><div class="eb">Question · ${L.time}</div><div class="logo">${LOGO}<div>qwinn <b>live</b></div></div></div>
<div class="meta"><div class="chip y">${esc(q.topic)}</div><div class="chip">${L.day}</div></div>
<h1>${esc(q.q)}</h1><div class="opts">${q.o.map((o,k)=>`<div class="o"><span>${'ABCD'[k]}</span>${esc(o)}</div>`).join('')}</div>
<div class="foot"><div class="cta">${story?'Answer <b>A, B, C or D</b> in the comments on our latest post':'Comment <b>A, B, C or D</b> · ₹100 winner at 10 PM'}</div><div class="small">Free to enter. We never ask for money, OTPs or passwords. @qwinnlive<br>Not sponsored, endorsed or administered by, or associated with, Instagram or Meta.</div></div></body></html>`;}
// Weekly extras, matching config.json "tag_bonus" (Wednesdays from 18 Nov) and "mega_draw" (Fridays from 20 Nov).
function extras(slot){const d=new Date(slot.split(' ')[0]+'T00:00:00Z');const iso=slot.slice(0,10);let x='';
 if(d.getUTCDay()===3&&iso>='2026-11-18')x+='\n👯 Tag-a-friend day: tag a friend in your answer comment for a bonus entry (one bonus per post).';
 if(iso>='2026-11-15')x+='\n🏆 Friday mega draw: a ₹200 gift card. Every correct answer from Saturday to Friday is an entry.';
 return x;}
function caption(q){const L=label(q.slot);const d=drawNote(q.slot);
 return `⏰ ${L.time} question | ${q.topic}

💬 Comment your answer: A, B, C or D (one answer per person; your first comment counts).
🎁 Every correct answer is one entry in the ₹100 gift card draw at 10 PM IST ${d.short} (${d.date}). A winner every night!${extras(q.slot)}

${q.tags.join(' ')}`;}
(async()=>{const b=await chromium.launch();const p=await b.newPage();let caps=[],csv=['file,slot_ist,slot_utc,topic,question,correct,correct_text'];
 for(const [i,q] of qs.entries()){const n=String(i+1).padStart(2,'0');const stamp=q.slot.replace(/[-: ]/g,'').slice(0,10);const base=`${n}-${stamp}`;
  for(const [kind,W,H] of (process.env.KINDS==='api'?[['api',1080,1350]]:[['feed',1080,1440],['story',1080,1920]])){await p.setViewportSize({width:W,height:H});await p.setContent(html(q,i,W,H),{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);
   if(kind==='api'){const [d,t]=q.slot.split(' ');fs.mkdirSync(`${out}/posts/${d}`,{recursive:true});await p.screenshot({path:`${out}/posts/${d}/${t.slice(0,2)}.jpg`,type:'jpeg',quality:92});fs.writeFileSync(`${out}/posts/${d}/${t.slice(0,2)}.txt`,caption(q));}else await p.screenshot({path:`${out}/${kind}/${base}.png`});}
  const utc=new Date(q.slot.replace(' ','T')+':00+05:30').toISOString().slice(0,16).replace('T',' ');
  caps.push(`## ${n}. ${label(q.slot).day}, ${label(q.slot).time} IST  (image: feed/${base}.png)\nAnswer: ${q.a}) ${q.o['ABCD'.indexOf(q.a)]}\n\n\`\`\`\n${caption(q)}\n\`\`\`\n`);
  csv.push([`${base}.png`,q.slot,utc,q.topic,JSON.stringify(q.q),q.a,JSON.stringify(q.o['ABCD'.indexOf(q.a)])].join(','));
  fs.writeFileSync(`${out}/feed/${base}.txt`,caption(q));}
 fs.writeFileSync(`${out}/captions.md`,'# Qwinn Live: captions for each hourly post\n\nCopy the text in each box as the post caption. The answer line is for you only: do not post it.\n\n'+caps.join('\n'));
 fs.writeFileSync(`${out}/schedule.csv`,csv.join('\n')+'\n');await b.close();console.log('done',qs.length);})();
