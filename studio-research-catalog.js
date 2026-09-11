(function(){
'use strict';

const CATALOG_VERSION='1.0.0';
const CANONICAL_GEOMETRY_ID='PATTERNS_CANONICAL_128_V1';
const CANONICAL_FAMILIES=['signal_shadow','machine_static','ghost_hound','broken_human','error_garden'];
const P0_IDS=/* P0_CATALOG_JSON */["hyperface_like","dazzle_surgical_lines","key_feature_blackout","saliency_eye_attack","adversarial_patch","swapped_landmarks","landmark_noise","feature_collage"];
const P0_META=[
  {id:'hyperface_like',title:'HYPERFACE LIKE',category:'STRUCTURAL BIOMETRIC',generator:'HyperfaceLikeGenerator'},
  {id:'dazzle_surgical_lines',title:'DAZZLE SURGICAL LINES',category:'STRUCTURAL BIOMETRIC',generator:'DazzleSurgicalLinesGenerator'},
  {id:'key_feature_blackout',title:'KEY FEATURE BLACKOUT',category:'STRUCTURAL BIOMETRIC',generator:'KeyFeatureBlackoutGenerator'},
  {id:'saliency_eye_attack',title:'SALIENCY EYE ATTACK',category:'FEATURE DISRUPTION',generator:'SaliencyEyeAttackGenerator'},
  {id:'adversarial_patch',title:'ADVERSARIAL PATCH',category:'FEATURE DISRUPTION',generator:'AdversarialPatchGenerator'},
  {id:'swapped_landmarks',title:'SWAPPED LANDMARKS',category:'FEATURE DISRUPTION',generator:'SwappedLandmarksGenerator'},
  {id:'landmark_noise',title:'LANDMARK NOISE',category:'FEATURE DISRUPTION',generator:'LandmarkNoiseGenerator'},
  {id:'feature_collage',title:'FEATURE COLLAGE',category:'FEATURE DISRUPTION',generator:'FeatureCollageGenerator'}
];
const P0_SET=new Set(P0_IDS);
let importedCanvas=null,importedMetadata=null;

function isResearchFamily(id){return P0_SET.has(id);}
function familyTitle(id){return P0_META.find(x=>x.id===id)?.title||String(id||'').replaceAll('_',' ').toUpperCase();}
function activeFamily(){return document.getElementById('designFamily')?.value||document.getElementById('family')?.value||null;}
function sha256(bytes){return crypto.subtle.digest('SHA-256',bytes).then(buf=>[...new Uint8Array(buf)].map(v=>v.toString(16).padStart(2,'0')).join(''));}
function dataUrl(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(reader.error||new Error('Unable to read candidate image'));reader.readAsDataURL(file);});}
function imageCanvas(url){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{const c=document.createElement('canvas');c.width=img.naturalWidth||img.width;c.height=img.naturalHeight||img.height;c.getContext('2d').drawImage(img,0,0);resolve(c);};img.onerror=()=>reject(new Error('Candidate image could not be decoded'));img.src=url;});}

function installRenderBridge(){
  if(!window.RACPatternComposition||window.RACPatternComposition.__researchCatalogWrapped)return;
  const original=window.RACPatternComposition.renderFamilyFromSpec;
  window.RACPatternComposition.renderFamilyFromSpec=function(ctx,size,spec){
    if(isResearchFamily(spec?.family)){
      ctx.save();ctx.fillStyle='#777';ctx.fillRect(0,0,size,size);
      if(importedCanvas){ctx.imageSmoothingEnabled=true;ctx.drawImage(importedCanvas,0,0,size,size);}
      else{ctx.fillStyle='#111';ctx.fillRect(size*.08,size*.42,size*.84,size*.16);ctx.fillStyle='#eee';ctx.textAlign='center';ctx.textBaseline='middle';ctx.font=`700 ${Math.max(12,Math.floor(size*.035))}px ui-monospace,monospace`;ctx.fillText('IMPORT GOVERNED CANDIDATE TILE',size/2,size/2);}
      ctx.restore();return;
    }
    return original(ctx,size,spec);
  };
  window.RACPatternComposition.__researchCatalogWrapped=true;
}

