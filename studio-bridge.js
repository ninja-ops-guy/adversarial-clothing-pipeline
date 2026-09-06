(function(){
  const IDS=['productType','designFamily','studioScale','studioDensity','studioDistress','studioSeed','brandName','productName','collectionName'];
  const FAMILY_BY_PRODUCT={hoodie:'machine_static',hat:'signal_shadow',beanie:'ghost_hound',cargo:'broken_human',mask:'machine_static',shirt:'error_garden'};

  function snapshot(){
    const state={schema_version:'1.2',saved_at:new Date().toISOString()};
    for(const id of IDS){const el=document.getElementById(id);if(el)state[id]=el.value;}
    if(state.designFamily==='auto')state.designFamily=FAMILY_BY_PRODUCT[state.productType]||'machine_static';
    state.resolvedDesignFamily=state.designFamily;
    state.reference_source_mode='use_existing_showcase';
    try{localStorage.setItem('rac.productStudioState',JSON.stringify(state));}catch(_){ }
    return state;
  }

  function vectorShowcase(){
    const W=2048,H=1536;
    const cards=[];
    const families=['GHOST HOUND','BROKEN HUMAN','ERROR GARDEN','MACHINE STATIC','SIGNAL SHADOW'];
    const fills=['signal','static','garden','static','signal'];
    for(let i=0;i<5;i++){
      const x=52+i*390;
      cards.push(`<g transform="translate(${x} 292)"><rect width="360" height="390" rx="12" fill="#0d1319" stroke="#394650" stroke-width="2"/><rect x="12" y="12" width="336" height="296" rx="8" fill="url(#${fills[i]})"/><path d="M28 270 L142 48 L205 154 L330 62" fill="none" stroke="${i%2?'#ece72b':'#2358da'}" stroke-width="28" opacity=".88"/>${i===0||i===4?'<ellipse cx="176" cy="150" rx="104" ry="57" fill="none" stroke="#e5ddca" stroke-width="14"/><circle cx="176" cy="150" r="27" fill="#080b0e" stroke="#d27891" stroke-width="9"/>':''}${i===2?'<g fill="none" stroke="#d27891" stroke-width="12"><circle cx="110" cy="108" r="49"/><circle cx="246" cy="188" r="62"/><path d="M60 250c90-125 152-129 262-195"/></g>':''}<text x="18" y="338" fill="#f1f3f2" font-family="Arial" font-size="18" font-weight="900" letter-spacing="2">${families[i]}</text><text x="18" y="365" fill="#7f8b94" font-family="monospace" font-size="11" letter-spacing="2">CONDITIONAL FAMILY ${i+1}</text></g>`);
    }
    const tiles=[];
    for(let i=0;i<8;i++){
      const x=52+i*242;
      tiles.push(`<g transform="translate(${x} 760)"><rect width="220" height="220" rx="8" fill="url(#${i%2?'signal':'static'})" stroke="#34414a" stroke-width="2"/><path d="M18 ${186-i*7} C62 ${20+i*13} 120 ${248-i*15} 205 ${45+i*9}" fill="none" stroke="${i%3===0?'#ece72b':i%3===1?'#2358da':'#e5ddca'}" stroke-width="${9+i}" opacity=".84"/>${i%2===0?'<circle cx="110" cy="110" r="48" fill="none" stroke="#d27891" stroke-width="9"/>':''}</g>`);
    }
    const motifs=[];
    for(let i=0;i<10;i++){
      const x=52+i*194;
      motifs.push(`<g transform="translate(${x} 126)"><rect width="176" height="126" rx="8" fill="#0d1319" stroke="#35414b" stroke-width="2"/><rect x="9" y="9" width="158" height="82" rx="5" fill="url(#${i%3===0?'static':i%3===1?'signal':'eye'})"/>${i%4===0?'<ellipse cx="88" cy="49" rx="54" ry="28" fill="none" stroke="#e5ddca" stroke-width="8"/><circle cx="88" cy="49" r="14" fill="#080b0e" stroke="#2358da" stroke-width="5"/>':''}${i%4===1?'<path d="M24 74 L68 20 L101 54 L151 18" fill="none" stroke="#ece72b" stroke-width="12"/>':''}${i%4===2?'<path d="M24 68 C42 24 70 19 88 49 C106 10 145 21 150 65 C145 94 108 98 90 72 C67 101 35 95 24 68Z" fill="none" stroke="#d27891" stroke-width="8"/>':''}<text x="10" y="112" fill="#8e9aa3" font-family="monospace" font-size="10" letter-spacing="2">MOTIF ${String(i+1).padStart(2,'0')}</text></g>`);
    }
    const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><defs><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".65" numOctaves="3" seed="118"/><feComponentTransfer><feFuncA type="table" tableValues="0 .13"/></feComponentTransfer></filter><pattern id="signal" width="150" height="150" patternUnits="userSpaceOnUse" patternTransform="rotate(17)"><rect width="150" height="150" fill="#090c0f"/><rect width="38" height="150" fill="#e5ddca"/><rect x="45" width="22" height="150" fill="#2358da"/><rect x="76" width="13" height="150" fill="#ece72b"/><rect x="108" width="42" height="150" fill="#171c20"/></pattern><pattern id="static" width="96" height="96" patternUnits="userSpaceOnUse"><rect width="96" height="96" fill="#080b0e"/><rect x="4" y="8" width="42" height="9" fill="#d8d1bf"/><rect x="55" y="7" width="31" height="6" fill="#2358da"/><rect x="12" y="35" width="68" height="7" fill="#30363c"/><rect x="7" y="58" width="28" height="15" fill="#ece72b"/><rect x="42" y="54" width="45" height="22" fill="#d27891"/><rect x="18" y="83" width="59" height="4" fill="#e5ddca"/></pattern><pattern id="garden" width="180" height="180" patternUnits="userSpaceOnUse"><rect width="180" height="180" fill="#101410"/><circle cx="48" cy="52" r="30" fill="#d27891"/><circle cx="126" cy="98" r="38" fill="#e5ddca"/><path d="M15 170 C58 62 103 81 173 17" fill="none" stroke="#6f7b4e" stroke-width="22"/></pattern><radialGradient id="eye"><stop offset="0" stop-color="#080b0e"/><stop offset=".2" stop-color="#e5ddca"/><stop offset=".36" stop-color="#2358da"/><stop offset=".57" stop-color="#0b0e11"/><stop offset=".78" stop-color="#ece72b"/><stop offset="1" stop-color="#0b0e11"/></radialGradient></defs><rect width="2048" height="1536" fill="#080b0e"/><rect width="2048" height="102" fill="#111922"/><text x="52" y="49" fill="#f2f4f3" font-family="Arial" font-size="34" font-weight="900" letter-spacing="5">RAC TEXTILE GENERATOR</text><text x="52" y="78" fill="#7e8b94" font-family="monospace" font-size="14" font-weight="700" letter-spacing="5">HIGH-RESOLUTION VECTOR SHOWCASE // VISUAL SOURCE ONLY</text><text x="1992" y="49" text-anchor="end" fill="#ece72b" font-family="monospace" font-size="14">2048 × 1536</text>${motifs.join('')}${cards.join('')}${tiles.join('')}<g transform="translate(52 1040)"><rect width="1940" height="430" rx="12" fill="#0d1319" stroke="#34414a" stroke-width="2"/><rect x="18" y="18" width="1220" height="394" rx="8" fill="url(#static)"/><path d="M50 380 L370 48 L520 238 L760 35 L922 297 L1190 88" fill="none" stroke="#2358da" stroke-width="58" opacity=".9"/><ellipse cx="470" cy="215" rx="240" ry="116" fill="none" stroke="#e5ddca" stroke-width="26"/><circle cx="470" cy="215" r="66" fill="#080b0e" stroke="#ece72b" stroke-width="21"/><text x="1280" y="70" fill="#f2f4f3" font-family="Arial" font-size="24" font-weight="900" letter-spacing="3">SOURCE QUALITY</text><text x="1280" y="112" fill="#ece72b" font-family="monospace" font-size="17" font-weight="800">VECTOR / SCALE-INDEPENDENT</text><text x="1280" y="160" fill="#8e9aa3" font-family="monospace" font-size="14">Native artboard: 2048 × 1536</text><text x="1280" y="194" fill="#8e9aa3" font-family="monospace" font-size="14">Production export: 4096 × 4096 PNG</text><text x="1280" y="242" fill="#e5ddca" font-family="monospace" font-size="13">BLACK · CREAM · BLUE · SIGNAL YELLOW</text><text x="1280" y="276" fill="#d27891" font-family="monospace" font-size="13">ANATOMY · FLORAL · GLITCH · SIGNAL</text><text x="1280" y="352" fill="#65727c" font-family="monospace" font-size="11">NOT BENCHMARK OR PHYSICAL EVIDENCE</text></g><rect width="2048" height="1536" filter="url(#grain)" opacity=".25"/></svg>`;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  }

  function addQualityBadge(frame,text,kind){
    if(!frame)return;
    let badge=frame.querySelector('.rac-quality-badge');
    if(!badge){
      badge=document.createElement('div');
      badge.className='rac-quality-badge';
      badge.style.cssText='position:absolute;top:14px;right:14px;z-index:3;padding:7px 9px;border:1px solid #3a4651;background:#080b0ee8;color:#dfe5e6;font:700 10px monospace;letter-spacing:.08em;';
      frame.style.position='relative';
      frame.appendChild(badge);
    }
    badge.textContent=text;
    badge.style.color=kind==='reject'?'#ece72b':'#dfe5e6';
  }

  function enforceReferenceQuality(){
    const img=document.getElementById('showcaseReference');
    const toggle=document.getElementById('useShowcaseSource');
    const frame=img&&img.closest('.showcase-reference-frame');
    if(!img)return;

    const audit=new Image();
    audit.onload=()=>{
      if(toggle){toggle.disabled=false;toggle.title='';}
      img.src=window.RAC_SHOWCASE_DATA_URI||img.src;
      img.alt='RAC Textile Generator existing showcase reference';
      addQualityBadge(frame,`SHOWCASE SOURCE · ${audit.naturalWidth}×${audit.naturalHeight}`,'ok');
      const note=document.querySelector('.showcase-source-controls .mini-note');
      if(note)note.textContent='Uses the existing RAC Textile Generator showcase as an optional stylized source layer. Measured detector evidence remains separate.';
    };
    audit.onerror=()=>{
      if(toggle){toggle.disabled=false;toggle.title='';}
      img.src=vectorShowcase();
      img.alt='RAC Textile Generator scalable fallback showcase';
      addQualityBadge(frame,'SHOWCASE SOURCE · VECTOR FALLBACK','ok');
    };
    audit.src=window.RAC_SHOWCASE_DATA_URI||img.currentSrc||img.src;
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

  window.RACStudioBridge={snapshot,enforceReferenceQuality,vectorShowcase};
  window.addEventListener('DOMContentLoaded',()=>{
    IDS.forEach(id=>{const el=document.getElementById(id);if(el)el.addEventListener('change',snapshot);});
    document.querySelectorAll('button').forEach(btn=>{
      if(/render design|generate pattern|next variation/i.test(btn.textContent||''))btn.addEventListener('click',()=>setTimeout(snapshot,0));
    });
    enforceReferenceQuality();
    sharpenPatternPreview();
    setTimeout(snapshot,250);
  });
})();
