(function(){
'use strict';

const CATALOG_VERSION='1.1.0';
const ARTIFACT_MANIFEST_SCHEMA='rac_pattern_candidate_artifact/v1';
const CANONICAL_GEOMETRY_ID='PATTERNS_CANONICAL_128_V1';
const CANONICAL_FAMILIES=['signal_shadow','machine_static','ghost_hound','broken_human','error_garden'];
const P0_IDS=/* P0_CATALOG_JSON */["hyperface_like","dazzle_surgical_lines","key_feature_blackout","saliency_eye_attack","adversarial_patch","swapped_landmarks","landmark_noise","feature_collage"];
const P0_META=[
  {id:'hyperface_like',title:'HYPERFACE LIKE',category:'STRUCTURAL BIOMETRIC',generator_class:'HyperfaceLikeGenerator'},
  {id:'dazzle_surgical_lines',title:'DAZZLE SURGICAL LINES',category:'STRUCTURAL BIOMETRIC',generator_class:'DazzleSurgicalLinesGenerator'},
  {id:'key_feature_blackout',title:'KEY FEATURE BLACKOUT',category:'STRUCTURAL BIOMETRIC',generator_class:'KeyFeatureBlackoutGenerator'},
  {id:'saliency_eye_attack',title:'SALIENCY EYE ATTACK',category:'FEATURE DISRUPTION',generator_class:'SaliencyEyeAttackGenerator'},
  {id:'adversarial_patch',title:'ADVERSARIAL PATCH',category:'FEATURE DISRUPTION',generator_class:'AdversarialPatchGenerator'},
  {id:'swapped_landmarks',title:'SWAPPED LANDMARKS',category:'FEATURE DISRUPTION',generator_class:'SwappedLandmarksGenerator'},
  {id:'landmark_noise',title:'LANDMARK NOISE',category:'FEATURE DISRUPTION',generator_class:'LandmarkNoiseGenerator'},
  {id:'feature_collage',title:'FEATURE COLLAGE',category:'FEATURE DISRUPTION',generator_class:'FeatureCollageGenerator'}
];
const P0_SET=new Set(P0_IDS);
let importedCanvas=null,importedDataUrl=null,importedMetadata=null;

function isResearchFamily(id){return P0_SET.has(id);}
function familyMeta(id){return P0_META.find(x=>x.id===id)||null;}
function familyTitle(id){return familyMeta(id)?.title||String(id||'').replaceAll('_',' ').toUpperCase();}
function activeFamily(){return document.getElementById('designFamily')?.value||document.getElementById('family')?.value||null;}
function imageMatchesFamily(family){return Boolean(importedCanvas&&importedMetadata?.research_family===family);}
function candidateMatchesFamily(family){return Boolean(imageMatchesFamily(family)&&importedMetadata?.provenance_verified===true);}
function sha256(bytes){return crypto.subtle.digest('SHA-256',bytes).then(buf=>[...new Uint8Array(buf)].map(v=>v.toString(16).padStart(2,'0')).join(''));}
function isHex64(value){return /^[0-9a-f]{64}$/i.test(String(value||''));}
function isPngBytes(bytes){const a=new Uint8Array(bytes);const sig=[0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a];return a.length>=sig.length&&sig.every((v,i)=>a[i]===v);}
function dataUrl(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(reader.error||new Error('Unable to read candidate image'));reader.readAsDataURL(file);});}
function imageCanvas(url){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{const c=document.createElement('canvas');c.width=img.naturalWidth||img.width;c.height=img.naturalHeight||img.height;c.getContext('2d').drawImage(img,0,0);resolve(c);};img.onerror=()=>reject(new Error('Candidate image could not be decoded'));img.src=url;});}

