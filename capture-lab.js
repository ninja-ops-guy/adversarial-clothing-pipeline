(function(){
'use strict';
const $=id=>document.getElementById(id);
const STEPS=['Experiment','Calibration','Control','Candidate','Motion','Review','Seal'];
let stream=null,recorder=null,chunks=[],arm='control',frozen=null,sealed=false;
const captures={control:{stills:[],videos:[]},candidate:{stills:[],videos:[]}};
function now(){return new Date().toISOString()}\nfunction stable(v){if(Array.isArray(v))return v.map(stable);if(v&&typeof v==='object'){const out={};Object.keys(v).sort().forEach(k=>out[k]=stable(v[k]));return out;}return v}\nfunction canonical(v){return JSON.stringify(stable(v))}
function cond(){return [+$('distance').value,+$('yaw').value,$('pose').value,$('lightingId').value].join('|')}
function hex(buf){return crypto.subtle.digest('SHA-256',buf).then(d=>[...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,'0')).join(''))}
function renderSteps(active=0){$('sopStrip').innerHTML=STEPS.map((s,i)=>'<div class="sop-step '+(i<active?'done ':i===active?'active':'')+'">'+(i+1)+' · '+s.toUpperCase()+'</div>').join('')}
function count(){for(const a of ['control','candidate'])$(a+'Count').textContent=captures[a].stills.length+' stills · '+captures[a].videos.length+' videos'}
function manifest(){
 return {schema_version:'1.0',session_id:'RAC-CAP-'+Date.now(),experiment_id:$('experimentId').value,hypothesis_id:$('hypothesisId').value,protocol_version:$('protocolVersion').value,evidence_class:$('evidenceClass').value,generation:{artifact_id:$('generationId').value,sha256:$('generationSha').value.toLowerCase()},candidate:{artifact_id:$('candidateId').value,sha256:$('candidateSha').value.toLowerCase()},control:{artifact_id:$('controlId').value},actor_id:$('actorId').value,camera_id:$('cameraId').value,lighting_id:$('lightingId').value,distance_m:+$('distance').value,yaw_deg:+$('yaw').value,pose:$('pose').value,created_at:now(),capture_blinding:'outcomes_hidden_until_capture_pair_complete',statistical_unit:'garment_x_actor_x_session',frames_are_nested:true}
}
async function freeze(){
 const m=manifest(); if(!m.experiment_id||!m.actor_id||!m.camera_id) return alert('Experiment, actor, and camera IDs are required.');
 if(m.candidate.sha256&&!/^[0-9a-f]{64}$/.test(m.candidate.sha256)) return alert('Candidate SHA-256 must be 64 hex characters or blank for a pre-freeze prototype.');\n if(m.generation.sha256&&!/^[0-9a-f]{64}$/.test(m.generation.sha256)) return alert('Generation SHA-256 must be 64 hex characters or blank for a prototype.');
 const bytes=new TextEncoder().encode(canonical(m));m.freeze_sha256=await hex(bytes);frozen=m;
 ['experimentId','hypothesisId','protocolVersion','evidenceClass','generationId','generationSha','candidateId','candidateSha','controlId','actorId','cameraId','lightingId','distance','yaw','pose'].forEach(id=>$(id).disabled=true);
 $('freezeBtn').disabled=true;$('stillBtn').disabled=!stream;$('recordBtn').disabled=!stream;$('instrumentStatus').textContent='FROZEN · '+m.freeze_sha256.slice(0,16)+'…';$('conditionBanner').textContent='CONTROL · '+cond();renderSteps(1)
}
async function camera(){try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});$('camera').srcObject=stream;$('cameraBtn').textContent='Camera Ready';$('cameraBtn').disabled=true;$('stillBtn').disabled=!frozen;$('recordBtn').disabled=!frozen;$('capturePrompt').textContent='FRAMING GUIDE · OUTCOMES BLINDED'}catch(e){$('instrumentStatus').textContent='CAMERA ERROR · '+e.message}}
async function still(){
 if(!frozen||sealed)return;const v=$('camera'),c=document.createElement('canvas');c.width=v.videoWidth||1280;c.height=v.videoHeight||720;c.getContext('2d').drawImage(v,0,0,c.width,c.height);
 const blob=await new Promise(r=>c.toBlob(r,'image/jpeg',.95));const bytes=await blob.arrayBuffer();const rec={id:arm+'-still-'+(captures[arm].stills.length+1),arm,type:'still',condition:cond(),timestamp:now(),sha256:await hex(bytes),blob};captures[arm].stills.push(rec);ledger(rec);count();renderSteps(arm==='control'?2:3)
}
function startRecord(){if(!stream||!frozen||sealed)return;chunks=[];recorder=new MediaRecorder(stream,{mimeType:MediaRecorder.isTypeSupported('video/webm;codecs=vp9')?'video/webm;codecs=vp9':'video/webm'});recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};recorder.onstop=finishRecord;recorder.start(250);$('recordBtn').disabled=true;$('stopBtn').disabled=false;$('capturePrompt').textContent='RECORDING '+arm.toUpperCase()+' · '+$('pose').value.toUpperCase()}
async function finishRecord(){const blob=new Blob(chunks,{type:recorder.mimeType});const bytes=await blob.arrayBuffer();const rec={id:arm+'-video-'+(captures[arm].videos.length+1),arm,type:'motion',condition:cond(),timestamp:now(),sha256:await hex(bytes),blob};captures[arm].videos.push(rec);ledger(rec);count();$('recordBtn').disabled=false;$('stopBtn').disabled=true;$('capturePrompt').textContent='FRAMING GUIDE · OUTCOMES BLINDED';renderSteps(4)}
function stopRecord(){if(recorder&&recorder.state!=='inactive')recorder.stop()}
function ledger(r){const tr=document.createElement('tr');tr.innerHTML='<td>'+r.timestamp+'</td><td>'+r.arm+'</td><td>'+r.type+'</td><td>'+r.condition+'</td><td>'+r.sha256+'</td>';$('ledger').appendChild(tr)}
function switchArm(a){arm=a;document.querySelectorAll('.arm').forEach(b=>b.classList.toggle('active',b.dataset.arm===a));$('conditionBanner').textContent=a.toUpperCase()+' · '+cond()}
function review(){
 const same=captures.control.stills.length>0&&captures.candidate.stills.length>0;
 if(!same)return alert('At least one still is required for both control and candidate before review.');
 $('analyzeBtn').disabled=false;$('exportBtn').disabled=false;$('sealBtn').disabled=false;$('analysisStatus').textContent='CAPTURE PAIR VALID · analysis may now run without changing capture.';renderSteps(5)
}
function analyze(){
 let mm;try{mm=JSON.parse($('modelManifest').value)}catch(e){return alert('Model manifest JSON is invalid.')}
 if(!Array.isArray(mm.models)||typeof mm.thresholds!=='object')return alert('Frozen model manifest requires models[] and thresholds{}.');
 $('modelManifest').disabled=true;$('analyzeBtn').disabled=true;
 const payload={schema_version:'1.0',status:'analysis_pending_local_runner',session_freeze_sha256:frozen.freeze_sha256,models:mm.models,thresholds:mm.thresholds,preprocessing:mm.preprocessing||{},motion_sampling:mm.motion_sampling||null,identity_mode:mm.identity_mode||'disabled',note:'Use scripts/analyze_capture_session.py or an authorized local runner. Browser does not fabricate inference.'};
 $('analysisStatus').textContent='ANALYSIS CONTRACT FROZEN · '+mm.models.length+' models · export bundle for local runner.';frozen.analysis_contract=payload
}
async function exportBundle(){
 const files=[];const session={...frozen,calibration_pass:$('calibrationPass').checked,sealed,captures:{control:{stills:[],videos:[]},candidate:{stills:[],videos:[]}}};
 for(const a of ['control','candidate'])for(const t of ['stills','videos'])for(const r of captures[a][t]){const ext=r.type==='still'?'jpg':'webm',name=a+'/'+r.id+'.'+ext;files.push({name,blob:r.blob});session.captures[a][t].push({...r,blob:undefined,path:name})}
 const data=new Blob([JSON.stringify(session,null,2)],{type:'application/json'});download(data,(frozen.session_id||'rac-capture')+'-session.json');
 for(const f of files)download(f.blob,(frozen.session_id||'rac-capture')+'-'+f.name.replaceAll('/','-'))
}
function download(blob,name){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
async function seal(){if(!$('calibrationPass').checked)return alert('Calibration must pass before sealing a physical evidence session.');if(!captures.control.stills.length||!captures.candidate.stills.length)return alert('Matched capture pair incomplete.');sealed=true;$('sealBtn').disabled=true;$('stillBtn').disabled=true;$('recordBtn').disabled=true;$('reviewBtn').disabled=true;$('sealStatus').textContent='SEALED · IMMUTABLE CAPTURE SESSION';renderSteps(6);await exportBundle()}
function preset(name){
 const sets={
  surrogate:{models:['yolov8n','fasterrcnn_mobilenet_v3_320','detr_resnet50','ssdlite320_mobilenet_v3','retinanet_resnet50_fpn_v2','fcos_resnet50_fpn']},
  heldout:{models:['fasterrcnn_resnet50_fpn_v2','maskrcnn_resnet50_fpn_v2']}
 };
 if(name==='custom')return;
 const models=sets[name].models,thresholds=Object.fromEntries(models.map(m=>[m,0.5]));
 $('modelManifest').value=JSON.stringify({models,thresholds,preprocessing:{source:'frozen model manifests'},motion_sampling:{fps:2.0,max_frames:120,aggregation:'sequence_fraction',sequence_detection_threshold:0.5},identity_mode:'disabled'},null,2)
}
function init(){renderSteps(0);count();$('ensemblePreset').onchange=()=>preset($('ensemblePreset').value);$('freezeBtn').onclick=freeze;$('cameraBtn').onclick=camera;$('stillBtn').onclick=still;$('recordBtn').onclick=startRecord;$('stopBtn').onclick=stopRecord;$('reviewBtn').onclick=review;$('analyzeBtn').onclick=analyze;$('exportBtn').onclick=exportBundle;$('sealBtn').onclick=seal;document.querySelectorAll('.arm').forEach(b=>b.onclick=()=>switchArm(b.dataset.arm));$('calibrationPass').onchange=()=>{$('calibrationGate').querySelector('span').textContent=$('calibrationPass').checked?'PASS':'Pending'}}
window.RACCaptureLab={manifest,freeze,review,analyze,seal,getState:()=>({frozen,sealed,captures})};window.addEventListener('DOMContentLoaded',init)
})();