(function(){
  'use strict';

  const $=id=>document.getElementById(id);
  const MIN_SIDE=256;
  let profile=null;

  function clamp(min,max,v){return Math.max(min,Math.min(max,v));}
  function hex(v){return Math.round(v).toString(16).padStart(2,'0');}
  function rgbHex(r,g,b){return `#${hex(r)}${hex(g)}${hex(b)}`;}
  function luminance(r,g,b){return .2126*r+.7152*g+.0722*b;}
  function saturation(r,g,b){
    const max=Math.max(r,g,b),min=Math.min(r,g,b);
    if(max===0)return 0;
    return (max-min)/max;
  }
  async function sha256(buffer){
    const digest=await crypto.subtle.digest('SHA-256',buffer);
    return [...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,'0')).join('');
  }
  function quantKey(r,g,b){return `${r>>4},${g>>4},${b>>4}`;}
  function keyRgb(key){return key.split(',').map(v=>Number(v)*16+8);}

  async function loadImage(file){
    const url=URL.createObjectURL(file);
    try{
      const img=new Image();
      await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(new Error(`Unable to read ${file.name}`));img.src=url;});
      return img;
    } finally {
      setTimeout(()=>URL.revokeObjectURL(url),0);
    }
  }

  function analyzePixels(img){
    const side=256;
    const scale=Math.min(1,side/Math.max(img.naturalWidth,img.naturalHeight));
    const w=Math.max(1,Math.round(img.naturalWidth*scale));
    const h=Math.max(1,Math.round(img.naturalHeight*scale));
    const c=document.createElement('canvas');c.width=w;c.height=h;
    const ctx=c.getContext('2d',{willReadFrequently:true});
    ctx.drawImage(img,0,0,w,h);
    const data=ctx.getImageData(0,0,w,h).data;
    const lum=new Float32Array(w*h);
    const bins=new Map();
    let sum=0,sum2=0,satSum=0,dark=0,accent=0;
    for(let i=0,p=0;i<data.length;i+=4,p++){
      const r=data[i],g=data[i+1],b=data[i+2];
      const y=luminance(r,g,b),s=saturation(r,g,b);
      lum[p]=y;sum+=y;sum2+=y*y;satSum+=s;
      if(y<68)dark++;
      if(s>.42&&y>45)accent++;
      const k=quantKey(r,g,b);bins.set(k,(bins.get(k)||0)+1);
    }
    let edge=0,edgeN=0;
    for(let y=1;y<h;y++)for(let x=1;x<w;x++){
      const i=y*w+x;
      edge+=Math.abs(lum[i]-lum[i-1])+Math.abs(lum[i]-lum[i-w]);
      edgeN+=2;
    }
    const n=w*h,mean=sum/n;
    const contrast=Math.sqrt(Math.max(0,sum2/n-mean*mean))/128;
    const palette=[...bins.entries()].sort((a,b)=>b[1]-a[1]).slice(0,12).map(([k,count])=>({rgb:keyRgb(k),count}));
    return {
      width:img.naturalWidth,height:img.naturalHeight,
      mean_luminance:mean/255,
      contrast:clamp(0,1.5,contrast),
      saturation:satSum/n,
      dark_fraction:dark/n,
      accent_fraction:accent/n,
      edge_density:clamp(0,1,(edge/Math.max(1,edgeN))/96),
      palette
    };
  }

  function mergeAnalyses(items){
    const weight=items.reduce((a,b)=>a+b.width*b.height,0)||1;
    const avg=key=>items.reduce((a,b)=>a+b[key]*(b.width*b.height),0)/weight;
    const paletteBins=new Map();
    for(const item of items)for(const p of item.palette){const key=p.rgb.join(',');paletteBins.set(key,(paletteBins.get(key)||0)+p.count);}
    const ranked=[...paletteBins.entries()].sort((a,b)=>b[1]-a[1]).map(([key,count])=>({rgb:key.split(',').map(Number),count}));
    return {
      mean_luminance:avg('mean_luminance'),contrast:avg('contrast'),saturation:avg('saturation'),
      dark_fraction:avg('dark_fraction'),accent_fraction:avg('accent_fraction'),edge_density:avg('edge_density'),
      palette:ranked
    };
  }

  function buildPalette(entries){
    const colors=entries.map(x=>x.rgb);
    const byLum=[...colors].sort((a,b)=>luminance(...a)-luminance(...b));
    const bySat=[...colors].sort((a,b)=>saturation(...b)-saturation(...a));
    const fallback=[[8,8,8],[24,24,24],[58,58,58],[112,112,112],[220,210,190],[30,90,215],[232,222,24]];
    const out=[
      byLum[0],byLum[1],byLum[Math.floor(byLum.length*.45)],byLum[Math.floor(byLum.length*.68)],byLum[byLum.length-1],bySat[0],bySat[1]
    ].map((v,i)=>v||fallback[i]);
    return out.map(v=>rgbHex(...v));
  }

  function deriveControls(stats,hash){
    const seed=parseInt(hash.slice(0,8),16)%1000;
    const scale=Math.round(clamp(24,86,72-stats.edge_density*38+stats.dark_fraction*10));
    const density=Math.round(clamp(35,96,48+stats.saturation*38+stats.accent_fraction*32+stats.edge_density*18));
    const distress=Math.round(clamp(38,98,48+stats.edge_density*42+stats.contrast*28));
    return {seed,scale,density,distress};
  }

  function renderProfile(){
    const status=$('referenceStatus'),swatches=$('referenceSwatches');
    if(!status||!swatches)return;
    swatches.innerHTML='';
    if(!profile){status.textContent='NO REFERENCE PROFILE';return;}
    status.textContent=`PROFILE READY · ${profile.source_count} SOURCE${profile.source_count===1?'':'S'}`;
    for(const color of profile.palette){const el=document.createElement('span');el.className='reference-swatch';el.style.background=color;el.title=color;swatches.appendChild(el);}
  }

  async function analyze(){
    const input=$('referenceInput');
    const files=[...(input&&input.files||[])];
    if(!files.length)throw new Error('Select at least one reference image.');
    const analyses=[],hashes=[];
    for(const file of files){
      const bytes=await file.arrayBuffer();hashes.push(await sha256(bytes));
      const img=await loadImage(file);
      if(Math.min(img.naturalWidth,img.naturalHeight)<MIN_SIDE)throw new Error(`${file.name} is below the ${MIN_SIDE}px reference-analysis minimum.`);
      analyses.push(analyzePixels(img));
    }
    const merged=mergeAnalyses(analyses);
    const combinedHash=await sha256(new TextEncoder().encode(hashes.join(':')).buffer);
    const controls=deriveControls(merged,combinedHash);
    profile={
      schema_version:'1.0',mode:'scalar_style_conditioning',source_count:files.length,source_sha256:hashes,
      combined_sha256:combinedHash,palette:buildPalette(merged.palette),metrics:{
        mean_luminance:merged.mean_luminance,contrast:merged.contrast,saturation:merged.saturation,
        dark_fraction:merged.dark_fraction,accent_fraction:merged.accent_fraction,edge_density:merged.edge_density
      },controls,
      source_pixels_used_in_output:false,
      evidence_scope:'design_reference_only'
    };
    renderProfile();
    try{localStorage.setItem('rac.referenceProfile',JSON.stringify(profile));}catch(_){ }
    return profile;
  }

  function setRange(id,value){const el=$(id);if(!el)return;el.value=String(value);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}
  function apply(){
    if(!profile)throw new Error('Analyze a reference first.');
    if(window.colorPalettes){
      const p=profile.palette;
      window.colorPalettes.rac_reference=p.slice(0,7);
      window.colorPalettes.error_garden=[p[0],p[1],p[4],p[2],p[5],p[6],p[3]];
    }
    setRange('studioScale',profile.controls.scale);
    setRange('studioDensity',profile.controls.density);
    setRange('studioDistress',profile.controls.distress);
    setRange('studioSeed',profile.controls.seed);
    if(window.RACStudio&&typeof window.RACStudio.renderAll==='function')window.RACStudio.renderAll();
    const status=$('referenceStatus');if(status)status.textContent='REFERENCE APPLIED';
  }

  function reset(){
    profile=null;
    try{localStorage.removeItem('rac.referenceProfile');}catch(_){ }
    renderProfile();
  }

  function restore(){
    try{const raw=localStorage.getItem('rac.referenceProfile');if(raw)profile=JSON.parse(raw);}catch(_){profile=null;}
    renderProfile();
  }

  function bind(){
    const analyzeBtn=$('analyzeReference'),applyBtn=$('applyReference'),resetBtn=$('resetReference');
    if(analyzeBtn)analyzeBtn.addEventListener('click',async()=>{try{analyzeBtn.disabled=true;await analyze();}catch(err){const s=$('referenceStatus');if(s)s.textContent=`REFERENCE ERROR · ${err.message}`;}finally{analyzeBtn.disabled=false;}});
    if(applyBtn)applyBtn.addEventListener('click',()=>{try{apply();}catch(err){const s=$('referenceStatus');if(s)s.textContent=`REFERENCE ERROR · ${err.message}`;}});
    if(resetBtn)resetBtn.addEventListener('click',reset);
    restore();
  }

  window.RACReferenceConditioner={analyze,apply,reset,getProfile:()=>profile};
  window.addEventListener('DOMContentLoaded',bind);
})();