function renderImportedOrPlaceholder(ctx,size,family){
  ctx.save();ctx.fillStyle='#777';ctx.fillRect(0,0,size,size);
  if(imageMatchesFamily(family)){ctx.imageSmoothingEnabled=true;ctx.drawImage(importedCanvas,0,0,size,size);if(!candidateMatchesFamily(family)){ctx.fillStyle='rgba(0,0,0,.72)';ctx.fillRect(0,size*.84,size,size*.16);ctx.fillStyle='#fff';ctx.textAlign='center';ctx.textBaseline='middle';ctx.font=`700 ${Math.max(10,Math.floor(size*.025))}px ui-monospace,monospace`;ctx.fillText('UNVERIFIED PREVIEW · MANIFEST REQUIRED',size/2,size*.92);}}
  else{ctx.fillStyle='#111';ctx.fillRect(size*.08,size*.42,size*.84,size*.16);ctx.fillStyle='#eee';ctx.textAlign='center';ctx.textBaseline='middle';ctx.font=`700 ${Math.max(12,Math.floor(size*.035))}px ui-monospace,monospace`;ctx.fillText('IMPORT CANDIDATE PNG + MANIFEST',size/2,size/2);}
  ctx.restore();
}
function installRenderBridge(){
  if(typeof patternGenerators!=='undefined')for(const id of P0_IDS)if(!patternGenerators[id])patternGenerators[id]=(ctx,size)=>renderImportedOrPlaceholder(ctx,size,id);
  if(!window.RACPatternComposition||window.RACPatternComposition.__researchCatalogWrapped)return;
  const original=window.RACPatternComposition.renderFamilyFromSpec;
  window.RACPatternComposition.renderFamilyFromSpec=function(ctx,size,spec){
    if(isResearchFamily(spec?.family)){renderImportedOrPlaceholder(ctx,size,spec.family);return;}
    return original(ctx,size,spec);
  };
  window.RACPatternComposition.__researchCatalogWrapped=true;
}

function addOption(select,meta){if(!select||select.querySelector(`option[value="${meta.id}"]`))return;const o=document.createElement('option');o.value=meta.id;o.textContent=`${meta.title} · P0 / VERIFIED IMPORT`;select.appendChild(o);}
function addOptions(){for(const meta of P0_META){addOption(document.getElementById('designFamily'),meta);addOption(document.getElementById('family'),meta);}}
function selectProductFamily(id){const select=document.getElementById('designFamily');if(!select)return;select.value=id;select.dispatchEvent(new Event('change',{bubbles:true}));}

function addCatalogCards(){
  const grid=document.querySelector('.family-grid');if(!grid||grid.querySelector('.p0-research'))return;
  const note=document.createElement('div');note.className='family-catalog-note';note.textContent='P0 RESEARCH GENERATORS · EXACT ARTIFACT IMPORT · HASH-BOUND CANDIDATE MANIFEST REQUIRED FOR EXPORT';grid.appendChild(note);
  for(const meta of P0_META){const card=document.createElement('button');card.type='button';card.className='family-card p0-research';card.dataset.family=meta.id;card.innerHTML=`<div class="family-art"><span>▧</span></div><strong>${meta.title}</strong><small>${meta.category} · P0</small>`;card.addEventListener('click',()=>selectProductFamily(meta.id));grid.appendChild(card);}
}

function ensureImportUi(){
  const productSelect=document.getElementById('designFamily'),productionSelect=document.getElementById('family');
  if(!productSelect&&!productionSelect)return;
  const anchor=productSelect?.closest('.two-col-fields')||productionSelect?.closest('.field');if(!anchor||document.getElementById('researchCandidateImport'))return;
  const box=document.createElement('div');box.id='researchCandidateImport';box.className='research-import';box.hidden=true;box.innerHTML=`<div class="research-import-copy"><strong>P0 RESEARCH CANDIDATE</strong><span id="researchCandidateFamily">—</span><small>Import the exact PNG plus its hash-bound <code>${ARTIFACT_MANIFEST_SCHEMA}</code> sidecar. PNG-only imports are previewable but cannot be exported or packaged as governed evidence.</small></div><div class="research-import-actions"><label class="research-import-button">Import candidate PNG<input id="researchCandidateFile" type="file" accept="image/png" hidden></label><label class="research-import-button">Import candidate manifest<input id="researchCandidateManifestFile" type="file" accept="application/json,.json" hidden></label><button id="researchCandidateClear" type="button">Clear candidate</button></div><div id="researchCandidateStatus" class="research-import-status">NO CANDIDATE LOADED</div>`;
  anchor.insertAdjacentElement('afterend',box);
  document.getElementById('researchCandidateFile').addEventListener('change',e=>importCandidate(e.target.files?.[0]));
  document.getElementById('researchCandidateManifestFile').addEventListener('change',e=>importCandidateManifest(e.target.files?.[0]));
  document.getElementById('researchCandidateClear').addEventListener('click',clearCandidate);
}

