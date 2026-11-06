// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
'use strict';
const $=id=>document.getElementById(id);
const state={devices:[],catalog:[],fullCatalog:[],capabilities:null,power:null,device:null,page:'overview',section:'System',rows:[],revision:0,console:null,socket:null,frameURL:null,drafts:new Map(),settingsBusy:false,settingsPosting:false,settingsReview:null,settingsNeedsRefresh:false};
const icons={System:'▦',Logs:'▤',Hardware:'◈',Controller:'▣',Access:'♙',Alerts:'♧',Console:'▻',Maintenance:'⚙'};
const show=(id,yes)=>{$(id).hidden=!yes;};
const text=(id,value)=>{$(id).textContent=value;};
function toast(message){text('toast',message);show('toast',true);clearTimeout(toast.timer);toast.timer=setTimeout(()=>show('toast',false),6000);}
async function api(path,options={}){
 const response=await fetch('/api'+path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...(options.headers||{})}});
 let body={};try{body=await response.json();}catch{}
 if(!response.ok){if(response.status===401 && path!='/login')signedOut();throw Error(typeof body.detail==='string'?body.detail:'The request could not be completed.');}
 return body;
}
function signedOut(){resetSettings();closeConsole();closeSol();show('app',false);show('login-view',true);state.rows=[];state.devices=[];$('login-password').value='';}
function current(){return state.devices.find(d=>d.id===state.device);}
async function signedIn(){
 show('login-view',false);show('app',true);state.fullCatalog=await api('/catalog');state.catalog=state.fullCatalog;await reloadDevices();renderNavigation();selectPage(state.page);
}
function useCapabilities(capabilities){
 state.capabilities=capabilities;
 state.catalog=capabilities?state.fullCatalog.filter(p=>capabilities.pages.includes(p.id)):state.fullCatalog.filter(p=>p.id==='overview');
 if(!state.catalog.some(p=>p.id===state.page))state.page=state.catalog[0]?.id||'overview';
 renderDevice();renderNavigation();renderTabs();
}
async function reloadDevices(){
 state.devices=await api('/devices');if(!state.devices.some(d=>d.id===state.device))state.device=state.devices[0]?.id||null;
 $('device-picker').replaceChildren();for(const device of state.devices){const option=new Option(device.name,device.id);$('device-picker').add(option);}if(state.device)$('device-picker').value=state.device;
 useCapabilities(current()?.connected?await api(`/devices/${state.device}/capabilities`):null);renderDevices();
}
function renderDevice(){
 const device=current();
 const writable=device?.settings_writable&&state.capabilities?.settings;
 text('workspace-mode',writable?'STAGED EDITS':'VIEW ONLY');text('field-mode',writable?'Changes require confirmation':'Read-only connection');text('access-mode',writable?'Confirmed edits':state.capabilities?'Confirmed power':'Not connected');text('access-mode-note',state.capabilities?'Review before sending':'Connect to detect capabilities');text('access-pill',state.capabilities?'CONFIRMATION REQUIRED':'NOT CONNECTED');text('sidebar-mode',writable?'Confirmation required':'Read-only mode');text('sidebar-mode-note',writable?'KVM input starts off':'No power or configuration changes');
 text('crumb-device',device?.name||'No device selected');text('summary-name',device?.name||'No devices');text('summary-address',device?.address||'Add a device to begin');
 show('sol',Boolean(state.capabilities?.sol));$('sol').disabled=!device?.connected||state.settingsBusy;
 show('kvm',Boolean(state.capabilities?.kvm));text('device-subtitle',device?`${device.address} · ${device.username} · ${state.capabilities?.source||'Management controller'}`:'Add your first DRAC in Manage devices.');text('summary-connection',device?.connected?'Connected':'Disconnected');text('summary-connection-note',device?.connected?'Status connection is active':'Ready when you are');
 text('connect',device?.connected?'Disconnect':'Connect device');$('connect').disabled=!device||state.settingsBusy;$('empty-connect').disabled=!device;$('refresh').disabled=!device?.connected||state.settingsBusy;$('kvm').disabled=!device?.has_password||state.settingsBusy;
}
function renderNavigation(){
 $('navigation').replaceChildren();for(const section of [...new Set(state.catalog.map(p=>p.section))]){const button=document.createElement('button');button.className=section===state.section?'active':'';button.setAttribute('aria-current',section===state.section?'page':'false');const icon=document.createElement('span');icon.textContent=icons[section]||'◇';button.append(icon,document.createTextNode(section));const count=document.createElement('small');count.textContent=state.catalog.filter(p=>p.section===section).length;button.append(count);button.onclick=()=>{const page=state.catalog.find(p=>p.section===section);selectPage(page.id);};$('navigation').append(button);}
}
function renderTabs(){
 $('subtabs').replaceChildren();for(const page of state.catalog.filter(p=>p.section===state.section)){const button=document.createElement('button');button.textContent=page.title;button.className=page.id===state.page?'active':'';button.setAttribute('role','tab');button.setAttribute('aria-selected',String(page.id===state.page));button.onclick=()=>selectPage(page.id);$('subtabs').append(button);}
}
function renderActions(){
 $('actions').replaceChildren();const power=state.page==='power'?state.power:null;
 show('actions',Boolean(power));if(!power)return;
 const note=document.createElement('p');note.textContent=`Power is ${power.state.toLowerCase()} · Every action requires confirmation.`;$('actions').append(note);
 for(const action of power.actions){if(action.supported===false)continue;const button=document.createElement('button');button.disabled=!action.enabled||state.settingsBusy||state.settingsNeedsRefresh;button.textContent=action.label;button.title=action.reason||`Review ${action.label.toLowerCase()} via ${action.source}`;button.onclick=()=>reviewPower(action.id);$('actions').append(button);}
}
function accessLabel(mode,editable=false){return mode==='configurable'?(editable?'Configurable':'Configurable · locked'):mode==='read-only'?'Read only':'Unverified';}
function fieldValueNode(row){
 const value=document.createElement('span');
 if(fieldEditable(row)){
  const edit=row.edit,raw=state.drafts.has(row.key)?state.drafts.get(row.key):edit.value;
  value.className='field-editor'+(state.drafts.has(row.key)?' pending-field':'');
  if(edit.type==='boolean'||edit.type==='choice'&&edit.choices.length===2&&edit.choices.some(c=>c.value==='0')&&edit.choices.some(c=>c.value==='1')){
   value.classList.add('binary-value');const toggle=document.createElement('input');toggle.type='checkbox';toggle.setAttribute('role','switch');toggle.setAttribute('aria-label',row.field);toggle.checked=raw==='1';toggle.disabled=state.settingsBusy;
   const caption=document.createElement('span'),captionFor=v=>edit.type==='boolean'?(v==='1'?edit.on:edit.off):edit.choices.find(c=>c.value===v)?.label||v;
   caption.textContent=captionFor(raw);toggle.onchange=()=>{const v=toggle.checked?'1':'0';stageSetting(row,v);caption.textContent=captionFor(v);value.classList.toggle('pending-field',state.drafts.has(row.key));};value.append(toggle,caption);
  }else{
   const input=document.createElement(edit.type==='choice'?'select':'input');input.setAttribute('aria-label',row.field);input.disabled=state.settingsBusy;
   if(edit.type==='choice'){for(const item of edit.choices){const option=document.createElement('option');option.value=item.value;option.textContent=item.label;input.append(option);}}
   else{input.type=edit.type==='number'?'number':'text';if(edit.max_length)input.maxLength=edit.max_length;if(edit.min!==undefined)input.min=edit.allow_zero?0:edit.min;if(edit.max!==undefined)input.max=edit.max;}
   input.value=raw;input.oninput=()=>{stageSetting(row,input.value);value.classList.toggle('pending-field',state.drafts.has(row.key));};value.append(input);
  }
 }else if(typeof row.checked==='boolean'){
  value.className='binary-value';const toggle=document.createElement('input');toggle.type='checkbox';toggle.setAttribute('role','switch');toggle.setAttribute('aria-label',row.field+': '+row.value);toggle.checked=row.checked;toggle.disabled=true;
  toggle.title='Reported device state · Changes locked during read-only access';
  const caption=document.createElement('span');caption.textContent=row.value;value.append(toggle,caption);
 }else if(/^(OK|Warning|Critical|Non-recoverable) \(code /.test(row.value)){
  value.className='value-health'+(row.value.startsWith('Warning')?' value-warning':/^(Critical|Non-recoverable)/.test(row.value)?' value-critical':'');value.textContent=row.value.replace(/ \(code .*\)$/,'');value.title=row.value;
 }else value.textContent=row.value;
 return value;
}
function renderRows(){
 const term=$('filter').value.trim().toLowerCase();const rows=state.rows.filter(r=>(r.group+' '+r.field+' '+r.value+' '+accessLabel(r.changeability,fieldEditable(r))).toLowerCase().includes(term));$('data-rows').replaceChildren();
 for(const row of rows){
  const tr=document.createElement('tr'),group=document.createElement('td'),field=document.createElement('td'),value=document.createElement('td'),access=document.createElement('td');
  group.textContent=row.group.split(' / ').slice(1).join(' / ')||'General';field.textContent=row.field;value.append(fieldValueNode(row));
  const badge=document.createElement('span');badge.className='field-access '+(row.changeability==='configurable'?'field-configurable':'');badge.textContent=accessLabel(row.changeability,fieldEditable(row));badge.title=row.evidence||'Editability has not been established.';access.append(badge);
  tr.append(group,field,value,access);$('data-rows').append(tr);
 }
 text('field-count',`${rows.length} of ${state.rows.length} fields`);renderSettingsTools();
}
async function selectPage(identifier){
 if(!leaveSettings())return;resetSettings();
 const page=state.catalog.find(p=>p.id===identifier)||state.catalog[0];if(!page)return;
 state.page=page.id;state.section=page.section;state.rows=[];state.power=null;++state.revision;text('page-kicker',page.section.toUpperCase());text('page-title',page.title);text('panel-title',page.title);$('filter').value='';renderNavigation();renderTabs();renderActions();
 show('table-wrap',false);show('notice',false);text('field-count','No data loaded');show('empty',!current()?.connected);if(current()?.connected)await loadPage();
}
async function loadPage(){
 if(!leaveSettings())return;state.drafts.clear();state.settingsNeedsRefresh=false;
 const device=current();if(!device?.connected)return;const revision=++state.revision;const id=state.device,page=state.page;
 show('notice',true);text('notice','Reading current device information…');$('refresh').disabled=true;
 try{const data=await api(`/devices/${id}/pages/${page}`);if(revision!==state.revision)return;
 if(data.capabilities&&!data.capabilities.pages.includes(page)){useCapabilities(data.capabilities);await selectPage(state.page);return;}
 state.rows=data.rows;state.power=data.power||null;if(data.capabilities)useCapabilities(data.capabilities);renderRows();renderActions();show('empty',false);show('table-wrap',state.rows.length>0);show('notice',data.errors.length>0);if(data.errors.length)text('notice','Some information is unavailable: '+data.errors.join(' · '));
 const date=new Date(data.updated);text('summary-updated',date.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}));text('panel-note',`Reported via ${state.capabilities?.source||'controller'} · ${date.toLocaleString()}`);
 }catch(error){if(revision!==state.revision)return;state.rows=[];state.power=null;renderRows();renderActions();show('table-wrap',false);show('notice',true);text('notice',error.message);}
 finally{if(revision===state.revision)$('refresh').disabled=!current()?.connected;}
}
async function toggleConnection(){
 if(!leaveSettings())return;resetSettings();
 const device=current();if(!device)return;closeSol();if(!device.has_password&&!device.connected){editProfile(device);return;}
 $('connect').disabled=true;show('notice',true);text('notice',device.connected?'Closing the status connection…':'Connecting to your DRAC…');
 try{await api(`/devices/${device.id}/${device.connected?'disconnect':'connect'}`,{method:'POST'});await reloadDevices();await selectPage(state.page);}catch(error){show('notice',true);text('notice',error.message);}finally{renderDevice();}
}
function renderDevices(){
 $('device-list').replaceChildren();for(const device of state.devices){const row=document.createElement('div');row.className='device-row';const info=document.createElement('div');const name=document.createElement('strong');name.textContent=device.name;const detail=document.createElement('p');detail.textContent=`${device.address} · ${device.username} · ${device.has_password?'Password saved':'Password needed'}`;info.append(name,detail);const edit=document.createElement('button');edit.textContent='Edit';edit.onclick=()=>editProfile(device);const remove=document.createElement('button');remove.textContent='Remove';remove.onclick=async()=>{if(!confirm(`Remove ${device.name} from DRACula? This does not change the machine.`))return;try{await api('/devices/'+device.id,{method:'DELETE'});await reloadDevices();await selectPage(state.page);}catch(error){toast(error.message);}};row.append(info,edit,remove);$('device-list').append(row);}
 if(!state.devices.length){const p=document.createElement('p');p.textContent='No devices configured yet.';$('device-list').append(p);}
}
function editProfile(device=null){
 $('profile-form').dataset.id=device?.id||'';text('profile-title',device?'Edit device':'Add device');$('profile-name').value=device?.name||'';$('profile-address').value=device?.address||'';$('profile-user').value=device?.username||'root';$('profile-password').value='';text('profile-password-note',device?.has_password?'Leave blank to keep the saved password. Stored passwords are never displayed.':'Encrypted on the server. A password is needed before connecting.');text('profile-error','');$('profile-dialog').showModal();
}
// Settings are staged locally. Only explicit confirmation calls the submit endpoint.
function fieldEditable(row){return Boolean(row.edit&&current()?.settings_writable&&current()?.connected&&!state.settingsNeedsRefresh);}
function stageSetting(row,value){
 if(!fieldEditable(row)||state.settingsBusy)return;
 if(value===row.edit.value)state.drafts.delete(row.key);else state.drafts.set(row.key,value);
 renderSettingsTools();
}
function leaveSettings(){
 if(state.settingsBusy){toast('Finish or cancel the settings review first.');return false;}
 return !state.drafts.size||confirm('Discard your staged settings changes? Nothing has been sent to the DRAC.');
}
function resetSettings(){
 state.drafts.clear();state.settingsBusy=false;state.settingsPosting=false;state.settingsReview=null;state.settingsNeedsRefresh=false;
 if($('settings-review').open)$('settings-review').close();renderSettingsTools();
}
function renderSettingsTools(){
 const available=state.rows.some(r=>fieldEditable(r));show('settings-tools',available||state.settingsNeedsRefresh);
 text('settings-pending',state.settingsNeedsRefresh?'Check the controller, then refresh before editing again.':state.drafts.size?`${state.drafts.size} staged change${state.drafts.size===1?'':'s'} · Nothing sent yet`:'No staged changes');
 $('apply-settings').disabled=!available||!state.drafts.size||state.settingsBusy;$('discard-settings').disabled=!state.drafts.size||state.settingsBusy;
 $('device-picker').disabled=state.settingsBusy;$('logout').disabled=state.settingsBusy;$('manage').disabled=state.settingsBusy;$('kvm').disabled=!current()?.has_password||state.settingsBusy;
 $('sol').disabled=!current()?.connected||state.settingsBusy;
 $('connect').disabled=!current()||state.settingsBusy;$('refresh').disabled=!current()?.connected||state.settingsBusy;
}
async function applySettings(){
 if(state.settingsBusy||!state.drafts.size||!current()?.settings_writable)return;
 const device=state.device,page=state.page,target=current().address,changes=Object.fromEntries(state.drafts),revision=state.rows.find(r=>r.edit)?.edit.revision;
 state.settingsBusy=true;renderRows();renderActions();
 try{
  const review=await api(`/devices/${device}/pages/${page}/review`,{method:'POST',body:JSON.stringify({changes,revision})});
  if(device!==state.device||page!==state.page||review.target!==target)throw Error('The selected device changed. Review again.');
  state.settingsReview={...review,device};text('confirm-settings',`Confirm and apply to ${review.target}`);text('settings-target',`Apply to ${review.target} · ${review.page}`);text('settings-warning',review.warning);text('settings-expiry',`Confirm within ${review.expires_in} seconds, or review again.`);
  $('settings-changes').replaceChildren();for(const change of review.changes){const row=document.createElement('tr');for(const value of [change.group+' / '+change.field,change.before||'(empty)',change.after||'(empty)']){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}$('settings-changes').append(row);}
  $('confirm-settings').disabled=false;$('cancel-settings').disabled=false;$('settings-review').showModal();
 }catch(error){state.settingsBusy=false;renderRows();renderActions();toast(error.message);}
}
async function cancelSettingsReview(){
 if(state.settingsPosting)return;const review=state.settingsReview;state.settingsReview=null;$('settings-review').close();state.settingsBusy=false;renderRows();renderActions();
 if(review)try{await api(`/devices/${review.device}/${review.kind||"settings"}/review/${review.token}`,{method:'DELETE'});}catch{}
}
async function confirmSettings(){
 const review=state.settingsReview;
 if(!review||state.settingsPosting||review.device!==state.device||review.target!==current()?.address)return;
 state.settingsReview=null;state.settingsPosting=true;$('confirm-settings').disabled=true;$('cancel-settings').disabled=true;
 try{
  const result=await api(`/devices/${review.device}/${review.kind||"settings"}/confirm`,{method:'POST',body:JSON.stringify({token:review.token,confirmed:true})});
  state.drafts.clear();state.settingsBusy=false;state.settingsPosting=false;$('settings-review').close();
  if(result.status==='verified'||result.status==='submitted'){await loadPage();toast(result.message);}
  else{state.settingsNeedsRefresh=true;renderRows();renderActions();show('notice',true);text('notice',result.message);}
 }catch(error){state.drafts.clear();state.settingsBusy=false;state.settingsPosting=false;state.settingsNeedsRefresh=true;$('settings-review').close();renderRows();renderActions();show('notice',true);text('notice',error.message+' Check the controller before trying again.');}
}
async function reviewPower(action){
 if(state.settingsBusy||state.settingsNeedsRefresh||!state.power?.actions.some(a=>a.id===action&&a.enabled))return;
 const device=state.device,target=current()?.address,revision=state.power.revision;
 state.settingsBusy=true;renderRows();renderActions();
 try{
  const review=await api(`/devices/${device}/power/review`,{method:'POST',body:JSON.stringify({action,revision})});
  if(device!==state.device||review.target!==target)throw Error('The selected device changed. Refresh and review again.');
  state.settingsReview={...review,device,kind:'power'};text('confirm-settings',`Confirm ${review.changes[0].field.toLowerCase()} on ${target}`);text('settings-target',`${review.changes[0].field} · ${target}`);text('settings-warning',review.warning);text('settings-expiry',`Confirm within ${review.expires_in} seconds.`);
  $('settings-changes').replaceChildren();for(const change of review.changes){const row=document.createElement('tr');for(const value of [change.field,change.before,change.after]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}$('settings-changes').append(row);}
  $('confirm-settings').disabled=false;$('cancel-settings').disabled=false;$('settings-review').showModal();
 }catch(error){state.settingsBusy=false;renderRows();renderActions();toast(error.message);}
}
let consoleRun=0,consoleRetry=null,inputUI=null,consoleResize=null,consoleWindowResize=false;
function fitConsoleViewport(){
 const canvas=$('console-canvas'),screen=$('console-screen'),dialog=$('kvm-dialog');
 if(!canvas?.style||!screen?.clientWidth||!screen?.clientHeight||!canvas.width||!canvas.height)return;
 if(dialog?.children&&typeof getComputedStyle==='function'&&typeof innerHeight==='number'){
  const chrome=Array.from(dialog.children).filter(node=>node!==screen&&!node.hidden),style=getComputedStyle(dialog);
  const number=name=>parseFloat(style[name])||0;
  const overhead=chrome.reduce((height,node)=>height+node.getBoundingClientRect().height,0)+number('paddingTop')+number('paddingBottom')+number('borderTopWidth')+number('borderBottomWidth')+number('rowGap')*chrome.length;
  const available=Math.max(1,(parseFloat(style.maxHeight)||innerHeight*.96)-overhead);
  screen.style.height=`${Math.min(available,screen.clientWidth*canvas.height/canvas.width+2)}px`;
 }
 const scale=Math.min(screen.clientWidth/canvas.width,screen.clientHeight/canvas.height);
 canvas.style.width=`${canvas.width*scale}px`;canvas.style.height=`${canvas.height*scale}px`;
}
function observeConsoleSize(){
 // A height-only browser resize need not resize the fixed-height screen itself.
 // Refit immediately, including while the remote picture is static.
 if(typeof window!=='undefined'&&!consoleWindowResize){window.addEventListener('resize',()=>requestAnimationFrame(fitConsoleViewport));consoleWindowResize=true;}
 if(typeof ResizeObserver!=='undefined'&&!consoleResize){consoleResize=new ResizeObserver(()=>requestAnimationFrame(fitConsoleViewport));consoleResize.observe($('console-screen'));}
 fitConsoleViewport();
}
function consoleInput(){
 if(typeof KvmInput==='undefined')return null;
 if(!inputUI)inputUI=new KvmInput($('console-canvas'),$('console-input-toggle'),$('console-input-note'),message=>{const socket=state.socket;if(socket?.readyState===1&&socket.bufferedAmount<65536)socket.send(JSON.stringify(message));else inputUI.reset(true);});
 return inputUI;
}
function renderConsoleStatus(phase,detail='',info={}){
 if(phase!=='connected')consoleInput()?.reset(true);
 const names={starting:'Connecting',connected:'Connected',reconnecting:'Reconnecting',failed:'Disconnected',expired:'Session ended',closing:'Closing'};
 const details={starting:'Opening remote console…',connected:info.generation>1?'Connection restored · Input starts off.':'Connected · Enable keyboard and mouse to control this machine.',reconnecting:'Reconnecting automatically.',failed:'Automatic reconnect stopped. Close this window and try again.',expired:'This console session ended. Open it again to reconnect.',closing:'Closing your console…'};
 let message=detail||details[phase]||details.starting;
 if(phase==='reconnecting'&&!detail){if(info.attempt)message+=` Attempt ${info.attempt}.`;if(info.retry_in>0)message+=` Next try in ${info.retry_in}s.`;}
 $('console-health').dataset.state=phase;
 const label=names[phase]||names.starting;
 if($('console-state-label').textContent!==label)text('console-state-label',label);
 text('console-status',message);
}
async function closeConsole(){
 consoleInput()?.release();
 ++consoleRun;clearTimeout(consoleRetry);consoleRetry=null;
 const id=state.console;state.console=null;if(state.socket){state.socket.close();state.socket=null;}$('kvm-dialog').close();
 if(state.frameURL){URL.revokeObjectURL(state.frameURL);state.frameURL=null;}
 if(id)try{await api('/kvm/'+id,{method:'DELETE'});}catch{}
}
async function openConsole(){
 if(!current()?.has_password)return;
 const run=++consoleRun,device=state.device;let attempts=0,connectedAt=0,terminal=false;
 const active=()=>run===consoleRun&&$('kvm-dialog').open;
 consoleInput()?.reset(true);$('kvm').disabled=true;$('kvm-dialog').showModal();observeConsoleSize();show('console-status',true);
 const retry=()=>{
  if(!active()||terminal)return;
  if(connectedAt&&Date.now()-connectedAt>=60000)attempts=0;
  connectedAt=0;$('console-canvas').hidden=true;
  const delays=[2000,5000,10000,20000,40000,60000,60000,60000];
  if(attempts>=delays.length){terminal=true;renderConsoleStatus('failed');return;}
  renderConsoleStatus('reconnecting','Browser connection lost. Reconnecting automatically…');
  consoleRetry=setTimeout(connectStream,delays[attempts++]);
 };
 async function connectStream(){
  if(!active())return;
  $('console-canvas').hidden=true;renderConsoleStatus('starting');
  const old=state.console;state.console=null;
  if(old)try{await api('/kvm/'+old,{method:'DELETE'});}catch{}
  if(!active())return;
  try{
   const data=await api('/devices/'+device+'/kvm',{method:'POST'});
   if(!active()){try{await api('/kvm/'+data.id,{method:'DELETE'});}catch{}return;}
   state.console=data.id;let phase='starting',drawing=false,frame=null;
   const protocol=location.protocol==='https:'?'wss:':'ws:';
   const socket=new WebSocket(`${protocol}//${location.host}/api/kvm/${data.id}/stream`);state.socket=socket;socket.binaryType='blob';
   socket.onmessage=async event=>{
    if(!active()||state.socket!==socket)return;
    if(typeof event.data==='string'){
     try{const info=JSON.parse(event.data);
      if(info.type==='frame-info'){if(info.generation)frame=info.frame;
      }else if(info.type==='console-status'){
       if(terminal&&info.state!=='failed'&&info.state!=='expired')return;
       consoleInput()?.update(info);phase=info.state;if(phase==='connected'&&!connectedAt)connectedAt=Date.now();
       if(phase==='failed'||phase==='expired')terminal=true;
       $('console-canvas').hidden=phase!=='connected';renderConsoleStatus(phase,'',info);
      }else if(info.type==='input-status'){consoleInput()?.update(info);if(info.error)text('console-input-note',info.error);
      }else if(info.message){terminal=true;$('console-canvas').hidden=true;renderConsoleStatus('failed',info.message);}
     }catch{}return;
    }
    if(drawing||phase!=='connected')return;drawing=true;const imageFrame=frame;
    try{const bitmap=await createImageBitmap(event.data);
     if(active()&&state.socket===socket&&!terminal&&phase==='connected'){const canvas=$('console-canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;canvas.getContext('2d').drawImage(bitmap,0,0);fitConsoleViewport();consoleInput()?.setFrame(imageFrame);}
     bitmap.close();
    }catch{if(active()&&state.socket===socket&&!terminal&&phase==='connected')renderConsoleStatus('connected','Waiting for a readable video frame…');}finally{drawing=false;}
   };
   socket.onerror=()=>{};
   socket.onclose=event=>{if(active()&&state.socket===socket){if(event.code===1008){terminal=true;$('console-canvas').hidden=true;renderConsoleStatus('failed','The console session is no longer available. Close and open it again.');}else retry();}};
  }catch(error){if(active()){renderConsoleStatus('failed',error.message);retry();}}
 }
 await connectStream();$('kvm').disabled=!current()?.has_password;
}
$('login-form').onsubmit=async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;try{await api('/login',{method:'POST',body:JSON.stringify({password:$('login-password').value})});$('login-password').value='';await signedIn();}catch(error){text('login-error',error.message);}finally{button.disabled=false;}};
$('device-picker').onchange=async()=>{if(!leaveSettings()){$('device-picker').value=state.device;return;}resetSettings();closeSol();await closeConsole();state.device=$('device-picker').value;useCapabilities(current()?.connected?await api(`/devices/${state.device}/capabilities`):null);text('summary-updated','Not yet');renderDevice();await selectPage('overview');};
$('connect').onclick=toggleConnection;$('empty-connect').onclick=toggleConnection;$('refresh').onclick=loadPage;$('filter').oninput=renderRows;
$('manage').onclick=()=>{$('devices-dialog').showModal();};$('new-device').onclick=()=>editProfile();
for(const button of document.querySelectorAll('[data-about]'))button.onclick=()=>{$('about-dialog').showModal();};
for(const button of document.querySelectorAll('[data-close]'))button.onclick=()=>{$(button.dataset.close).close();if(button.dataset.close==='profile-dialog')$('profile-password').value='';};
$('profile-form').onsubmit=async event=>{event.preventDefault();const id=$('profile-form').dataset.id;const body={name:$('profile-name').value.trim(),address:$('profile-address').value.trim(),username:$('profile-user').value.trim()};if($('profile-password').value||!id)body.password=$('profile-password').value;event.submitter.disabled=true;
 try{const saved=await api('/devices'+(id?'/'+id:''),{method:id?'PUT':'POST',body:JSON.stringify(body)});state.device=saved.id;$('profile-password').value='';$('profile-dialog').close();await reloadDevices();await selectPage('overview');toast('Device profile saved.');}catch(error){text('profile-error',error.message);}finally{event.submitter.disabled=false;}};
$('profile-dialog').addEventListener('close',()=>{$('profile-password').value='';});$('logout').onclick=async()=>{if(!leaveSettings())return;resetSettings();closeSol();await closeConsole();try{await api('/logout',{method:'POST'});}finally{signedOut();}};
$('apply-settings').onclick=applySettings;$('discard-settings').onclick=()=>{state.drafts.clear();renderRows();};$('cancel-settings').onclick=cancelSettingsReview;$('confirm-settings').onclick=confirmSettings;$('settings-review').addEventListener('cancel',event=>{event.preventDefault();cancelSettingsReview();});
initSol();
$('kvm').onclick=openConsole;$('close-kvm').onclick=closeConsole;$('kvm-dialog').addEventListener('cancel',event=>{event.preventDefault();closeConsole();});
(async()=>{try{const data=await api('/session');if(data.authenticated)await signedIn();else{signedOut();if(!data.configured)text('login-error','The server needs initial setup. Run apps/web/start.sh on the Docker host.');}}catch(error){signedOut();text('login-error',error.message);}})();
