(function(){
'use strict';

function ensureResearchCatalog(){
  if(document.querySelector('script[src$="studio-research-catalog.js"]'))return;
  const script=document.createElement('script');
  script.src='studio-research-catalog.js';
  script.async=false;
  script.dataset.racResearchCatalog='true';
  document.head.appendChild(script);
}

ensureResearchCatalog();

const input=document.getElementById('templateFile');
if(!input)return;

function setStatus(text){
  const el=document.getElementById('productionStatus');
  if(!el)return;
  el.textContent=text;
  el.className='status error';
}

async function sha256Text(text){
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,'0')).join('');
}

function provenanceErrors(template){
  const errors=[];
  if(template&&template.vendor_ready===true){
    if(typeof template.source!=='string'||template.source.trim().length<3){
      errors.push('vendor_ready templates require a non-empty provider source reference');
    }
    if(String(template.provider||'').toUpperCase()==='GENERIC_PREVIEW'){
      errors.push('GENERIC_PREVIEW cannot claim vendor_ready status');
    }
  }
  return errors;
}

input.addEventListener('change',async event=>{
  // Own the import path so provenance is validated and hashed before the
  // Production Mapper accepts the normalized template.
  event.stopImmediatePropagation();
  const file=event.target.files&&event.target.files[0];
  if(!file)return;
  try{
    const raw=await file.text();
    const parsed=JSON.parse(raw);
    const structural=window.RACProduction&&window.RACProduction.validateTemplate
      ? window.RACProduction.validateTemplate(parsed)
      : ['Production Mapper is not ready'];
    const errors=[...structural,...provenanceErrors(parsed)];
    if(errors.length)throw new Error(errors.join('; '));
    parsed.source_artifact={
      filename:file.name,
      sha256:await sha256Text(raw)
    };
    window.RACProduction.setTemplate(parsed,'imported');
  }catch(error){
    setStatus('TEMPLATE ERROR · '+error.message);
  }
},true);
})();
