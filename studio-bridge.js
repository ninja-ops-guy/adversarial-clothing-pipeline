(function(){
  const IDS=['productType','designFamily','studioScale','studioDensity','studioDistress','studioSeed','brandName','productName','collectionName'];
  function snapshot(){
    const state={schema_version:'1.0',saved_at:new Date().toISOString()};
    for(const id of IDS){const el=document.getElementById(id);if(el)state[id]=el.value;}
    try{localStorage.setItem('rac.productStudioState',JSON.stringify(state));}catch(_){ }
    return state;
  }
  window.RACStudioBridge={snapshot};
  window.addEventListener('DOMContentLoaded',()=>{
    IDS.forEach(id=>{const el=document.getElementById(id);if(el)el.addEventListener('change',snapshot);});
    document.querySelectorAll('button').forEach(btn=>{
      if(/render design|next variation/i.test(btn.textContent||''))btn.addEventListener('click',()=>setTimeout(snapshot,0));
    });
    setTimeout(snapshot,250);
  });
})();