function installStyles(){if(document.getElementById('researchCatalogStyles'))return;const s=document.createElement('style');s.id='researchCatalogStyles';s.textContent=`
.family-catalog-note{grid-column:1/-1;padding:10px 12px;border:1px dashed rgba(255,255,255,.25);font:700 10px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.07em;opacity:.76}
.family-card.p0-research{position:relative;min-height:96px}.family-card.p0-research .family-art{display:grid;place-items:center;font-size:26px}.family-card.p0-research small{display:block;margin-top:5px;font-size:8px;letter-spacing:.05em;opacity:.62}.family-card.p0-research::after{content:'P0';position:absolute;right:7px;top:7px;padding:2px 4px;border:1px solid currentColor;font:700 8px/1 ui-monospace,monospace;opacity:.65}
.research-import{margin:12px 0;padding:12px;border:1px solid rgba(255,255,255,.2);display:grid;gap:8px}.research-import[hidden]{display:none}.research-import-copy{display:grid;gap:3px}.research-import-copy small,.research-import-status{font-size:10px;opacity:.72}.research-import-actions{display:flex;gap:8px;flex-wrap:wrap}.research-import-button{display:inline-block;padding:8px 10px;border:1px solid currentColor;cursor:pointer;font-weight:700;text-transform:uppercase}.research-import-status{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}#findBestMatchBtn[disabled]{opacity:.45;cursor:not-allowed}
`;document.head.appendChild(s);}

function setResearchStatus(message){const status=document.getElementById('researchCandidateStatus');if(status)status.textContent=message;}
function resetCandidateState(statusText='NO CANDIDATE LOADED'){
  importedCanvas=null;importedDataUrl=null;importedMetadata=null;
  if(window.RACStudio?.clearFrozenTile)window.RACStudio.clearFrozenTile();
  if(window.RACProduction?.renderAll)window.RACProduction.renderAll();
  for(const id of ['researchCandidateFile','researchCandidateManifestFile']){const input=document.getElementById(id);if(input)input.value='';}
  setResearchStatus(statusText);
}
function invalidateCandidateForFamily(family){
  if(importedMetadata&&!imageMatchesFamily(family))resetCandidateState('CANDIDATE CLEARED · FAMILY CHANGED · REIMPORT REQUIRED');
}
function updateProductExportControls(family,research){
  const ready=research&&candidateMatchesFamily(family);
  for(const method of ['exportTile','exportMockup','exportManifest']){
    const button=document.querySelector(`button[onclick*="RACStudio.${method}"]`);if(!button)continue;
    if(research&&!ready){if(!button.disabled)button.dataset.researchDisabled='true';button.disabled=true;button.title='Import the candidate PNG and matching hash-bound manifest before export.';}
    else{if(button.dataset.researchDisabled==='true'){button.disabled=false;delete button.dataset.researchDisabled;}if(!research||ready)button.title='';}
  }
}
function updateProductionExportControls(family,research){
  const ready=research&&candidateMatchesFamily(family);
  for(const id of ['exportMapBtn','exportSelectedBtn','exportManifestBtn','exportPackBtn','runBatchBtn','exportBatchBtn']){
    const button=document.getElementById(id);if(!button)continue;
    if(research&&!ready){if(!button.disabled)button.dataset.researchDisabled='true';button.disabled=true;button.title='Verified P0 candidate manifest required.';}
    else if(button.dataset.researchDisabled==='true'){button.disabled=false;delete button.dataset.researchDisabled;button.title='';}
  }
}

