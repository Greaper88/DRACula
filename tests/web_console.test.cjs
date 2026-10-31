// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('apps/web/static/app.js','utf8');
function setup(apiOverride,bitmapOverride){
 const elements=new Map();const el=id=>{if(!elements.has(id))elements.set(id,{dataset:{},textContent:'',hidden:false,open:false,showModal(){this.open=true;},close(){this.open=false;}});return elements.get(id);};
 const sockets=[],timers=new Map(),calls=[];let number=0,timer=0;
 class Socket{constructor(){sockets.push(this);}close(){if(this.onclose)this.onclose({code:1000});}}
 const context=vm.createContext({state:{device:'test',console:null,socket:null},$:el,current:()=>({has_password:true,connected:false}),show:()=>{},text:(id,value)=>{el(id).text=value;el(id).textContent=value;},URL:{revokeObjectURL(){}},location:{protocol:'http:',host:'localhost'},WebSocket:Socket,Date,createImageBitmap:bitmapOverride|| (async()=>({width:1,height:1,close(){}})),setTimeout:fn=>{timers.set(++timer,fn);return timer;},clearTimeout:id=>timers.delete(id),api:async(path,options)=>{calls.push({path,method:options?.method});return apiOverride?apiOverride(path,options):{id:'console-'+(++number)};}});
 vm.runInContext(source.slice(source.indexOf('let consoleRun='),source.indexOf("$('login-form').onsubmit")),context);
 return {context,sockets,timers,calls,el,open:()=>vm.runInContext('openConsole()',context),close:()=>vm.runInContext('closeConsole()',context)};
}
test('browser transport loss requests a new worker and close cancels further retries',async()=>{
 const h=setup();await h.open();assert.equal(h.sockets.length,1);
 h.sockets[0].onclose({code:1006});assert.equal(h.timers.size,1);
 await [...h.timers.values()][0]();assert.equal(h.sockets.length,2);
 assert.equal(h.calls.filter(c=>c.method==='POST').length,2);
 assert.equal(h.calls.filter(c=>c.method==='DELETE').length,1);
 await h.close();assert.equal(h.timers.size,0);assert.equal(h.el('kvm-dialog').open,false);
});
test('closing during launch deletes the late worker instead of opening a socket',async()=>{
 let resolve;const pending=new Promise(r=>{resolve=r;});
 const h=setup((path,options)=>options?.method==='POST'?pending:{});
 const opening=h.open();await h.close();resolve({id:'late-worker'});await opening;
 assert.equal(h.sockets.length,0);assert.ok(h.calls.some(c=>c.path==='/kvm/late-worker'&&c.method==='DELETE'));
});
test('exhausted backend reconnect budget does not restart through the browser',async()=>{
 const h=setup();await h.open();await h.sockets[0].onmessage({data:JSON.stringify({type:'console-status',state:'failed'})});
 h.sockets[0].onclose({code:1000});assert.equal(h.timers.size,0);
});
test('connection badge follows backend state, retry details and recovery',async()=>{
 const h=setup();await h.open();
 assert.equal(h.el('console-state-label').textContent,'Connecting');
 const message=info=>h.sockets[0].onmessage({data:JSON.stringify({type:'console-status',...info})});
 await message({state:'connected',generation:1});
 assert.equal(h.el('console-state-label').textContent,'Connected');assert.equal(h.el('console-health').dataset.state,'connected');
 await message({state:'reconnecting',attempt:3,retry_in:10});
 assert.equal(h.el('console-state-label').textContent,'Reconnecting');assert.equal(h.el('console-canvas').hidden,true);
 assert.match(h.el('console-status').textContent,/Attempt 3/);assert.match(h.el('console-status').textContent,/10s/);
 await message({state:'connected',generation:2});assert.match(h.el('console-status').textContent,/restored/i);
 await message({state:'expired'});assert.equal(h.el('console-state-label').textContent,'Session ended');
});
test('policy-close cannot leave a stale connected badge',async()=>{
 const h=setup();await h.open();await h.sockets[0].onmessage({data:JSON.stringify({type:'console-status',state:'connected'})});
 h.sockets[0].onclose({code:1008});assert.equal(h.el('console-state-label').textContent,'Disconnected');assert.equal(h.el('console-canvas').hidden,true);
});
test('late status cannot turn a terminal error back into a green connected badge',async()=>{
 const h=setup();await h.open();
 await h.sockets[0].onmessage({data:JSON.stringify({type:'error',message:'Stream ended'})});
 await h.sockets[0].onmessage({data:JSON.stringify({type:'console-status',state:'connected'})});
 assert.equal(h.el('console-state-label').textContent,'Disconnected');assert.equal(h.el('console-canvas').hidden,true);
});

