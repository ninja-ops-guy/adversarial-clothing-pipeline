(function(){
  'use strict';

  const IDS=['productType','designFamily','studioScale','studioDensity','studioDistress','studioSeed','brandName','productName','collectionName','generationMode'];
  const FAMILY_BY_PRODUCT={hoodie:'machine_static',hat:'signal_shadow',beanie:'ghost_hound',cargo:'broken_human',mask:'machine_static',shirt:'error_garden'};

  function snapshot(){
    const state={schema_version:'2.0',saved_at:new Date().toISOString()};
    for(const id of IDS){const el=document.getElementById(id);if(el)state[id]=el.value;}
    if(state.designFamily==='auto')state.designFamily=FAMILY_BY_PRODUCT[state.productType]||'machine_static';
    state.resolvedDesignFamily=state.designFamily;
    state.referenceProfile=state.resolvedDesignFamily;
    state.artDirectionProfile='canonical_launch_capsule_v1';
    const conditioner=window.RACReferenceConditioner;
    state.reference_profile=conditioner&&typeof conditioner.getProfile==='function'?conditioner.getProfile():null;
    state.reference_source_mode=state.reference_profile?'scalar_style_conditioning':'canonical_profile';
    try{localStorage.setItem('rac.productStudioState',JSON.stringify(state));}catch(_){ }
    return state;
  }

  function sharpenPatternPreview(){
    const canvas=document.getElementById('studioPatternCanvas');
    if(!canvas)return;
    if(canvas.width<1024||canvas.height<1024){
      canvas.width=1024;
      canvas.height=1024;
      requestAnimationFrame(()=>{
        if(window.RACStudio&&typeof window.RACStudio.renderAll==='function')window.RACStudio.renderAll();
      });
    }
  }

  function bind(){
    IDS.forEach(id=>{
      const el=document.getElementById(id);
      if(!el)return;
      el.addEventListener('change',snapshot);
      if(el.type==='range')el.addEventListener('input',()=>setTimeout(snapshot,0));
    });
    for(const id of ['analyzeReference','applyReference','resetReference']){
      const el=document.getElementById(id);if(el)el.addEventListener('click',()=>setTimeout(snapshot,0));
    }
    document.querySelectorAll('.motif-card,.variation-card').forEach(el=>el.addEventListener('click',()=>setTimeout(snapshot,0)));
    sharpenPatternPreview();
    setTimeout(snapshot,250);
  }

  window.RACStudioBridge={snapshot,sharpenPatternPreview};
  window.addEventListener('DOMContentLoaded',bind);
})();
