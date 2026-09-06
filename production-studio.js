(function(){
'use strict';
const $=id=>document.getElementById(id);
const FAMILY_BY_PRODUCT={hoodie:'machine_static',beanie:'ghost_hound',cargo:'broken_human',mask:'machine_static',shirt:'error_garden'};
let template=null,mappings={},selectedPanel=null,currentTile=null,shortlist=[],lastManifest=null,renderQueued=false;

function config(){return{family:$('family').value,seed:+$('seed').value,scale:+$('scale').value,density:+$('density').value,distress:+$('distress').value};}
function stable(value){if(Array.isArray(value))return value.map(stable);if(value&&typeof value==='object'){const out={};Object.keys(value).sort().forEach(k=>out[k]=stable(value[k]));return out;}return value;}
function stableJSON(value){return JSON.stringify(stable(value));}
async function sha256Bytes(bytes){const digest=await crypto.subtle.digest('SHA-256',bytes);return [...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,'0')).join('');}
async function sha256Text(text){return sha256Bytes(new TextEncoder().encode(text));}
function downloadBlob(blob,name){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
function canvasBlob(canvas,type='image/png'){return new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('Canvas export failed')),type));}
function makeTile(size,cfg=config()){
  const c=document.createElement('canvas');c.width=c.height=size;
  const ctx=c.getContext('2d');
  const params={patternType:cfg.family,patternScale:cfg.scale,colorVariance:cfg.density,edgeIntensity:cfg.distress,symmetry:0,seed:cfg.seed};
  const palette=colorPalettes[cfg.family==='error_garden'?'error_garden':'rac_reference'];
  const generator=patternGenerators[cfg.family];
  if(!generator)throw new Error('Missing design family '+cfg.family);
  generator(ctx,size,params,palette,seededRandom(cfg.seed));
  return c;
}
function syncValues(){['seed','scale','density','distress','offsetX','offsetY','panelScale','rotation'].forEach(id=>{const e=$(id+'Value');if(e&&$(id))e.textContent=$(id).value;});}
function status(text,kind=''){const e=$('productionStatus');e.textContent=text;e.className='status'+(kind?' '+kind:'');}