test('late frame decoding failure cannot overwrite a terminal connection error',async()=>{
 let failFrame;
 const h=setup(undefined,()=>new Promise((resolve,reject)=>{failFrame=reject;}));await h.open();
 await h.sockets[0].onmessage({data:JSON.stringify({type:'console-status',state:'connected'})});
 const drawing=h.sockets[0].onmessage({data:{}});
 await h.sockets[0].onmessage({data:JSON.stringify({type:'error',message:'Stream ended'})});
 failFrame(new Error('synthetic decode failure'));await drawing;
 assert.equal(h.el('console-state-label').textContent,'Disconnected');assert.equal(h.el('console-canvas').hidden,true);
});

test('a remote resolution change refits the viewer without a browser resize',async()=>{
 const frames=[{width:720,height:424,close(){}},{width:1280,height:1048,close(){}}];
 const h=setup(undefined,async()=>frames.shift());const canvas=h.el('console-canvas');canvas.style={};let drawn=0;canvas.getContext=()=>({drawImage(){drawn++}});
 h.el('console-screen').clientWidth=1000;h.el('console-screen').clientHeight=500;
 await h.open();const socket=h.sockets[0];await socket.onmessage({data:JSON.stringify({type:'console-status',state:'connected',generation:1})});
 await socket.onmessage({data:{}});assert.equal(canvas.width,720);assert.equal(canvas.height,424);assert.ok(Math.abs(parseFloat(canvas.style.height)-500)<.001);const before=parseFloat(canvas.style.width);
 await socket.onmessage({data:{}});assert.equal(canvas.width,1280);assert.equal(canvas.height,1048);assert.ok(Math.abs(parseFloat(canvas.style.height)-500)<.001);assert.ok(parseFloat(canvas.style.width)<before);assert.equal(drawn,2);
 await h.close();
});

test('height-only browser resizing refits a static console immediately and registers once',()=>{
 const listeners=[];const canvas={width:720,height:424,style:{}};
 const screen={clientWidth:1000,clientHeight:500,style:{}};
 Object.defineProperty(screen.style,'height',{set(value){screen.clientHeight=parseFloat(value)-2;}});
 const dialog={children:[{getBoundingClientRect:()=>({height:60})},{getBoundingClientRect:()=>({height:40})},{getBoundingClientRect:()=>({height:24})},screen]};
 const context=vm.createContext({$:id=>({'console-canvas':canvas,'console-screen':screen,'kvm-dialog':dialog})[id],innerHeight:900,window:{addEventListener:(type,fn)=>listeners.push({type,fn})},requestAnimationFrame:fn=>fn(),getComputedStyle:()=>({maxHeight:context.innerHeight*.96+'px',paddingTop:'24px',paddingBottom:'24px',borderTopWidth:'1px',borderBottomWidth:'1px',rowGap:'12px'})});
 vm.runInContext(source.slice(source.indexOf('let consoleRun='),source.indexOf('function consoleInput'))+'observeConsoleSize();observeConsoleSize();',context);
 assert.equal(listeners.length,1);assert.equal(listeners[0].type,'resize');
 const large=parseFloat(canvas.style.height);
 context.innerHeight=500;listeners[0].fn();const small=parseFloat(canvas.style.height);
 assert.ok(small<large);assert.ok(small<=500*.96-210);assert.ok(Math.abs(parseFloat(canvas.style.width)/small-720/424)<.001);
 context.innerHeight=1000;listeners[0].fn();assert.ok(parseFloat(canvas.style.height)>small);
 assert.equal(canvas.width,720);assert.equal(canvas.height,424);
});