function validateCandidateManifest(manifest,family){
  if(!imageMatchesFamily(family))throw new Error('Import the candidate PNG before its manifest');
  if(!manifest||typeof manifest!=='object'||Array.isArray(manifest))throw new Error('Candidate manifest must be a JSON object');
  if(manifest.schema_version!==ARTIFACT_MANIFEST_SCHEMA)throw new Error(`Manifest schema must be ${ARTIFACT_MANIFEST_SCHEMA}`);
  if(manifest.research_family!==family)throw new Error('Manifest research_family does not match the selected family');
  if(manifest.generator!==family)throw new Error('Manifest generator does not match the registered P0 family');
  if(manifest.artifact_media_type!=='image/png')throw new Error('Manifest artifact_media_type must be image/png');
  if(manifest.artifact_filename!==importedMetadata.filename)throw new Error('Manifest artifact_filename does not match the imported PNG');
  if(!isHex64(manifest.artifact_sha256)||manifest.artifact_sha256.toLowerCase()!==importedMetadata.sha256)throw new Error('Manifest artifact_sha256 does not match the imported PNG bytes');
  if(!isHex64(manifest.pattern_sha256))throw new Error('Manifest pattern_sha256 is missing or invalid');
  if(!isHex64(manifest.provenance_hash))throw new Error('Manifest provenance_hash is missing or invalid');
  if(!String(manifest.candidate_id||'').startsWith('RAC-PAT-CAND-'))throw new Error('Manifest candidate_id is missing or invalid');
  if(!String(manifest.generator_version||'').trim())throw new Error('Manifest generator_version is required');
  if(manifest.evidence_class!=='digital_candidate')throw new Error('Manifest evidence_class must be digital_candidate');
  if(manifest.physical_efficacy_claimed!==false)throw new Error('Manifest must explicitly set physical_efficacy_claimed=false');
  if(manifest.claim_state!=='EXPLORATORY')throw new Error('Manifest claim_state must be EXPLORATORY');
  if(!manifest.params||typeof manifest.params!=='object'||Array.isArray(manifest.params))throw new Error('Manifest params are required');
  return manifest;
}
function sanitizeResearchManifest(manifest,family){
  const copy=JSON.parse(JSON.stringify(manifest));
  if(!isResearchFamily(family)||copy?.design?.family!==family)throw new Error('P0 manifest family binding mismatch');
  const frozen=copy.frozen_tile_override;
  if(!frozen?.active||frozen.research_family!==family||!candidateMatchesFamily(family))throw new Error('P0 manifest export requires the active verified family-bound candidate');
  if(!isHex64(frozen.sha256)||frozen.sha256.toLowerCase()!==String(frozen.artifact_sha256||'').toLowerCase())throw new Error('P0 manifest export requires a byte-hash-bound artifact');
  if(frozen.provenance_verified!==true||frozen.manifest_schema_version!==ARTIFACT_MANIFEST_SCHEMA)throw new Error('P0 manifest export requires verified candidate provenance');
  copy.art_direction_profile='p0_verified_candidate_import_v1';
  copy.generation_mode='verified_candidate_import';
  copy.reference_profile=null;
  copy.reference_target=null;
  copy.reference_fidelity={score:null,subscores:null,penalties:[],scorer_version:null,evidence_scope:'not_applicable_to_p0_governed_candidate_import'};
  return copy;
}
function installProductStudioGuards(){
  const studio=window.RACStudio;if(!studio||studio.__researchCatalogGuarded)return;
  const originalFind=studio.findBestMatch?.bind(studio),originalGetFidelity=studio.getReferenceFidelity?.bind(studio),originalExportManifest=studio.exportManifest?.bind(studio);
  if(originalFind)studio.findBestMatch=function(...args){if(isResearchFamily(activeFamily())){setResearchStatus('REFERENCE MATCH BLOCKED · NOT APPLICABLE TO P0 IMPORTS');return Promise.resolve({skipped:true,reason:'not_applicable_to_p0_governed_candidate_import'});}return originalFind(...args);};
  if(originalGetFidelity)studio.getReferenceFidelity=function(){return isResearchFamily(activeFamily())?null:originalGetFidelity();};
  for(const method of ['exportTile','exportMockup']){
    const original=studio[method]?.bind(studio);if(!original)continue;
    studio[method]=function(...args){const family=activeFamily();if(isResearchFamily(family)&&!candidateMatchesFamily(family)){setResearchStatus('EXPORT BLOCKED · VERIFIED CANDIDATE MANIFEST REQUIRED');return false;}return original(...args);};
  }
  if(originalExportManifest)studio.exportManifest=function(...args){
    const family=activeFamily();if(!isResearchFamily(family))return originalExportManifest(...args);
    if(!candidateMatchesFamily(family)){setResearchStatus('EXPORT BLOCKED · VERIFIED CANDIDATE MANIFEST REQUIRED');return false;}
    const NativeBlob=window.Blob;let intercepted=false;
    window.Blob=class RACResearchManifestBlob extends NativeBlob{
      constructor(parts=[],options={}){
        let next=parts;
        if(options?.type==='application/json'){
          if(parts.length!==1||typeof parts[0]!=='string')throw new Error('Unexpected P0 manifest serialization');
          const parsed=JSON.parse(parts[0]),sanitized=sanitizeResearchManifest(parsed,family);next=[JSON.stringify(sanitized,null,2)];intercepted=true;
        }
        super(next,options);
      }
    };
    try{const result=originalExportManifest(...args);if(!intercepted)throw new Error('P0 manifest export was not intercepted for evidence sanitization');return result;}
    finally{window.Blob=NativeBlob;}
  };
  Object.defineProperty(studio,'__researchCatalogGuarded',{value:true,configurable:false,enumerable:false,writable:false});
}

