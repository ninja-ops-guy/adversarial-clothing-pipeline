const RACStudio=(()=>{
  const W=1122,H=1402;
  const N={
    hoodie:'MACHINE STATIC HOODIE',
    hat:'SIGNAL SHADOW HAT',
    beanie:'GHOST HOUND BEANIE',
    cargo:'BROKEN HUMAN CARGO PANTS',
    mask:'MACHINE STATIC MASK',
    shirt:'ERROR GARDEN SHIRT'
  };
  const F={
    hoodie:'machine_static',
    hat:'signal_shadow',
    beanie:'ghost_hound',
    cargo:'broken_human',
    mask:'machine_static',
    shirt:'error_garden'
  };
  const S={
    signal_shadow:['SIGNAL LAYERING','SUBTLE HIGH-CONTRAST CUES','INTERFERENCE GEOMETRY','FRAGMENTED VISUAL LANGUAGE','WEARABLE COMPLEXITY','HIDDEN ANIMAL FORMS'],
    machine_static:['MICRO-BLOCK DISRUPTION','INTERFERENCE TEXTURES','DIRECTIONAL GRAIN LAYERS','TONAL SIGNAL OVERLAYS','HIGH CONTRAST + LOW VISIBILITY','WEARABLE CAMOUFLAGE'],
    ghost_hound:['FRAGMENTED CANINE CUES','SILHOUETTE DISRUPTION','COMPETING VISUAL SIGNALS','HIGH CONTRAST + DIRECTIONAL NOISE','WEARABLE CAMOUFLAGE'],
    broken_human:['FRAGMENTED HUMAN CUES','DISPLACED ANATOMY','HIGH CONTRAST + DIRECTIONAL BREAKS','UTILITY DRIVEN CONSTRUCTION','ARTICULATED FORM FOR MOVEMENT','WEARABLE CAMOUFLAGE'],
    error_garden:['ORGANIC FLORAL FORMS','PIXEL CLUSTERS & DIGITAL ARTIFACTS','DISGUISED ANIMAL FRAGMENTS','FLUID NON-REPETITIVE COMPOSITION','HIGH CONTRAST + NATURAL TENSION','WEARABLE CAMOUFLAGE']
  };
  const T={
    hoodie:'LESS NOISE. MORE YOU.',
    hat:'LESS SIGNAL. MORE SHADOWS.',
    beanie:'LESS VISIBLE. MORE YOURS.',
    cargo:'LESS VISIBLE. MORE FREE.',
    mask:'LESS RECOGNITION. MORE FREEDOM.',
    shirt:'BEAUTY HIDES DIFFERENTLY.'
  };
  const DESC={
    signal_shadow:'A STUDY IN VISUAL CONFLICT. FAMILIAR SIGNALS. FRAGMENTED. REASSEMBLED.',
    machine_static:'A STUDY IN SYSTEM NOISE. IDENTITY AS INTERFERENCE. FICTION AS FREEDOM.',
    ghost_hound:'A STUDY IN VISUAL CONFLICT. CANINE SIGNALS. FRAGMENTED. REASSEMBLED.',
    broken_human:'A STUDY IN FRAGMENTATION. BODIES AS DATA. IDENTITIES OUT OF SYNC.',
    error_garden:'A STUDY IN NATURAL CONFLICT. FLORAL SIGNALS. FRAGMENTED. REASSEMBLED.'
  };
  const VERBS={
    signal_shadow:['OBSERVE','DISRUPT','MISLEAD','ADAPT','REMAIN'],
    machine_static:['COVER','DISRUPT','OBSCURE','ADAPT','CONTINUE'],
    ghost_hound:['DISRUPT','MISDIRECT','BLEND','REMAIN'],
    broken_human:['OBSERVE','DISTORT','MISLEAD','ADAPT','LIVE'],
    error_garden:['FRAGMENT','MUTATE','OVERGROW','ADAPT','PERSIST']
  };
  const FAMILY_TITLE={
    signal_shadow:'SIGNAL SHADOW',machine_static:'MACHINE STATIC',ghost_hound:'GHOST HOUND',broken_human:'BROKEN HUMAN',error_garden:'ERROR GARDEN'
  };

  let tile=null,manifest=null;
  const $=id=>document.getElementById(id);
  function state(){
    const product=$('productType').value;
    let family=$('designFamily').value;
    if(family==='auto')family=F[product];
    return {
      product,family,
      brand:($('brandName').value||'RUTHLESS').trim().toUpperCase(),
      productName:($('productName').value||N[product]).trim().toUpperCase(),
      collection:($('collectionName').value||'URBAN WILDERNESS').trim().toUpperCase(),
      seed:+$('studioSeed').value,scale:+$('studioScale').value,density:+$('studioDensity').value,distress:+$('studioDistress').value
    };
  }
  function defaults(force=false){
    const p=$('productType').value;
    if(force||!$('productName').dataset.edited)$('productName').value=N[p];
    const f=$('designFamily').value==='auto'?F[p]:$('designFamily').value;
    $('resolvedFamily').textContent=f.replaceAll('_',' ').toUpperCase();
  }
  function sync(id){const e=$(id+'Value');if(e)e.textContent=$(id).value;}
  function makeTile(size,s=state()){
    const c=document.createElement('canvas');c.width=c.height=size;
    const x=c.getContext('2d');
    const p={patternType:s.family,patternScale:s.scale,colorVariance:s.density,edgeIntensity:s.distress,symmetry:0,seed:s.seed};
    const pal=colorPalettes[s.family==='error_garden'?'error_garden':'rac_reference'];
    const r=seededRandom(s.seed),g=patternGenerators[s.family];
    if(!g)throw new Error('Missing pattern family: '+s.family);
    g(x,size,p,pal,r);return c;
  }
  function rr(c,x,y,w,h,r){r=Math.min(r,w/2,h/2);c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();}
  function fill(c,t,x,y,w,h,sz){for(let yy=y;yy<y+h;yy+=sz)for(let xx=x;xx<x+w;xx+=sz)c.drawImage(t,xx,yy,sz,sz);}
  function clip(c,p,t,b,sz){c.save();c.clip(p);fill(c,t,b.x,b.y,b.w,b.h,sz);c.restore();}
  function sh(c,x,y,rx,ry){c.save();c.globalAlpha=.12;c.fillStyle='#000';c.filter='blur(8px)';c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fill();c.filter='none';c.restore();}
  function label(c,x,y,w,h,title,lines=[]){
    c.save();c.fillStyle='rgba(10,10,10,.9)';rr(c,x,y,w,h,3);c.fill();c.fillStyle='#eee';c.font=`700 ${Math.max(7,w*.075)}px Arial`;c.fillText(title,x+w*.1,y+h*.2);
    c.font=`${Math.max(6,w*.055)}px monospace`;lines.slice(0,4).forEach((v,i)=>c.fillText(v,x+w*.1,y+h*(.42+i*.14)));
    c.strokeStyle='#eee';c.beginPath();c.moveTo(x+w*.72,y+h*.72);c.lineTo(x+w*.92,y+h*.72);c.moveTo(x+w*.82,y+h*.62);c.lineTo(x+w*.82,y+h*.82);c.stroke();c.restore();
  }
  function familyLabel(s){return FAMILY_TITLE[s.family]||s.brand;}

  function hoodiePath(x,y,w,h){
    const p=new Path2D(),b=x+w*.24,by=y+h*.2,bw=w*.52,bh=h*.72;
    p.moveTo(b+bw*.14,by);p.quadraticCurveTo(b,by+h*.03,b-w*.04,by+h*.12);p.lineTo(x+w*.02,y+h*.52);p.quadraticCurveTo(x,y+h*.62,x+w*.07,y+h*.65);p.lineTo(b+w*.02,y+h*.48);p.lineTo(b+w*.04,by+bh);p.quadraticCurveTo(x+w*.5,y+h*.98,b+bw-w*.04,by+bh);p.lineTo(b+bw-w*.02,y+h*.48);p.lineTo(x+w*.93,y+h*.65);p.quadraticCurveTo(x+w,y+h*.62,x+w*.98,y+h*.52);p.lineTo(b+bw+w*.04,by+h*.12);p.quadraticCurveTo(b+bw,by+h*.03,b+bw*.86,by);p.closePath();
    const hood=new Path2D();hood.moveTo(x+w*.35,y+h*.24);hood.quadraticCurveTo(x+w*.31,y+h*.04,x+w*.5,y+h*.01);hood.quadraticCurveTo(x+w*.69,y+h*.04,x+w*.65,y+h*.24);hood.quadraticCurveTo(x+w*.5,y+h*.32,x+w*.35,y+h*.24);hood.closePath();
    return{body:p,hood};
  }
  function hoodie(c,t,cx,cy,sc,v,s){
    const w=340*sc,h=560*sc,x=cx-w/2,y=cy-h/2,p=hoodiePath(x,y,w,h);sh(c,cx,y+h*.96,w*.45,h*.025);clip(c,p.body,t,{x,y,w,h},150*sc);clip(c,p.hood,t,{x,y,w,h:h*.35},130*sc);c.strokeStyle='#1b1b1b';c.lineWidth=3*sc;c.stroke(p.body);c.stroke(p.hood);
    c.save();c.strokeStyle='rgba(240,240,240,.32)';c.lineWidth=sc;c.beginPath();c.moveTo(cx,y+h*.23);c.lineTo(cx,y+h*.91);c.stroke();c.restore();
    if(v==='front'){c.fillStyle='rgba(12,12,12,.45)';rr(c,x+w*.31,y+h*.69,w*.38,h*.16,18*sc);c.fill();label(c,x+w*.55,y+h*.33,w*.22,h*.18,familyLabel(s),['SYSTEMS','DEVIATE','HUMANS','EVOLVE']);}
    else label(c,x+w*.57,y+h*.36,w*.22,h*.18,'SAME',['SIGNAL','DIFFERENT','OUTCOME']);
  }
  function teePath(x,y,w,h){
    const p=new Path2D();p.moveTo(x+w*.33,y+h*.08);p.quadraticCurveTo(x+w*.5,y,x+w*.67,y+h*.08);p.lineTo(x+w*.96,y+h*.2);p.lineTo(x+w*.82,y+h*.43);p.lineTo(x+w*.72,y+h*.37);p.lineTo(x+w*.7,y+h*.96);p.lineTo(x+w*.3,y+h*.96);p.lineTo(x+w*.28,y+h*.37);p.lineTo(x+w*.18,y+h*.43);p.lineTo(x+w*.04,y+h*.2);p.closePath();return p;
  }
  function shirt(c,t,cx,cy,sc,v,s){
    const w=365*sc,h=520*sc,x=cx-w/2,y=cy-h/2,p=teePath(x,y,w,h);sh(c,cx,y+h*.98,w*.42,h*.025);clip(c,p,t,{x,y,w,h},165*sc);c.strokeStyle='#1b1b1b';c.lineWidth=2.5*sc;c.stroke(p);
    label(c,x+w*.55,y+h*.28,w*.23,h*.18,v==='front'?familyLabel(s):'NATURE',v==='front'?['BEAUTY','DISTORTED','STILL','ALIVE']:['ERRORS','CREATE','NEW','LIFE']);
  }
  function beanie(c,t,cx,cy,sc,v,s){
    const w=280*sc,h=245*sc,x=cx-w/2,y=cy-h/2;sh(c,cx,y+h*.93,w*.42,h*.035);const p=new Path2D();
    if(v==='slouch'){p.moveTo(x+w*.06,y+h*.65);p.quadraticCurveTo(x+w*.15,y+h*.08,x+w*.55,y+h*.08);p.quadraticCurveTo(x+w*1.05,y+h*.12,x+w*.86,y+h*.67);p.quadraticCurveTo(x+w*.72,y+h*.92,x+w*.22,y+h*.88);}
    else{p.moveTo(x+w*.08,y+h*.72);p.quadraticCurveTo(x+w*.08,y+h*.12,x+w*.5,y+h*.06);p.quadraticCurveTo(x+w*.92,y+h*.12,x+w*.92,y+h*.72);}
    p.closePath();clip(c,p,t,{x,y,w,h},120*sc);c.strokeStyle='#171717';c.lineWidth=3*sc;c.stroke(p);c.fillStyle='rgba(10,10,10,.2)';rr(c,x+w*.08,y+h*.62,w*.84,h*.25,8*sc);c.fill();
    if(v==='front')label(c,x+w*.56,y+h*.64,w*.3,h*.2,familyLabel(s),['SEE','DIFFERENTLY']);
  }
  function mask(c,t,cx,cy,sc,v,s){
    const w=245*sc,h=360*sc,x=cx-w/2,y=cy-h/2;sh(c,cx,y+h*.95,w*.36,h*.025);const p=new Path2D();p.moveTo(cx,y+h*.02);p.bezierCurveTo(x+w*.16,y+h*.04,x+w*.08,y+h*.33,x+w*.18,y+h*.62);p.lineTo(x+w*.08,y+h*.96);p.lineTo(x+w*.92,y+h*.96);p.lineTo(x+w*.82,y+h*.62);p.bezierCurveTo(x+w*.92,y+h*.33,x+w*.84,y+h*.04,cx,y+h*.02);p.closePath();clip(c,p,t,{x,y,w,h},115*sc);c.strokeStyle='#171717';c.lineWidth=2.5*sc;c.stroke(p);c.fillStyle='#0d0d0d';rr(c,x+w*.2,y+h*.29,w*.6,h*.18,18*sc);c.fill();
    if(v==='front')label(c,x+w*.55,y+h*.49,w*.29,h*.19,familyLabel(s),['SIGNAL','DISTORT','ADAPT','SURVIVE']);
    else if(v==='side')label(c,x+w*.54,y+h*.46,w*.28,h*.17,'SAME',['SIGNAL','DIFFERENT','FACE']);
    else label(c,x+w*.55,y+h*.46,w*.28,h*.17,'NO HUMAN',['JUST','NOISE']);
  }
  function cargo(c,t,cx,cy,sc,v,s){
    const w=300*sc,h=610*sc,x=cx-w/2,y=cy-h/2;sh(c,cx,y+h*.98,w*.4,h*.02);const p=new Path2D();p.moveTo(x+w*.16,y+h*.03);p.lineTo(x+w*.84,y+h*.03);p.lineTo(x+w*.79,y+h*.51);p.lineTo(x+w*.7,y+h*.97);p.lineTo(x+w*.49,y+h*.97);p.lineTo(x+w*.5,y+h*.53);p.lineTo(x+w*.42,y+h*.97);p.lineTo(x+w*.21,y+h*.97);p.lineTo(x+w*.16,y+h*.5);p.closePath();clip(c,p,t,{x,y,w,h},145*sc);c.strokeStyle='#171717';c.lineWidth=2.5*sc;c.stroke(p);
    const pockets=v==='side'?[[.58,.31,.3,.2]]:[[.12,.3,.27,.17],[.61,.3,.27,.17],[.18,.53,.22,.13],[.6,.53,.22,.13]];
    pockets.forEach(q=>{c.fillStyle='rgba(10,10,10,.27)';rr(c,x+w*q[0],y+h*q[1],w*q[2],h*q[3],6*sc);c.fill();});
    label(c,x+w*(v==='side'?.55:.56),y+h*.28,w*.27,h*.15,v==='side'?'FRAGMENT':familyLabel(s),v==='side'?['MUTATE','OVERGROW','PERSIST']:['OBSERVE','DISTORT','MISLEAD','ADAPT']);
  }
  function hat(c,t,cx,cy,sc,v,s){
    const w=330*sc,h=255*sc,x=cx-w/2,y=cy-h/2;sh(c,cx,y+h*.92,w*.44,h*.035);c.save();
    if(v==='top'){
      const p=new Path2D();p.ellipse(cx,cy,w*.36,h*.43,0,0,Math.PI*2);clip(c,p,t,{x,y,w,h},125*sc);c.strokeStyle='#171717';c.lineWidth=2.5*sc;c.stroke(p);c.strokeStyle='rgba(230,230,230,.26)';
      for(let i=0;i<6;i++){const a=Math.PI*2*i/6;c.beginPath();c.moveTo(cx,cy);c.lineTo(cx+Math.cos(a)*w*.36,cy+Math.sin(a)*h*.43);c.stroke();}
      c.fillStyle='#111';c.beginPath();c.arc(cx,cy,8*sc,0,Math.PI*2);c.fill();c.restore();return;
    }
    const crown=new Path2D();
    if(v==='side'){
      crown.moveTo(x+w*.18,y+h*.67);crown.quadraticCurveTo(x+w*.19,y+h*.15,x+w*.52,y+h*.08);crown.quadraticCurveTo(x+w*.82,y+h*.1,x+w*.84,y+h*.68);crown.closePath();
      clip(c,crown,t,{x,y,w,h},130*sc);c.strokeStyle='#171717';c.lineWidth=2.5*sc;c.stroke(crown);
      const brim=new Path2D();brim.moveTo(x+w*.18,y+h*.64);brim.quadraticCurveTo(x-w*.02,y+h*.7,x+w*.04,y+h*.82);brim.quadraticCurveTo(x+w*.24,y+h*.84,x+w*.43,y+h*.71);brim.closePath();clip(c,brim,t,{x:x-w*.05,y,w:w*.55,h},120*sc);c.stroke(brim);
      label(c,x+w*.54,y+h*.44,w*.25,h*.18,'SIGNAL',['IN','NOISE']);
    }else{
      crown.moveTo(x+w*.12,y+h*.68);crown.quadraticCurveTo(x+w*.13,y+h*.13,cx,y+h*.07);crown.quadraticCurveTo(x+w*.87,y+h*.13,x+w*.88,y+h*.68);crown.closePath();
      clip(c,crown,t,{x,y,w,h},130*sc);c.strokeStyle='#171717';c.lineWidth=2.5*sc;c.stroke(crown);
      c.strokeStyle='rgba(230,230,230,.24)';c.beginPath();c.moveTo(cx,y+h*.08);c.lineTo(cx,y+h*.68);c.stroke();
      if(v==='back'){
        c.fillStyle='#0b0b0b';rr(c,x+w*.32,y+h*.52,w*.36,h*.22,28*sc);c.fill();
        c.strokeStyle='#1a1a1a';c.lineWidth=4*sc;c.beginPath();c.moveTo(x+w*.3,y+h*.78);c.lineTo(x+w*.72,y+h*.78);c.stroke();
        label(c,x+w*.58,y+h*.42,w*.24,h*.18,'ADVERSARIAL',['ALWAYS','EVOLVING']);
      }else{
        const brim=new Path2D();brim.moveTo(x+w*.18,y+h*.63);brim.quadraticCurveTo(cx,y+h*.68,x+w*.82,y+h*.63);brim.quadraticCurveTo(x+w*.75,y+h*.9,cx,y+h*.92);brim.quadraticCurveTo(x+w*.25,y+h*.9,x+w*.18,y+h*.63);brim.closePath();clip(c,brim,t,{x,y:y+h*.55,w,h:h*.42},125*sc);c.stroke(brim);
        label(c,x+w*.54,y+h*.36,w*.26,h*.2,familyLabel(s),['SAME','DIFFERENT','YOU']);
      }
    }
    c.fillStyle='#111';c.beginPath();c.arc(cx,y+h*.065,7*sc,0,Math.PI*2);c.fill();c.restore();
  }
  function product(c,t,type,x,y,sc,v,s){
    if(type==='hoodie')return hoodie(c,t,x,y,sc,v,s);
    if(type==='hat')return hat(c,t,x,y,sc,v,s);
    if(type==='beanie')return beanie(c,t,x,y,sc,v,s);
    if(type==='cargo')return cargo(c,t,x,y,sc,v,s);
    if(type==='mask')return mask(c,t,x,y,sc,v,s);
    return shirt(c,t,x,y,sc,v,s);
  }

  function spaced(c,text,x,y,sp,font,col='#444'){c.save();c.font=font;c.fillStyle=col;let q=x;for(const ch of text){c.fillText(ch,q,y);q+=c.measureText(ch).width+sp;}c.restore();}
  function wrap(c,text,x,y,max,lh){const words=text.split(/\s+/);let line='',yy=y;for(const word of words){const z=line?line+' '+word:word;if(c.measureText(z).width>max&&line){c.fillText(line,x,yy);line=word;yy+=lh;}else line=z;}if(line)c.fillText(line,x,yy);}
  function macro(c,t,x,y,w,h){c.save();rr(c,x,y,w,h,2);c.clip();fill(c,t,x-w*.15,y-h*.2,w*1.3,h*1.4,Math.min(w,h)*.62);c.globalAlpha=.16;c.strokeStyle='#f5f2e7';for(let i=-h;i<w+h;i+=8){c.beginPath();c.moveTo(x+i,y);c.lineTo(x+i-h,y+h);c.stroke();}c.restore();}
  function header(c,s){
    c.fillStyle='#111';c.font='900 50px Arial Black,Arial,sans-serif';c.fillText(s.productName,31,62);
    spaced(c,'ADVERSARIAL APPAREL FOR A LESS PREDICTABLE YOU',32,84,3.5,'12px Arial','#4f4f4f');
    spaced(c,'HUMAN FORM OPTIONAL',797,40,4,'10px Arial','#5e5e5e');c.strokeStyle='#555';c.beginPath();c.moveTo(993,37);c.lineTo(1070,37);c.stroke();
    c.fillStyle='#555';c.font='11px monospace';wrap(c,DESC[s.family]||'A STUDY IN SYSTEM NOISE. PATTERN AS BEHAVIOR. FORM AS A VARIABLE.',797,68,250,14);
    (VERBS[s.family]||VERBS.machine_static).forEach((v,i)=>spaced(c,v,32,115+i*19,4.3,'12px monospace','#555'));
    c.beginPath();c.moveTo(1055,98);c.lineTo(1079,98);c.moveTo(1067,86);c.lineTo(1067,110);c.stroke();
  }
  function view(c,v,x,y){spaced(c,v.toUpperCase(),x,y,3.5,'10px Arial','#686868');}
  function board(t,s){
    const cv=$('mockupCanvas'),c=cv.getContext('2d');cv.width=W;cv.height=H;c.fillStyle='#f3f1ec';c.fillRect(0,0,W,H);header(c,s);
    if(s.product==='hoodie'||s.product==='shirt'){
      product(c,t,s.product,300,470,1.08,'front',s);product(c,t,s.product,820,470,1.08,'back',s);view(c,'FRONT VIEW',245,872);view(c,'BACK VIEW',780,872);
    }else if(s.product==='hat'){
      product(c,t,'hat',300,330,1.06,'front',s);product(c,t,'hat',820,330,1.06,'side',s);product(c,t,'hat',300,655,1.06,'back',s);product(c,t,'hat',820,655,1.06,'top',s);
      view(c,'FRONT VIEW',245,505);view(c,'SIDE VIEW',780,505);view(c,'BACK VIEW',248,825);view(c,'TOP VIEW',785,825);
    }else if(s.product==='beanie'){
      product(c,t,'beanie',300,330,1.08,'front',s);product(c,t,'beanie',820,330,1.08,'side',s);product(c,t,'beanie',300,655,1.08,'back',s);product(c,t,'beanie',820,655,1.08,'slouch',s);
      view(c,'FRONT VIEW',245,500);view(c,'SIDE VIEW',780,500);view(c,'BACK VIEW',248,828);view(c,'SLOUCH FIT VIEW',740,828);
    }else if(s.product==='cargo'){
      product(c,t,'cargo',235,485,.9,'front',s);product(c,t,'cargo',560,485,.9,'back',s);product(c,t,'cargo',885,485,.9,'side',s);view(c,'FRONT VIEW',195,878);view(c,'BACK VIEW',520,878);view(c,'SIDE VIEW',850,878);
    }else{
      product(c,t,'mask',245,470,1.18,'front',s);product(c,t,'mask',560,470,1.18,'side',s);product(c,t,'mask',875,470,1.18,'back',s);view(c,'FRONT VIEW',205,862);view(c,'SIDE VIEW',523,862);view(c,'BACK VIEW',838,862);
    }
    const y=930;macro(c,t,31,y,510,302);spaced(c,'TEXTILE DETAIL',32,y+326,3.2,'10px Arial','#222');spaced(c,'DIGITAL PRINT PREVIEW / REPEAT TILE / POD CONCEPT',32,y+346,2.5,'8px Arial','#969696');
    c.strokeStyle='#777';c.beginPath();c.moveTo(575,y+20);c.lineTo(597,y+20);c.stroke();spaced(c,'PATTERN STRATEGY',575,y+60,3.4,'11px Arial','#222');c.font='10px monospace';c.fillStyle='#7b7b7b';(S[s.family]||S.machine_static).forEach((v,i)=>c.fillText('— '+v,575,y+93+i*21));
    spaced(c,T[s.product]||'LESS NOISE. MORE YOU.',575,y+280,3.2,'14px Arial','#666');spaced(c,`${s.collection}™ / TOKYO — EVERYWHERE`,32,1334,2.8,'10px Arial','#8a8a8a');
    c.fillStyle='#111';c.font='900 18px Arial Black,Arial,sans-serif';c.fillText(familyLabel(s),885,1330);spaced(c,'ADVERSARIAL APPAREL',887,1347,2.2,'8px Arial','#777');
    c.fillStyle='#8a8a8a';c.font='9px monospace';c.fillText('DIGITAL CONCEPT — VERIFY VENDOR TEMPLATE BEFORE ORDER.',575,1380);
  }
  function mkManifest(s){
    return {
      schema_version:'1.1',generated_at:new Date().toISOString(),brand:s.brand,collection:s.collection,product:s.product,product_name:s.productName,
      art_direction_profile:'canonical_launch_capsule_v1',reference_target:FAMILY_TITLE[s.family]||s.family,
      design:{family:s.family,seed:s.seed,scale:s.scale,density:s.density,distress:s.distress,repeat:'tile',master_export_px:4096},
      outputs:{reference_board_px:[W,H],production_tile_px:[4096,4096]},production_status:'digital_design_ready',pod_status:'requires provider-specific print-template mapping'
    };
  }
  function render(){
    const s=state();tile=makeTile(1024,s);const p=$('studioPatternCanvas'),x=p.getContext('2d');x.clearRect(0,0,p.width,p.height);x.drawImage(tile,0,0,p.width,p.height);board(tile,s);manifest=mkManifest(s);$('studioStatus').textContent=`READY · ${s.family.replaceAll('_',' ').toUpperCase()} · SEED ${s.seed}`;
  }
  function dl(url,name){const a=document.createElement('a');a.download=name;a.href=url;a.click();}
  function exportMockup(){if(!tile)render();dl($('mockupCanvas').toDataURL('image/png'),`rac_${state().product}_${Date.now()}_reference-board.png`);}
  function exportTile(){const s=state();$('studioStatus').textContent='BUILDING 4096 PX PRODUCTION TILE…';requestAnimationFrame(()=>{const t=makeTile(4096,s);dl(t.toDataURL('image/png'),`rac_${s.family}_seed-${s.seed}_4096.png`);$('studioStatus').textContent='READY · 4096 PX TILE EXPORTED';});}
  function exportManifest(){if(!manifest)render();const b=new Blob([JSON.stringify(manifest,null,2)],{type:'application/json'}),a=document.createElement('a');a.download=`rac_${state().product}_${Date.now()}_manifest.json`;a.href=URL.createObjectURL(b);a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
  function next(){$('studioSeed').value=(+$('studioSeed').value+37)%1000;sync('studioSeed');render();}
  function init(){
    ['studioSeed','studioScale','studioDensity','studioDistress'].forEach(id=>{sync(id);$(id).addEventListener('input',()=>sync(id));});
    $('productType').addEventListener('change',()=>{defaults();render();});$('designFamily').addEventListener('change',()=>{defaults();render();});$('productName').addEventListener('input',()=>{$('productName').dataset.edited='true';});defaults(true);render();
  }
  return{init,renderAll:render,exportMockup,exportTile,exportManifest,nextVariation:next};
})();
window.addEventListener('DOMContentLoaded',RACStudio.init);
