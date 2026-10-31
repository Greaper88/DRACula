// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
function setup(address='192.0.2.252',writable=true,connected=true){
 const ids=new Map();function element(tag='div'){return {tag,open:false,children:[],classList:{add(){},toggle(){}},setAttribute(){},append(...c){this.children.push(...c);},replaceChildren(){this.children=[];},showModal(){this.open=true;},close(){this.open=false;}};}
 const $=id=>{if(!ids.has(id))ids.set(id,element());return ids.get(id);};
 const row={key:'one',field:'SSH',value:'Enabled',checked:true,changeability:'configurable',edit:{type:'boolean',value:'1',revision:'revision',on:'Enabled',off:'Disabled'}};
 const state={device:'target',page:'services',rows:[row],drafts:new Map(),settingsBusy:false,settingsPosting:false,settingsReview:null,settingsNeedsRefresh:false};
 const calls=[];let loaded=0;
 const context=vm.createContext({state,$,document:{createElement:element},current:()=>({address,settings_writable:writable,connected}),text:(id,v)=>{$(id).textContent=v;},show:(id,v)=>{$(id).hidden=!v;},toast(){},confirm:()=>true,renderRows(){},renderActions(){},loadPage:async()=>{loaded++;},api:async(path,options)=>{calls.push({path,...options});if(path.endsWith('/review'))return {token:'review-token',target:address,page:'Services',expires_in:120,warning:'Review',changes:[{group:'Services',field:'SSH',before:'Enabled',after:'Disabled'}]};return {status:'verified',message:'Verified'};}});
 const source=fs.readFileSync('apps/web/static/app.js','utf8');
 vm.runInContext(source.slice(source.indexOf('function accessLabel'),source.indexOf('function renderRows')),context);
 vm.runInContext(source.slice(source.indexOf('// Settings are staged locally.'),source.indexOf('let consoleRun=')),context);context.row=row;
 return {state,row,calls,$,context,loaded:()=>loaded,run:code=>vm.runInContext(code,context)};
}
test('changing a toggle stages a draft without making any request',()=>{
 const h=setup();const value=h.run('fieldValueNode(row)');const toggle=value.children[0];assert.equal(toggle.disabled,false);toggle.checked=false;toggle.onchange();
 assert.equal(h.state.drafts.get('one'),'0');assert.equal(h.calls.length,0);assert.equal(h.$('apply-settings').disabled,false);
});
test('Apply prepares review only and Cancel never sends confirmation',async()=>{
 const h=setup();h.run("stageSetting(row,'0')");await h.run('applySettings()');
 assert.equal(h.calls.length,1);assert.match(h.calls[0].path,/\/review$/);assert.equal(h.$('settings-review').open,true);
 await h.run('cancelSettingsReview()');assert.equal(h.$('settings-review').open,false);assert.equal(h.calls[1].method,'DELETE');assert.ok(!h.calls.some(c=>c.path.endsWith('/confirm')));assert.equal(h.state.drafts.get('one'),'0');
});
test('confirmation sends only the reviewed token once and reloads verified values',async()=>{
 const h=setup();h.run("stageSetting(row,'0')");await h.run('applySettings()');await Promise.all([h.run('confirmSettings()'),h.run('confirmSettings()')]);
 const posts=h.calls.filter(c=>c.path.endsWith('/confirm'));assert.equal(posts.length,1);assert.deepEqual(JSON.parse(posts[0].body),{token:'review-token',confirmed:true});assert.equal(h.state.drafts.size,0);assert.equal(h.loaded(),1);
});
test('unavailable devices remain locked even if edit metadata is forged',async()=>{
 for(const address of ['192.0.2.253','192.0.2.254']){const h=setup(address,false);const value=h.run('fieldValueNode(row)');assert.equal(value.children[0].disabled,true);h.run("stageSetting(row,'0')");await h.run('applySettings()');assert.equal(h.state.drafts.size,0);assert.equal(h.calls.length,0);}
});

test('confirmation follows the selected target without hardcoded address blocks',async()=>{
 for(const address of ['192.0.2.253','192.0.2.254']){
  const h=setup(address);h.run("stageSetting(row,'0')");await h.run('applySettings()');assert.equal(h.state.settingsReview.target,address);await h.run('confirmSettings()');assert.equal(h.calls.filter(c=>c.path.endsWith('/confirm')).length,1);
 }
});