function syncProductUi(){
  const select=document.getElementById('designFamily');if(!select)return;const research=isResearchFamily(select.value),box=document.getElementById('researchCandidateImport'),family=document.getElementById('researchCandidateFamily'),find=document.getElementById('findBestMatchBtn'),profile=document.getElementById('referenceProfileStatus');
  if(research)invalidateCandidateForFamily(select.value);else if(importedMetadata)resetCandidateState();
  if(box)box.hidden=!research;if(family)family.textContent=research?familyTitle(select.value):'—';
  if(find){find.disabled=research;find.textContent=research?'Reference Match N/A':'Find Best Match';find.title=research?'Reference-fidelity search is defined for canonical art-direction families only.':'';}
  if(profile&&research){const state=candidateMatchesFamily(select.value)?'VERIFIED CANDIDATE BOUND':imageMatchesFamily(select.value)?'MANIFEST REQUIRED':'PNG + MANIFEST REQUIRED';const msg=`P0 RESEARCH IMPORT · ${familyTitle(select.value)} · ${state}`;if(profile.textContent!==msg)profile.textContent=msg;}
  if(!research&&window.RACStudio?.getFrozenTileMetadata?.()?.research_family)window.RACStudio.clearFrozenTile();
  updateProductExportControls(select.value,research);
}
function syncProductionUi(){
  const select=document.getElementById('family');if(!select)return;const research=isResearchFamily(select.value),box=document.getElementById('researchCandidateImport'),family=document.getElementById('researchCandidateFamily'),ranking=document.getElementById('batchRankingMode');
  if(research)invalidateCandidateForFamily(select.value);else if(importedMetadata)resetCandidateState();
  if(box)box.hidden=!research;if(family)family.textContent=research?familyTitle(select.value):'—';
  if(ranking){const ref=ranking.querySelector('option[value="reference_fidelity"]');if(ref)ref.disabled=research;if(research&&ranking.value==='reference_fidelity')ranking.value='visual_proxy';ranking.title=research?'P0 imports use visual/printability ranking only; reference fidelity is not defined for research families.':'';}
  updateProductionExportControls(select.value,research);
}
function syncAll(){syncProductUi();syncProductionUi();}