function validateTemplate(t){
  const errors=[];
  if(!t||typeof t!=='object')return['Template must be a JSON object'];
  if(t.schema_version!=='1.0')errors.push('schema_version must be 1.0');
  for(const k of ['provider','product_id','template_version'])if(typeof t[k]!=='string'||!t[k].trim())errors.push(k+' is required');
  if(t.units!=='px')errors.push('units must be px');
  if(!Number.isFinite(+t.dpi)||+t.dpi<=0)errors.push('dpi must be positive');
  if(!t.canvas||!Number.isInteger(t.canvas.width)||!Number.isInteger(t.canvas.height)||t.canvas.width<1||t.canvas.height<1)errors.push('canvas width/height must be positive integers');
  if(t.canvas&&(t.canvas.width>50000||t.canvas.height>50000))errors.push('canvas dimensions exceed safety limit');
  if(!Array.isArray(t.panels)||!t.panels.length)errors.push('at least one panel is required');
  if(Array.isArray(t.panels)&&t.panels.length>32)errors.push('panel count exceeds safety limit (32)');
  const ids=new Set();
  (t.panels||[]).forEach((p,i)=>{
    if(!p||typeof p!=='object'){errors.push('panel '+i+' invalid');return;}
    if(!/^[a-z0-9_-]+$/.test(p.id||''))errors.push('panel '+i+' has invalid id');
    if(ids.has(p.id))errors.push('duplicate panel id '+p.id);ids.add(p.id);
    for(const k of ['x','y','width','height'])if(!Number.isInteger(p[k])||p[k]<(k==='width'||k==='height'?1:0))errors.push(`${p.id||i}.${k} invalid`);
    if(Number.isInteger(p.width)&&Number.isInteger(p.height)&&p.width*p.height>50000000)errors.push(`${p.id||i} exceeds 50M-pixel export safety limit`);
    if(t.canvas&&Number.isInteger(p.x)&&Number.isInteger(p.y)&&Number.isInteger(p.width)&&Number.isInteger(p.height)&&(p.x+p.width>t.canvas.width||p.y+p.height>t.canvas.height))errors.push(`${p.id||i} exceeds template canvas bounds`);
  });
  (t.seams||[]).forEach((s,i)=>{if(!ids.has(s.a)||!ids.has(s.b))errors.push('seam '+i+' references missing panel');if(!['top','right','bottom','left'].includes(s.edge_a)||!['top','right','bottom','left'].includes(s.edge_b))errors.push('seam '+i+' has invalid edge');});
  return errors;
}
function claimsVendorReady(){return !!(template&&template.vendor_ready===true&&String(template.provider).toUpperCase()!=='GENERIC_PREVIEW');}
function setTemplate(t,origin='builtin'){
  const errors=validateTemplate(t);if(errors.length){status('TEMPLATE ERROR · '+errors[0],'error');throw new Error(errors.join('; '));}
  template=JSON.parse(JSON.stringify(t));template.__origin=origin;
  mappings={};for(const p of template.panels)mappings[p.id]={offsetX:0,offsetY:0,scale:100,rotation:Number(p.rotation||0)};
  selectedPanel=template.panels[0].id;
  renderTemplateMeta();renderPanelList();loadSelectedControls();renderAll();
}
function renderTemplateMeta(){
  const meta=$('templateMeta');if(!template){meta.innerHTML='';return;}
  const rows=[['Provider',template.provider],['Product',template.product_name||template.product_id],['Version',template.template_version],['Canvas',`${template.canvas.width}×${template.canvas.height}px`],['DPI',template.dpi],['Panels',template.panels.length],['Status',claimsVendorReady()?'vendor-ready claim / imported':'draft / normalized']];
  meta.innerHTML=rows.map(([a,b])=>`<div>${esc(a)}</div><div>${esc(String(b))}</div>`).join('');
}
function esc(s){return String(s).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
function renderPanelList(){
  const list=$('panelList');list.innerHTML='';
  for(const p of template.panels){const row=document.createElement('div');row.className='panel-row'+(p.id===selectedPanel?' active':'');row.dataset.panelId=p.id;row.innerHTML=`<span><strong>${esc(p.label)}</strong><br><small>${p.width}×${p.height}px · ${esc(p.continuity_group||'independent')}</small></span><span>${p.required===false?'optional':'required'}</span>`;row.onclick=()=>{selectedPanel=p.id;renderPanelList();loadSelectedControls();renderAll();};list.appendChild(row);}
}
function loadSelectedControls(){const m=mappings[selectedPanel];if(!m)return;for(const [id,key] of [['offsetX','offsetX'],['offsetY','offsetY'],['panelScale','scale'],['rotation','rotation']])$(id).value=m[key];syncValues();}
function saveSelectedControls(){const m=mappings[selectedPanel];if(!m)return;m.offsetX=+$('offsetX').value;m.offsetY=+$('offsetY').value;m.scale=+$('panelScale').value;m.rotation=+$('rotation').value;}

function tilePanel(ctx,tile,p,view,m,drawLabels=true){
  const x=view.x+p.x*view.fit,y=view.y+p.y*view.fit,w=p.width*view.fit,h=p.height*view.fit;
  ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();
  ctx.fillStyle='#111';ctx.fillRect(x,y,w,h);
  const cx=x+w/2,cy=y+h/2;ctx.translate(cx,cy);ctx.rotate(m.rotation*Math.PI/180);ctx.translate(-cx,-cy);
  const tileSize=Math.max(12,512*(m.scale/100)*view.fit);
  const ox=(m.offsetX%Math.max(1,512))*view.fit,oy=(m.offsetY%Math.max(1,512))*view.fit;
  const startX=x-tileSize*3+ox,startY=y-tileSize*3+oy;
  for(let yy=startY;yy<y+h+tileSize*3;yy+=tileSize)for(let xx=startX;xx<x+w+tileSize*3;xx+=tileSize)ctx.drawImage(tile,xx,yy,tileSize,tileSize);
  ctx.restore();
  if(drawLabels){ctx.save();ctx.strokeStyle=p.id===selectedPanel?'#3478f6':'rgba(20,20,20,.7)';ctx.lineWidth=p.id===selectedPanel?3:1.2;ctx.strokeRect(x,y,w,h);const bleed=Number(p.bleed||0)*view.fit;if(bleed>0){ctx.setLineDash([5,4]);ctx.strokeStyle='rgba(255,100,100,.8)';ctx.strokeRect(x+bleed,y+bleed,w-2*bleed,h-2*bleed);}const safe=Number(p.safe_margin||0)*view.fit;if(safe>0){ctx.setLineDash([4,4]);ctx.strokeStyle='rgba(60,207,145,.85)';ctx.strokeRect(x+safe,y+safe,w-2*safe,h-2*safe);}ctx.setLineDash([]);ctx.fillStyle='rgba(244,241,235,.9)';ctx.fillRect(x+6,y+6,Math.min(w-12,160),27);ctx.fillStyle='#111';ctx.font='700 11px monospace';ctx.fillText(p.label.toUpperCase(),x+12,y+23);ctx.restore();}
}
function renderMap(){
  if(!template)return;currentTile=makeTile(512);
  const c=$('panelMap'),ctx=c.getContext('2d'),margin=34;
  ctx.fillStyle='#f4f1eb';ctx.fillRect(0,0,c.width,c.height);
  const fit=Math.min((c.width-margin*2)/template.canvas.width,(c.height-margin*2)/template.canvas.height);const view={fit,x:(c.width-template.canvas.width*fit)/2,y:(c.height-template.canvas.height*fit)/2};
  ctx.strokeStyle='#b8b2a7';ctx.lineWidth=1;ctx.strokeRect(view.x,view.y,template.canvas.width*fit,template.canvas.height*fit);
  for(const p of template.panels)tilePanel(ctx,currentTile,p,view,mappings[p.id]);
  ctx.fillStyle='#272727';ctx.font='700 13px monospace';ctx.fillText(`${template.provider} / ${template.product_id} / ${template.template_version}`,margin,22);
  ctx.fillStyle='#6a645a';ctx.font='11px monospace';ctx.fillText(claimsVendorReady()?'IMPORTED TEMPLATE · VENDOR-READY CLAIM':'GENERIC PREVIEW · NOT VENDOR PRODUCTION GEOMETRY',margin,c.height-12);
}
function continuityWarnings(){
  const warnings=[];
  const groups={};for(const p of template.panels){if(!p.continuity_group)continue;(groups[p.continuity_group]||(groups[p.continuity_group]=[])).push(p.id);}
  for(const [g,ids] of Object.entries(groups)){if(ids.length<2)continue;const base=mappings[ids[0]];for(const id of ids.slice(1)){const m=mappings[id];if(m.scale!==base.scale||m.rotation!==base.rotation||m.offsetX!==base.offsetX||m.offsetY!==base.offsetY){warnings.push(`Continuity group ${g} has inconsistent transforms (${ids[0]} vs ${id}).`);break;}}}
  return warnings;
}
function renderValidation(){
  const box=$('validationList'),warnings=continuityWarnings();
  if(!claimsVendorReady())warnings.unshift('Generic preview: exact vendor dimensions have not been supplied. Exports are draft-only.');
  const required=template.panels.filter(p=>p.required!==false);if(!required.length)warnings.push('Template has no required panels.');
  box.innerHTML=warnings.length?warnings.map(w=>`<div class="warning">${esc(w)}</div>`).join(''):'<div class="ok">Template and continuity transforms pass local validation.</div>';
  status(claimsVendorReady()?`READY · IMPORTED TEMPLATE · ${template.provider} ${template.template_version}`:`DRAFT READY · GENERIC TEMPLATE · ${template.panels.length} PANELS`,claimsVendorReady()?'ready':'draft');
}
async function renderHashes(){const payload={design:config(),template:{provider:template.provider,product_id:template.product_id,template_version:template.template_version},mappings};const h=await sha256Text(stableJSON(payload));$('hashMetrics').innerHTML=`<div>Mapping fingerprint</div><div>${h.slice(0,16)}…</div><div>Evidence scope</div><div>${claimsVendorReady()?'imported-template':'draft-preview'}</div>`;}
function renderAll(){saveSelectedControls();renderMap();renderValidation();renderHashes().catch(()=>{});}
function queueRender(){syncValues();saveSelectedControls();if(renderQueued)return;renderQueued=true;requestAnimationFrame(()=>{renderQueued=false;renderAll();});}
function autoMap(){const groups={};for(const p of template.panels){if(!p.continuity_group)continue;(groups[p.continuity_group]||(groups[p.continuity_group]=[])).push(p.id);}for(const ids of Object.values(groups)){const b={...mappings[ids[0]]};ids.forEach(id=>mappings[id]={...b});}loadSelectedControls();renderAll();}
function resetMap(){for(const p of template.panels)mappings[p.id]={offsetX:0,offsetY:0,scale:100,rotation:Number(p.rotation||0)};loadSelectedControls();renderAll();}

function renderPanelExact(p){
  const m=mappings[p.id],c=document.createElement('canvas');c.width=p.width;c.height=p.height;const ctx=c.getContext('2d');ctx.fillStyle='#111';ctx.fillRect(0,0,c.width,c.height);const tile=currentTile||makeTile(512),cx=c.width/2,cy=c.height/2;ctx.save();ctx.translate(cx,cy);ctx.rotate(m.rotation*Math.PI/180);ctx.translate(-cx,-cy);const tileSize=Math.max(8,512*(m.scale/100));const ox=m.offsetX%512,oy=m.offsetY%512;for(let y=-tileSize*3+oy;y<c.height+tileSize*3;y+=tileSize)for(let x=-tileSize*3+ox;x<c.width+tileSize*3;x+=tileSize)ctx.drawImage(tile,x,y,tileSize,tileSize);ctx.restore();return c;
}
async function exportSelected(){const p=template.panels.find(x=>x.id===selectedPanel);if(!p)return;const blob=await canvasBlob(renderPanelExact(p));downloadBlob(blob,`${slug(template.provider)}_${slug(template.product_id)}_${p.id}_${p.width}x${p.height}.png`);}
function slug(s){return String(s).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'rac';}
function mappingPayload(){return{schema_version:'1.0',created_at:new Date().toISOString(),design:config(),template:{provider:template.provider,product_id:template.product_id,template_version:template.template_version,source:template.source||null,vendor_ready_claim:claimsVendorReady()},mappings};}
function exportMapping(){downloadBlob(new Blob([JSON.stringify(mappingPayload(),null,2)],{type:'application/json'}),`rac-mapping-${Date.now()}.json`);}
async function buildManifest(includeBytes=false){
  renderAll();const master=makeTile(4096);const masterBlob=await canvasBlob(master);const masterBytes=new Uint8Array(await masterBlob.arrayBuffer());const masterHash=await sha256Bytes(masterBytes);
  const panelRecords=[],files=[];
  for(const p of template.panels){const blob=await canvasBlob(renderPanelExact(p));const bytes=new Uint8Array(await blob.arrayBuffer());const hash=await sha256Bytes(bytes);panelRecords.push({id:p.id,label:p.label,width:p.width,height:p.height,required:p.required!==false,bleed:p.bleed||0,safe_margin:p.safe_margin||0,continuity_group:p.continuity_group||null,sha256:hash});if(includeBytes)files.push({name:`panels/${p.id}.png`,data:bytes});}
  const templateClean={...template};delete templateClean.__origin;const templateHash=await sha256Text(stableJSON(templateClean));const mapping=mappingPayload();const mappingHash=await sha256Text(stableJSON(mapping));
  const manifest={schema_version:'2.0',created_at:new Date().toISOString(),status:claimsVendorReady()?'vendor_template_mapped':'draft_preview_mapped',vendor_ready:claimsVendorReady(),caveat:claimsVendorReady()?'Template structure and dimensions were imported by the user; RAC has not independently verified the provider source.':'Generic RAC preview geometry only. Do not upload as a vendor production template.',design:{...config(),master_tile:{filename:'master/repeat_4096.png',width:4096,height:4096,sha256:masterHash}},template:{provider:template.provider,product_id:template.product_id,product_name:template.product_name||null,template_version:template.template_version,dpi:template.dpi,units:template.units,source:template.source||null,sha256:templateHash},mapping:{sha256:mappingHash,transforms:JSON.parse(JSON.stringify(mappings))},panels:panelRecords,evidence_binding:{design_artifact_sha256:masterHash,template_sha256:templateHash,mapping_sha256:mappingHash,invalidates_on_any_artifact_change:true}};
  lastManifest=manifest;if(includeBytes){files.unshift({name:'master/repeat_4096.png',data:masterBytes});files.push({name:'manifest.json',data:new TextEncoder().encode(JSON.stringify(manifest,null,2))});files.push({name:'mapping.json',data:new TextEncoder().encode(JSON.stringify(mapping,null,2))});files.push({name:'template.json',data:new TextEncoder().encode(JSON.stringify(templateClean,null,2))});}
  $('hashMetrics').innerHTML=`<div>Design SHA-256</div><div>${masterHash.slice(0,16)}…</div><div>Template SHA-256</div><div>${templateHash.slice(0,16)}…</div><div>Mapping SHA-256</div><div>${mappingHash.slice(0,16)}…</div>`;
  return{manifest,files};
}
async function exportManifest(){status('HASHING ARTIFACTS…');try{const {manifest}=await buildManifest(false);downloadBlob(new Blob([JSON.stringify(manifest,null,2)],{type:'application/json'}),`rac-evidence-manifest-${Date.now()}.json`);renderValidation();}catch(e){status('EXPORT ERROR · '+e.message,'error');}}

function crc32(data){let c=0xffffffff;for(let i=0;i<data.length;i++){c^=data[i];for(let k=0;k<8;k++)c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;}
function u16(v){const a=new Uint8Array(2);new DataView(a.buffer).setUint16(0,v,true);return a;}function u32(v){const a=new Uint8Array(4);new DataView(a.buffer).setUint32(0,v,true);return a;}
function concat(parts){const n=parts.reduce((s,p)=>s+p.length,0),o=new Uint8Array(n);let at=0;for(const p of parts){o.set(p,at);at+=p.length;}return o;}
function zipStore(files){const enc=new TextEncoder(),locals=[],centrals=[];let offset=0;for(const file of files){const name=enc.encode(file.name),data=file.data instanceof Uint8Array?file.data:new Uint8Array(file.data),crc=crc32(data);const local=concat([u32(0x04034b50),u16(20),u16(0),u16(0),u16(0),u16(0),u32(crc),u32(data.length),u32(data.length),u16(name.length),u16(0),name,data]);locals.push(local);const central=concat([u32(0x02014b50),u16(20),u16(20),u16(0),u16(0),u16(0),u16(0),u32(crc),u32(data.length),u32(data.length),u16(name.length),u16(0),u16(0),u16(0),u16(0),u32(0),u32(offset),name]);centrals.push(central);offset+=local.length;}const centralBlob=concat(centrals),end=concat([u32(0x06054b50),u16(0),u16(0),u16(files.length),u16(files.length),u32(centralBlob.length),u32(offset),u16(0)]);return concat([...locals,centralBlob,end]);}
async function exportPack(){status('BUILDING PANEL PACK…');$('exportPackBtn').disabled=true;try{const {manifest,files}=await buildManifest(true);const zip=zipStore(files);const prefix=manifest.vendor_ready?'rac-vendor-panel-pack':'rac-draft-panel-pack';downloadBlob(new Blob([zip],{type:'application/zip'}),`${prefix}-${Date.now()}.zip`);renderValidation();}catch(e){status('PACK ERROR · '+e.message,'error');}finally{$('exportPackBtn').disabled=false;}}

function localScore(canvas){const d=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data,w=canvas.width,h=canvas.height,bins=new Array(32).fill(0),colors=new Set();let samples=0,edges=0,comp=0;for(let y=0;y<h;y+=4)for(let x=0;x<w;x+=4){const i=(y*w+x)*4,r=d[i],g=d[i+1],b=d[i+2],gray=(r+g+b)/3;bins[Math.min(31,Math.floor(gray/8))]++;colors.add(`${r>>5}-${g>>5}-${b>>5}`);samples++;if(x+4<w){const j=(y*w+x+4)*4,ng=(d[j]+d[j+1]+d[j+2])/3;if(Math.abs(gray-ng)>48)edges++;comp++;}}let entropy=0;for(const n of bins)if(n){const p=n/samples;entropy-=p*Math.log2(p);}const entropyScore=Math.min(10,entropy/5*10),edgeDensity=edges/Math.max(1,comp),colorComplexity=Math.min(1,colors.size/128),complexity=Math.min(10,(edgeDensity*.65+colorComplexity*.35)*10),printability=Math.max(0,Math.min(10,10-edgeDensity*4-colorComplexity*2)),score=Math.max(0,Math.min(10,entropyScore*.45+complexity*.35+printability*.2));return{score,entropyScore,complexity,printability};}
async function runBatch(){const count=Math.max(4,Math.min(100,+$('batchCount').value||24)),keep=Math.max(1,Math.min(20,+$('batchKeep').value||9)),base=config(),rows=[];$('runBatchBtn').disabled=true;$('batchGrid').innerHTML='<div class="hint">Generating candidates…</div>';await new Promise(r=>setTimeout(r,20));for(let i=0;i<count;i++){const seed=(base.seed+i*37)%1000,c=makeTile(128,{...base,seed}),m=localScore(c);rows.push({seed,...m,data:c.toDataURL('image/png')});}rows.sort((a,b)=>b.score-a.score);shortlist=rows.slice(0,Math.min(keep,rows.length));renderBatch();$('exportBatchBtn').disabled=false;$('runBatchBtn').disabled=false;}
function renderBatch(){const g=$('batchGrid');g.innerHTML='';for(const row of shortlist){const card=document.createElement('div');card.className='candidate';card.dataset.seed=row.seed;const c=document.createElement('canvas');c.width=c.height=128;const im=new Image();im.onload=()=>c.getContext('2d').drawImage(im,0,0);im.src=row.data;const text=document.createElement('div');text.innerHTML=`SEED <strong>${row.seed}</strong><br>SCORE ${row.score.toFixed(2)}`;card.append(c,text);card.onclick=()=>{$('seed').value=row.seed;syncValues();document.querySelectorAll('.candidate').forEach(x=>x.classList.remove('selected'));card.classList.add('selected');renderAll();};g.appendChild(card);}}
function exportBatch(){const payload={schema_version:'1.0',created_at:new Date().toISOString(),family:$('family').value,base_controls:{scale:+$('scale').value,density:+$('density').value,distress:+$('distress').value},ranking_metric:'local_visual_printability_proxy',caveat:'Local visual/printability proxy only; not detector efficacy or RAC certification evidence.',candidates:shortlist.map(({data,...x})=>x)};downloadBlob(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),`rac-batch-shortlist-${Date.now()}.json`);}
function loadStudioState(){try{const s=JSON.parse(localStorage.getItem('rac.productStudioState')||'null');if(!s)throw new Error('No saved Product Studio state');let f=s.designFamily;if(f==='auto')f=FAMILY_BY_PRODUCT[s.productType]||'machine_static';if(f&&patternGenerators[f])$('family').value=f;if(s.studioSeed!=null)$('seed').value=s.studioSeed;if(s.studioScale!=null)$('scale').value=s.studioScale;if(s.studioDensity!=null)$('density').value=s.studioDensity;if(s.studioDistress!=null)$('distress').value=s.studioDistress;syncValues();renderAll();status(`DESIGN LOADED · ${$('family').value.toUpperCase().replaceAll('_',' ')} · SEED ${$('seed').value}`,claimsVendorReady()?'ready':'draft');}catch(e){status('DESIGN LOAD · '+e.message,'error');}}
async function importTemplate(file){if(!file)return;try{const t=JSON.parse(await file.text());setTemplate(t,'imported');}catch(e){status('TEMPLATE ERROR · '+e.message,'error');}}
async function downloadSchema(){try{const r=await fetch('templates/vendor-template.schema.json',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);downloadBlob(new Blob([await r.text()],{type:'application/json'}),'rac-vendor-template.schema.json');}catch(e){status('SCHEMA DOWNLOAD ERROR · '+e.message,'error');}}
async function init(){
  try{const r=await fetch('templates/generic-aop-hoodie-preview.json',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);setTemplate(await r.json(),'builtin');}catch(e){status('INIT ERROR · '+e.message,'error');return;}
  ['seed','scale','density','distress','offsetX','offsetY','panelScale','rotation'].forEach(id=>$(id).addEventListener('input',queueRender));$('family').addEventListener('change',renderAll);$('renderBtn').onclick=renderAll;$('templateFile').addEventListener('change',e=>importTemplate(e.target.files[0]));$('downloadSchemaBtn').onclick=downloadSchema;$('loadStudioStateBtn').onclick=loadStudioState;$('autoMapBtn').onclick=autoMap;$('resetMapBtn').onclick=resetMap;$('exportMapBtn').onclick=exportMapping;$('exportSelectedBtn').onclick=exportSelected;$('exportManifestBtn').onclick=exportManifest;$('exportPackBtn').onclick=exportPack;$('runBatchBtn').onclick=runBatch;$('exportBatchBtn').onclick=exportBatch;syncValues();
}
window.RACProduction={validateTemplate,setTemplate,renderAll,buildManifest,zipStore,runBatch,loadStudioState};
window.addEventListener('DOMContentLoaded',init);
})();