function addOption(select,meta){if(!select||select.querySelector(`option[value="${meta.id}"]`))return;const o=document.createElement('option');o.value=meta.id;o.textContent=`${meta.title} · P0 / IMPORT`;select.appendChild(o);}
function addOptions(){for(const meta of P0_META){addOption(document.getElementById('designFamily'),meta);addOption(document.getElementById('family'),meta);}}
function selectProductFamily(id){const select=document.getElementById('designFamily');if(!select)return;select.value=id;select.dispatchEvent(new Event('change',{bubbles:true}));}

function addCatalogCards(){
  const grid=document.querySelector('.family-grid');if(!grid||grid.querySelector('.p0-research'))return;
  const note=document.createElement('div');note.className='family-catalog-note';note.textContent='P0 RESEARCH GENERATORS · IMPORT GOVERNED CANDIDATE OUTPUTS · BROWSER DOES NOT REIMPLEMENT RESEARCH GENERATORS';grid.appendChild(note);
  for(const meta of P0_META){const card=document.createElement('button');card.type='button';card.className='family-card p0-research';card.dataset.family=meta.id;card.innerHTML=`<div class="family-art"><span>▧</span></div><strong>${meta.title}</strong><small>${meta.category} · P0</small>`;card.addEventListener('click',()=>selectProductFamily(meta.id));grid.appendChild(card);}
}

function ensureImportUi(){
  const productSelect=document.getElementById('designFamily'),productionSelect=document.getElementById('family');
  if(!productSelect&&!productionSelect)return;
  const anchor=productSelect?.closest('.two-col-fields')||productionSelect?.closest('.field');if(!anchor||document.getElementById('researchCandidateImport'))return;
  const box=document.createElement('div');box.id='researchCandidateImport';box.className='research-import';box.hidden=true;box.innerHTML=`<div class="research-import-copy"><strong>P0 RESEARCH CANDIDATE</strong><span id="researchCandidateFamily">—</span><small>Import a PNG produced by the governed Python pattern pipeline. Product Studio will mock up the exact imported tile; it does not regenerate the research family in-browser.</small></div><label class="research-import-button">Import candidate PNG<input id="researchCandidateFile" type="file" accept="image/png" hidden></label><button id="researchCandidateClear" type="button">Clear candidate</button><div id="researchCandidateStatus" class="research-import-status">NO CANDIDATE LOADED</div>`;
  anchor.insertAdjacentElement('afterend',box);
  document.getElementById('researchCandidateFile').addEventListener('change',e=>importCandidate(e.target.files?.[0]));
  document.getElementById('researchCandidateClear').addEventListener('click',clearCandidate);
}

function installStyles(){if(document.getElementById('researchCatalogStyles'))return;const s=document.createElement('style');s.id='researchCatalogStyles';s.textContent=`
.family-catalog-note{grid-column:1/-1;padding:10px 12px;border:1px dashed rgba(255,255,255,.25);font:700 10px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.07em;opacity:.76}
.family-card.p0-research{position:relative;min-height:96px}.family-card.p0-research .family-art{display:grid;place-items:center;font-size:26px}.family-card.p0-research small{display:block;margin-top:5px;font-size:8px;letter-spacing:.05em;opacity:.62}.family-card.p0-research::after{content:'P0';position:absolute;right:7px;top:7px;padding:2px 4px;border:1px solid currentColor;font:700 8px/1 ui-monospace,monospace;opacity:.65}
.research-import{margin:12px 0;padding:12px;border:1px solid rgba(255,255,255,.2);display:grid;gap:8px}.research-import[hidden]{display:none}.research-import-copy{display:grid;gap:3px}.research-import-copy small,.research-import-status{font-size:10px;opacity:.72}.research-import-button{display:inline-block;padding:8px 10px;border:1px solid currentColor;cursor:pointer;font-weight:700;text-transform:uppercase}.research-import-status{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}#findBestMatchBtn[disabled]{opacity:.45;cursor:not-allowed}
`;document.head.appendChild(s);}