async function importCandidate(file){
  if(!file)return;const family=activeFamily();if(!isResearchFamily(family))return;
  setResearchStatus('READING CANDIDATE PNG…');
  try{
    const bytes=await file.arrayBuffer();if(!isPngBytes(bytes))throw new Error('File bytes are not PNG despite the selected filename/type');
    const hash=await sha256(bytes),url=await dataUrl(file),canvas=await imageCanvas(url);
    if(activeFamily()!==family){const input=document.getElementById('researchCandidateFile');if(input)input.value='';setResearchStatus('IMPORT DISCARDED · FAMILY CHANGED · REIMPORT REQUIRED');return;}
    const meta=familyMeta(family);importedCanvas=canvas;importedDataUrl=url;importedMetadata={research_family:family,generator:null,generator_class:meta?.generator_class||null,sha256:hash,artifact_sha256:hash,filename:file.name,width:canvas.width,height:canvas.height,provenance_verified:false,evidence_scope:'unverified_candidate_preview_not_physical_efficacy',catalog_version:CATALOG_VERSION};
    if(window.RACStudio?.loadFrozenTile)await window.RACStudio.loadFrozenTile(url,importedMetadata);
    if(activeFamily()!==family){resetCandidateState('IMPORT DISCARDED · FAMILY CHANGED · REIMPORT REQUIRED');return;}
    if(window.RACProduction?.renderAll)window.RACProduction.renderAll();
    syncAll();setResearchStatus(`PNG LOADED · MANIFEST REQUIRED · SHA-256 ${hash.slice(0,12)}…`);
  }catch(err){resetCandidateState('IMPORT ERROR · '+err.message);syncAll();}
}
async function importCandidateManifest(file){
  if(!file)return;const family=activeFamily();if(!isResearchFamily(family))return;
  setResearchStatus('VERIFYING CANDIDATE MANIFEST…');
  try{
    const manifest=validateCandidateManifest(JSON.parse(await file.text()),family),meta=familyMeta(family);
    importedMetadata={...importedMetadata,candidate_id:manifest.candidate_id,generator:manifest.generator,generator_class:meta?.generator_class||null,generator_version:manifest.generator_version,pattern_sha256:manifest.pattern_sha256,provenance_hash:manifest.provenance_hash,params:manifest.params,manifest_schema_version:manifest.schema_version,claim_state:manifest.claim_state,evidence_class:manifest.evidence_class,physical_efficacy_claimed:false,artifact_filename:manifest.artifact_filename,artifact_media_type:manifest.artifact_media_type,provenance_verified:true,evidence_scope:'verified_governed_candidate_preview_not_physical_efficacy'};
    if(window.RACStudio?.loadFrozenTile&&importedDataUrl)await window.RACStudio.loadFrozenTile(importedDataUrl,importedMetadata);
    if(activeFamily()!==family){resetCandidateState('MANIFEST DISCARDED · FAMILY CHANGED · REIMPORT REQUIRED');return;}
    if(window.RACProduction?.renderAll)window.RACProduction.renderAll();
    syncAll();setResearchStatus(`VERIFIED · ${manifest.candidate_id} · ARTIFACT ${manifest.artifact_sha256.slice(0,12)}…`);
  }catch(err){if(importedMetadata)importedMetadata.provenance_verified=false;const input=document.getElementById('researchCandidateManifestFile');if(input)input.value='';syncAll();setResearchStatus('MANIFEST REFUSED · '+err.message);}
}
function clearCandidate(){resetCandidateState();syncAll();}

function bind(){
  installStyles();installRenderBridge();addOptions();addCatalogCards();ensureImportUi();installProductStudioGuards();
  const product=document.getElementById('designFamily');if(product)product.addEventListener('change',()=>requestAnimationFrame(syncAll));
  const production=document.getElementById('family');if(production)production.addEventListener('change',()=>requestAnimationFrame(syncAll));
  const load=document.getElementById('loadStudioStateBtn');if(load)load.addEventListener('click',()=>requestAnimationFrame(syncAll),true);
  const profile=document.getElementById('referenceProfileStatus');if(profile)new MutationObserver(()=>{if(isResearchFamily(document.getElementById('designFamily')?.value))requestAnimationFrame(syncProductUi);}).observe(profile,{childList:true,subtree:true,characterData:true});
  requestAnimationFrame(syncAll);
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind);else bind();
window.RACStudioResearchCatalog={catalogVersion:CATALOG_VERSION,artifactManifestSchema:ARTIFACT_MANIFEST_SCHEMA,canonicalGeometryId:CANONICAL_GEOMETRY_ID,canonicalFamilies:[...CANONICAL_FAMILIES],p0Families:P0_META.map(x=>({...x,priority:'P0',studio_mode:'verified_candidate_artifact_import'})),implementedFamilyIds:[...CANONICAL_FAMILIES,...P0_IDS],deferred:{p1:5,p2:23,p3_refused:['bad_words','web_attack_strings']},isResearchFamily,getImportedMetadata:()=>importedMetadata,isCandidateVerified:family=>candidateMatchesFamily(family||activeFamily()),sanitizeResearchManifest,validateCandidateManifest,clearCandidate};
})();
