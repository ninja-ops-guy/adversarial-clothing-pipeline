(function(){
'use strict';
const profiles={
signal_shadow:{id:'signal_shadow',target_ratios:{dark:[.58,.78],cream_gray:[.16,.30],blue:[.015,.06],yellow:[.015,.06],negative_space:[.12,.28]},hero:{required:true,count:[1,2],size_fraction:[.18,.34]},variation_limits:{scale:[42,68],density:[58,82],distress:[60,88]},direction:'vertical_modest'},
machine_static:{id:'machine_static',target_ratios:{dark:[.62,.82],cream_gray:[.14,.28],blue:[.01,.05],yellow:[.01,.05]},hero:{required:false,count:[0,1],size_fraction:[.08,.20]},variation_limits:{scale:[36,60],density:[68,90],distress:[70,94]},direction:'vertical_strong'},
ghost_hound:{id:'ghost_hound',target_ratios:{dark:[.50,.70],cream_gray:[.22,.38],blue:[.02,.07],yellow:[.02,.07]},hero:{required:true,count:[1,3],size_fraction:[.22,.40]},variation_limits:{scale:[50,74],density:[58,80],distress:[60,84]},direction:'mixed'},
broken_human:{id:'broken_human',target_ratios:{dark:[.46,.66],cream_gray:[.24,.42],blue:[.02,.07],yellow:[.02,.07]},hero:{required:true,count:[1,3],size_fraction:[.24,.44]},variation_limits:{scale:[56,80],density:[60,82],distress:[58,82]},direction:'mixed_asymmetric'},
error_garden:{id:'error_garden',target_ratios:{dark:[.42,.62],cream_gray:[.10,.24],pink:[.08,.20],olive:[.08,.20],blue_yellow:[.02,.08]},hero:{required:true,count:[8,18],size_fraction:[.10,.30]},variation_limits:{scale:[52,76],density:[64,84],distress:[46,70]},direction:'neutral'}
};
const productLayouts={
hat:{family:'signal_shadow',hero_zones:[{x:.10,y:.08,w:.55,h:.44,weight:1},{x:.52,y:.16,w:.38,h:.38,weight:.55}],suppression_zones:[]},
mask:{family:'machine_static',hero_zones:[{x:.25,y:.42,w:.5,h:.48,weight:1}],suppression_zones:[{x:.18,y:.22,w:.64,h:.20}]},
beanie:{family:'ghost_hound',hero_zones:[{x:.12,y:.08,w:.76,h:.48,weight:1}],suppression_zones:[{x:.05,y:.72,w:.90,h:.18}]},
cargo:{family:'broken_human',hero_zones:[{x:.04,y:.10,w:.40,h:.72,weight:1},{x:.56,y:.18,w:.40,h:.70,weight:.8}],suppression_zones:[{x:.08,y:.28,w:.28,h:.16},{x:.64,y:.28,w:.28,h:.16},{x:.10,y:.56,w:.28,h:.14},{x:.62,y:.56,w:.28,h:.14}]},
shirt:{family:'error_garden',hero_zones:[{x:.16,y:.16,w:.68,h:.60,weight:1}],suppression_zones:[{x:.38,y:.02,w:.24,h:.12},{x:0,y:.08,w:.07,h:.84},{x:.93,y:.08,w:.07,h:.84}]},
hoodie:{family:'machine_static',hero_zones:[{x:.18,y:.18,w:.64,h:.58,weight:1}],suppression_zones:[{x:.38,y:.02,w:.24,h:.15}]}
};
function getProfile(f){return profiles[f]||null} function getProductLayout(p){return productLayouts[p]||null}
function clamp(v,r){return Math.max(r[0],Math.min(r[1],Number(v)))}
function resolveProfile({family,product,mode='creative',controls={}}){const p=getProfile(family),layout=getProductLayout(product);if(!p)return{...controls,family,product,mode,profile:null,layout};const c={...controls};if(mode==='reference'){for(const k of ['scale','density','distress'])c[k]=clamp(c[k],p.variation_limits[k]);}return{...c,family,product,mode,profile:p,layout};}
window.RACStyleProfiles={profiles,productLayouts,getProfile,getProductLayout,resolveProfile};
})();