function syncProductUi(){
  const select=document.getElementById('designFamily');if(!select)return;const research=isResearchFamily(select.value),box=document.getElementById('researchCandidateImport'),family=document.getElementById('researchCandidateFamily'),find=document.getElementById('findBestMatchBtn'),profile=document.getElementById('referenceProfileStatus');
  if(box)box.hidden=!research;if(family)family.textContent=research?familyTitle(select.value):'—';
  if(find){find.disabled=research;find.textContent=research?'Reference Match N/A':'Find Best Match';find.title=research?'Reference-fidelity search is defined for canonical art-direction families only.':'';}
  if(profile&&research){const msg=`P0 RESEARCH IMPORT · ${familyTitle(select.value)} · GOVERNED CANDIDATE REQUIRED`;if(profile.textContent!==msg)profile.textContent=msg;}
  if(!research&&window.RACStudio?.getFrozenTileMetadata?.()?.research_family)window.RACStudio.clearFrozenTile();
}
function syncProductionUi(){
  const select=document.getElementById('family');if(!select)return;const research=isResearchFamily(select.value),box=document.getElementById('researchCandidateImport'),family=document.getElementById('researchCandidateFamily'),ranking=document.getElementById('batchRankingMode');
  if(box)box.hidden=!research;if(family)family.textContent=research?familyTitle(select.value):'—';
  if(ranking){const ref=ranking.querySelector('option[value="reference_fidelity"]');if(ref)ref.disabled=research;if(research&&ranking.value==='reference_fidelity')ranking.value='visual_proxy';ranking.title=research?'P0 imports use visual/printability ranking only; reference fidelity is not defined for research families.':'';}
  if(!research){importedCanvas=null;importedMetadata=null;}
}
function syncAll(){syncProductUi();syncProductionUi();}

async function importCandidate(file){
  if(!file)return;const family=activeFamily();if(!isResearchFamily(family))return;
  const status=document.getElementById('researchCandidateStatus');if(status)status.textContent='READING CANDIDATE…';
  try{
    const bytes=await file.arrayBuffer(),hash=await sha256(bytes),url=await dataUrl(file),canvas=await imageCanvas(url);
    importedCanvas=canvas;importedMetadata={research_family:family,generator:P0_META.find(x=>x.id===family)?.generator||null,sha256:hash,filename:file.name,width:canvas.width,height:canvas.height,evidence_scope:'imported_governed_candidate_preview_not_physical_efficacy',catalog_version:CATALOG_VERSION};
    if(window.RACStudio?.loadFrozenTile)await window.RACStudio.loadFrozenTile(url,importedMetadata);
    if(window.RACProduction?.renderAll)window.RACProduction.renderAll();
    if(status)status.textContent=`LOADED · ${file.name} · SHA-256 ${hash.slice(0,12)}…`;
  }catch(err){if(status)status.textContent='IMPORT ERROR · '+err.message;}
}
function clearCandidate(){
  importedCanvas=null;importedMetadata=null;if(window.RACStudio?.clearFrozenTile)window.RACStudio.clearFrozenTile();if(window.RACProduction?.renderAll)window.RACProduction.renderAll();const input=document.getElementById('researchCandidateFile');if(input)input.value='';const status=document.getElementById('researchCandidateStatus');if(status)status.textContent='NO CANDIDATE LOADED';
}

function bind(){
  installStyles();installRenderBridge();addOptions();addCatalogCards();ensureImportUi();
  const product=document.getElementById('designFamily');if(product)product.addEventListener('change',()=>requestAnimationFrame(syncAll));
  const production=document.getElementById('family');if(production)production.addEventListener('change',()=>requestAnimationFrame(syncAll));
  const load=document.getElementById('loadStudioStateBtn');if(load)load.addEventListener('click',()=>requestAnimationFrame(syncAll),true);
  const profile=document.getElementById('referenceProfileStatus');if(profile)new MutationObserver(()=>{if(isResearchFamily(document.getElementById('designFamily')?.value))requestAnimationFrame(syncProductUi);}).observe(profile,{childList:true,subtree:true,characterData:true});
  requestAnimationFrame(syncAll);
}

document.addEventListener('DOMContentLoaded',bind);
window.RACStudioResearchCatalog={catalogVersion:CATALOG_VERSION,canonicalGeometryId:CANONICAL_GEOMETRY_ID,canonicalFamilies:[...CANONICAL_FAMILIES],p0Families:P0_META.map(x=>({...x,priority:'P0',studio_mode:'governed_candidate_import'})),implementedFamilyIds:[...CANONICAL_FAMILIES,...P0_IDS],deferred:{p1:5,p2:23,p3_refused:['bad_words','web_attack_strings']},isResearchFamily,getImportedMetadata:()=>importedMetadata,clearCandidate};
})();
