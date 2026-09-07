(function(){
  if(typeof patternGenerators==='undefined'||typeof colorPalettes==='undefined'){
    throw new Error('studio-patterns.js requires core.js');
  }

  colorPalettes.rac_reference=['#080808','#151515','#343434','#777777','#d8ccb6','#155bd8','#e7df16'];
  colorPalettes.error_garden=['#080808','#222222','#d9cdb9','#7b8756','#d98ca4','#2b62d8','#eadf1a'];

  function pick(r,a){return a[Math.floor(r()*a.length)];}
  function rgba(hex,a){
    const v=hex.replace('#','');
    return `rgba(${parseInt(v.slice(0,2),16)},${parseInt(v.slice(2,4),16)},${parseInt(v.slice(4,6),16)},${a})`;
  }
  function wrapRect(c,s,x,y,w,h){
    const xs=[x,x-s,x+s],ys=[y,y-s,y+s];
    for(const xx of xs)for(const yy of ys)c.fillRect(xx,yy,w,h);
  }
  function patchField(c,s,pal,r,p,opts={}){
    const dark=opts.dark||'#080808';
    const neutral=opts.neutral||pal.slice(1,5);
    const accents=opts.accents||pal.slice(5);
    const sc=Math.max(.52,p.patternScale/52);
    c.fillStyle=dark;c.fillRect(0,0,s,s);

    const large=Math.floor(24+p.colorVariance*.26);
    for(let i=0;i<large;i++){
      const vertical=r()>.52;
      const w=(vertical?12+r()*56:42+r()*150)*sc;
      const h=(vertical?48+r()*190:12+r()*58)*sc;
      const x=r()*s,y=r()*s;
      const useAccent=r()<(.07+p.colorVariance/850);
      c.globalAlpha=useAccent?.92:.44+r()*.42;
      c.fillStyle=useAccent?pick(r,accents):pick(r,neutral);
      wrapRect(c,s,x,y,w,h);
      if(r()>.34){
        c.globalAlpha=.42+r()*.32;c.fillStyle=dark;
        const cuts=2+Math.floor(r()*7);
        for(let k=0;k<cuts;k++){
          if(vertical)wrapRect(c,s,x+r()*w,y,Math.max(1,w*(.04+r()*.12)),h);
          else wrapRect(c,s,x,y+r()*h,w,Math.max(1,h*(.04+r()*.12)));
        }
      }
    }

    c.globalAlpha=1;
    const lineCount=Math.floor(110+p.edgeIntensity*2.5);
    for(let i=0;i<lineCount;i++){
      const x=r()*s,y=r()*s,horizontal=r()>.28;
      const len=(4+r()*(horizontal?66:28))*sc;
      c.strokeStyle=rgba(r()<.12?pick(r,accents):pick(r,neutral),.25+r()*.58);
      c.lineWidth=Math.max(.7,(.7+r()*1.8)*sc);
      c.beginPath();c.moveTo(x,y);c.lineTo(x+(horizontal?len:r()*4),y+(horizontal?r()*3:len));c.stroke();
    }

    const clusters=Math.floor(34+p.edgeIntensity*1.25);
    for(let i=0;i<clusters;i++){
      const cell=Math.max(2,Math.round((2+r()*6)*sc));
      const cols=2+Math.floor(r()*8),rows=1+Math.floor(r()*5);
      const x0=r()*s,y0=r()*s,col=r()<.18?pick(r,accents):pick(r,neutral);
      for(let yy=0;yy<rows;yy++)for(let xx=0;xx<cols;xx++)if(r()>.42){
        c.globalAlpha=.42+r()*.48;c.fillStyle=col;
        wrapRect(c,s,x0+xx*cell,y0+yy*cell,cell*.72,cell*.72);
      }
    }
    c.globalAlpha=1;
  }
  function grainChannels(c,s,r,p,count=14){
    c.save();c.globalAlpha=.46;c.strokeStyle='#d8ccb6';c.lineWidth=Math.max(1,s/950);
    for(let i=0;i<count;i++){
      const x=r()*s;c.beginPath();c.moveTo(x,r()*s*.18);c.lineTo(x+(r()-.5)*s*.08,s*(.58+r()*.42));c.stroke();
    }
    for(let i=0;i<Math.floor(p.edgeIntensity/5);i++){
      const y=r()*s;c.globalAlpha=.12+r()*.2;c.fillStyle='#d8ccb6';c.fillRect(0,y,s,Math.max(1,s*.002+r()*s*.007));
    }
    c.restore();
  }
  function eye(c,x,y,rad,r,t='#d8ccb6',alpha=.92){
    c.save();c.translate(x,y);c.rotate((r()-.5)*.26);c.strokeStyle=t;c.fillStyle=t;c.globalAlpha=alpha;c.lineWidth=Math.max(2,rad*.075);
    c.beginPath();c.moveTo(-rad,0);c.quadraticCurveTo(0,-rad*.7,rad,0);c.quadraticCurveTo(0,rad*.7,-rad,0);c.stroke();
    c.beginPath();c.arc(0,0,rad*.34,0,Math.PI*2);c.fill();c.fillStyle='#0d0d0d';c.beginPath();c.arc(rad*.07,-rad*.02,rad*.16,0,Math.PI*2);c.fill();
    c.globalCompositeOperation='destination-out';
    for(let i=0;i<5+Math.floor(r()*8);i++)c.fillRect(-rad+r()*rad*2,-rad*.76+r()*rad*1.52,rad*(.08+r()*.32),rad*(.05+r()*.22));
    c.restore();
  }
  function ribs(c,x,y,rad,t='#d8ccb6'){
    c.save();c.strokeStyle=t;c.lineWidth=Math.max(1.5,rad*.034);c.globalAlpha=.78;
    c.beginPath();c.moveTo(x,y-rad*.68);c.lineTo(x,y+rad*.72);c.stroke();
    for(let i=0;i<7;i++){
      const yy=y+(i-3)*rad*.18,sp=rad*(.92-Math.abs(i-3)*.065);
      c.beginPath();c.moveTo(x,yy);c.bezierCurveTo(x-sp*.28,yy-rad*.1,x-sp*.76,yy-rad*.02,x-sp,yy+rad*.14);c.stroke();
      c.beginPath();c.moveTo(x,yy);c.bezierCurveTo(x+sp*.28,yy-rad*.1,x+sp*.76,yy-rad*.02,x+sp,yy+rad*.14);c.stroke();
    }
    c.restore();
  }
  function flower(c,x,y,rad,petals,t,r){
    c.save();c.translate(x,y);c.rotate(r()*Math.PI);c.fillStyle=t;c.globalAlpha=.72+r()*.2;
    for(let i=0;i<petals;i++){
      c.save();c.rotate(Math.PI*2*i/petals);c.beginPath();c.ellipse(rad*.58,0,rad*.64,rad*.23,0,0,Math.PI*2);c.fill();c.restore();
    }
    c.fillStyle='#111';c.beginPath();c.arc(0,0,rad*.23,0,Math.PI*2);c.fill();c.restore();
  }
  function leaf(c,x,y,len,t,r){
    c.save();c.translate(x,y);c.rotate(r()*Math.PI*2);c.fillStyle=t;c.globalAlpha=.7+r()*.18;
    c.beginPath();c.moveTo(0,0);c.quadraticCurveTo(len*.55,-len*.26,len,0);c.quadraticCurveTo(len*.55,len*.26,0,0);c.fill();c.restore();
  }
  function signalWedge(c,s,r,col){
    const x=r()*s,y=r()*s,w=s*(.035+r()*.07),h=s*(.025+r()*.055);
    c.save();c.globalAlpha=.92;c.fillStyle=col;c.beginPath();c.moveTo(x,y);c.lineTo(x+w,y+h*.18);c.lineTo(x+w*.45,y+h);c.closePath();c.fill();c.restore();
  }
  function portraitFragment(c,s,r){
    c.save();c.globalAlpha=.46;c.strokeStyle='#d8ccb6';c.lineWidth=Math.max(2,s*.005);
    const x=r()*s,y=r()*s,rad=s*(.08+r()*.06);
    c.beginPath();c.arc(x,y,rad,Math.PI*.82,Math.PI*1.85);c.stroke();
    c.beginPath();c.moveTo(x-rad*.18,y+rad*.34);c.lineTo(x+rad*.5,y+rad*.62);c.stroke();c.restore();
  }

  patternGenerators.machine_static=function(c,s,p,pal,r){
    patchField(c,s,colorPalettes.rac_reference,r,p);
    grainChannels(c,s,r,p,18);
    c.save();c.globalAlpha=.28;c.fillStyle='#d8ccb6';
    for(let i=0;i<7;i++)c.fillRect(r()*s,r()*s,s*(.006+r()*.012),s*(.12+r()*.28));
    c.restore();
    applyFeatureMotifs(c,s,p,r);
  };

  patternGenerators.signal_shadow=function(c,s,p,pal,r){
    patchField(c,s,colorPalettes.rac_reference,r,p,{dark:'#090909'});
    grainChannels(c,s,r,p,11);
    const eyes=2+Math.floor(Math.min(2,p.colorVariance/45));
    for(let i=0;i<eyes;i++)eye(c,r()*s,r()*s,s*(.07+r()*.08),r,'#d8ccb6',.72+r()*.18);
    for(let i=0;i<4;i++)signalWedge(c,s,r,i%2?'#155bd8':'#e7df16');
    for(let i=0;i<3;i++)portraitFragment(c,s,r);
    applyFeatureMotifs(c,s,p,r);
  };

  patternGenerators.ghost_hound=function(c,s,p,pal,r){
    patchField(c,s,colorPalettes.rac_reference,r,p,{dark:'#080808'});
    const count=2+Math.floor(p.patternScale/46);
    for(let i=0;i<count;i++)eye(c,r()*s,r()*s,s*(.105+r()*.095),r,'#d8ccb6',.9);
    for(let i=0;i<3;i++)signalWedge(c,s,r,i===1?'#e7df16':'#155bd8');
    c.save();c.globalAlpha=.55;c.fillStyle='#d8ccb6';
    for(let i=0;i<3;i++){const x=r()*s,y=r()*s,rad=s*(.04+r()*.05);c.beginPath();c.moveTo(x,y);c.lineTo(x+rad,y-rad*1.25);c.lineTo(x+rad*1.55,y+rad*.15);c.closePath();c.fill();}
    c.restore();
    applyFeatureMotifs(c,s,p,r);
  };

  patternGenerators.broken_human=function(c,s,p,pal,r){
    patchField(c,s,colorPalettes.rac_reference,r,p,{dark:'#080808'});
    eye(c,s*(.22+r()*.18),s*(.22+r()*.28),s*(.12+r()*.05),r,'#d8ccb6',.92);
    eye(c,s*(.55+r()*.28),s*(.58+r()*.22),s*(.08+r()*.055),r,'#d8ccb6',.82);
    ribs(c,s*(.46+r()*.22),s*(.42+r()*.26),s*(.16+r()*.05));
    for(let i=0;i<4;i++)signalWedge(c,s,r,i%2?'#155bd8':'#e7df16');
    portraitFragment(c,s,r);
    applyFeatureMotifs(c,s,p,r);
  };

  function applyFeatureMotifs(c,s,p,r){
    const motifs=Array.isArray(p.featureMotifs)?p.featureMotifs:[];
    for(const motif of motifs){
      if(motif==='canine_eye')eye(c,r()*s,r()*s,s*(.08+r()*.08),r,'#d8ccb6',.92);
      else if(motif==='human_eye')eye(c,r()*s,r()*s,s*(.06+r()*.065),r,'#d8ccb6',.78);
      else if(motif==='rib')ribs(c,r()*s,r()*s,s*(.12+r()*.07),'#d8ccb6');
      else if(motif==='floral')for(let i=0;i<3;i++)flower(c,r()*s,r()*s,s*(.035+r()*.06),6+Math.floor(r()*5),r()>.5?'#d98ca4':'#d9cdb9',r);
      else if(motif==='glitch'){c.save();for(let i=0;i<12;i++){c.globalAlpha=.45+r()*.45;c.fillStyle=r()>.5?'#155bd8':'#d98ca4';wrapRect(c,s,r()*s,r()*s,s*(.012+r()*.04),s*(.008+r()*.025));}c.restore();}
      else if(motif==='slash')for(let i=0;i<3;i++)signalWedge(c,s,r,i%2?'#155bd8':'#e7df16');
      else if(motif==='static')grainChannels(c,s,r,p,22);
      else if(motif==='leaf')for(let i=0;i<5;i++)leaf(c,r()*s,r()*s,s*(.04+r()*.09),'#7b8756',r);
      else if(motif==='data'){c.save();c.strokeStyle='#d8ccb6';c.globalAlpha=.55;for(let i=0;i<12;i++){const x=r()*s,y=r()*s;c.beginPath();c.moveTo(x,y);c.lineTo(x,y+s*(.03+r()*.15));c.stroke();}c.restore();}
      else if(motif==='mask')for(let i=0;i<2;i++)portraitFragment(c,s,r);
    }
  }

  patternGenerators.error_garden=function(c,s,p,pal,r){
    patchField(c,s,colorPalettes.error_garden,r,p,{dark:'#080808'});
    const flowers=['#d98ca4','#d9cdb9','#7b8756'];
    for(let i=0;i<8+Math.floor(p.colorVariance/10);i++)flower(c,r()*s,r()*s,s*(.045+r()*.085),6+Math.floor(r()*6),pick(r,flowers),r);
    for(let i=0;i<11;i++)leaf(c,r()*s,r()*s,s*(.05+r()*.11),r()>.52?'#7b8756':'#d9cdb9',r);
    eye(c,s*(.26+r()*.5),s*(.28+r()*.45),s*(.08+r()*.05),r,'#d8ccb6',.72);
    if(r()>.45)eye(c,r()*s,r()*s,s*(.055+r()*.04),r,'#d8ccb6',.55);
    for(let i=0;i<4;i++)signalWedge(c,s,r,i%2?'#2b62d8':'#eadf1a');
    applyFeatureMotifs(c,s,p,r);
  };

  function deriveSeed(base,label){let h=(Number(base)>>>0)||1;for(let i=0;i<label.length;i++){h^=label.charCodeAt(i);h=Math.imul(h,16777619)>>>0;}return h%2147483647;}
  function buildStyleSpec(family,params,seed,product=null,mode='creative'){
    const resolved=window.RACStyleProfiles?RACStyleProfiles.resolveProfile({family,product,mode,controls:{scale:params.patternScale??params.scale??52,density:params.colorVariance??params.density??72,distress:params.edgeIntensity??params.distress??76}}):{scale:params.patternScale,density:params.colorVariance,distress:params.edgeIntensity,profile:null,layout:null};
    const profile=resolved.profile,layout=resolved.layout,seeds={base:deriveSeed(seed,'base'),hero:deriveSeed(seed,'hero'),structure:deriveSeed(seed,'structure'),secondary:deriveSeed(seed,'secondary'),grain:deriveSeed(seed,'grain'),accents:deriveSeed(seed,'accents')};
    const zones=layout?.hero_zones||[{x:.1,y:.1,w:.8,h:.8,weight:1}],rng=seededRandom(seeds.hero),zone=zones[Math.floor(rng()*zones.length)]||zones[0],heroRequired=!!profile?.hero?.required;
    const heroCount=heroRequired?Math.max(1,Math.round((profile.hero.count[0]+profile.hero.count[1])/2)):0,heroArea=profile?.hero?((profile.hero.size_fraction[0]+profile.hero.size_fraction[1])/2):.18;
    return{family,product,mode,seed,seeds,featureMotifs:Array.isArray(params.featureMotifs)?[...params.featureMotifs]:[],controls:{scale:resolved.scale,density:resolved.density,distress:resolved.distress},profile,layout,hero:{count:heroCount,area_ratio:heroArea,zone,center:{x:zone.x+zone.w*(.25+rng()*.5),y:zone.y+zone.h*(.25+rng()*.5)}},suppression_overlap:0};
  }
  function renderFamilyFromSpec(ctx,size,spec){
    const p={patternType:spec.family,patternScale:spec.controls.scale,colorVariance:spec.controls.density,edgeIntensity:spec.controls.distress,symmetry:0,seed:spec.seed,featureMotifs:spec.featureMotifs||[]},pal=colorPalettes[spec.family==='error_garden'?'error_garden':'rac_reference'],g=patternGenerators[spec.family];
    if(!g)throw new Error('Missing pattern family: '+spec.family);g(ctx,size,p,pal,seededRandom(spec.seed));
  }
  function analyzeComposition(ctx,size,spec){
    const d=ctx.getImageData(0,0,size,size).data;let dark=0,cream=0,blue=0,yellow=0,pink=0,olive=0,hi=0,n=0,ve=0,he=0,edges=0;
    const step=Math.max(1,Math.floor(size/96));
    function lum(i){return .2126*d[i]+.7152*d[i+1]+.0722*d[i+2]}
    for(let y=0;y<size;y+=step)for(let x=0;x<size;x+=step){const i=(y*size+x)*4,r=d[i],g=d[i+1],b=d[i+2],l=lum(i);n++;if(l<70)dark++;if(l>120&&Math.abs(r-g)<35&&Math.abs(g-b)<35)cream++;if(b>r*1.2&&b>g*1.1)blue++;if(r>150&&g>140&&b<110)yellow++;if(r>130&&r>b*1.1&&b>80)pink++;if(g>r*.8&&r>60&&b<r*.85)olive++;if(l<45||l>190)hi++;if(x+step<size){const j=(y*size+x+step)*4,dd=Math.abs(l-lum(j));he+=dd;if(dd>45)edges++;}if(y+step<size){const j=((y+step)*size+x)*4,dd=Math.abs(l-lum(j));ve+=dd;if(dd>45)edges++;}}
    return{palette:{dark:dark/n,dark_ratio:dark/n,cream_gray:cream/n,cream_gray_ratio:cream/n,blue:blue/n,blue_ratio:blue/n,yellow:yellow/n,yellow_ratio:yellow/n,pink:pink/n,pink_ratio:pink/n,olive:olive/n,olive_ratio:olive/n,blue_yellow:(blue+yellow)/n},edges:{horizontal_energy:he/Math.max(1,n)/255,vertical_energy:ve/Math.max(1,n)/255,directional_bias:(ve-he)/Math.max(1,ve+he)},occupancy:{high_contrast_ratio:hi/n,negative_space_ratio:dark/n,connected_region_count:Math.max(1,Math.round(edges/25))},motifs:{hero_count:spec?.hero?.count||0,hero_area_ratio:spec?.hero?.area_ratio||0,eye_count:['signal_shadow','ghost_hound','broken_human'].includes(spec?.family)?spec.hero.count:0,anatomy_count:spec?.family==='broken_human'?1:0,floral_count:spec?.family==='error_garden'?Math.max(8,spec.hero.count):0,accent_cluster_count:Math.round((blue+yellow)/Math.max(1,n)*20)}};
  }
  window.RACPatternComposition={deriveSeed,buildStyleSpec,renderFamilyFromSpec,analyzeComposition};

})();