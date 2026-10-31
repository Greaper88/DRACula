// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs'),vm=require('node:vm');
function setup(){
 const canvas={events:{},classList:{toggle(){}},addEventListener(k,v){this.events[k]=v},focus(){this.focused=true},getBoundingClientRect(){return {left:10,top:20,width:640,height:512}},setPointerCapture(){}};
 const toggle={},label={},messages=[],timers=new Map(),win={},doc={};let number=0;
 const ctx=vm.createContext({canvas,toggle,label,messages,window:{addEventListener:(k,v)=>win[k]=v},document:{hidden:false,addEventListener:(k,v)=>doc[k]=v},setInterval:fn=>{timers.set(++number,fn);return number},clearInterval:id=>timers.delete(id)});
 vm.runInContext(fs.readFileSync('apps/web/static/kvm-input.js','utf8')+';var ui=new KvmInput(canvas,toggle,label,m=>messages.push(m));',ctx);
 const run=s=>vm.runInContext(s,ctx);return {canvas,toggle,label,messages,timers,win,run,event:(kind,values={})=>{const e={preventDefault(){this.prevented=true},...values};canvas.events[kind](e);return e},connect:()=>run("ui.update({type:'console-status',state:'connected',generation:1,input_enabled:false})"),enable:()=>run("ui.update({type:'input-status',generation:1,enabled:true})")};
}
test('console input starts off and only an explicit switch asks to enable it',()=>{const h=setup();h.connect();h.event('keydown',{code:'Enter'});assert.equal(h.messages.length,0);h.toggle.checked=true;h.toggle.onchange();assert.equal(h.messages[0].type,'input-control');assert.equal(h.messages[0].enabled,true);h.enable();assert.equal(h.canvas.focused,true)});
test('focused input forwards physical keys and correctly scales mouse coordinates',()=>{const h=setup();h.connect();h.enable();h.run("ui.setFrame('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')");h.event('keydown',{code:'KeyA'});h.event('keyup',{code:'KeyA'});h.event('pointerdown',{clientX:330,clientY:276,button:2,pointerId:1});assert.equal(h.messages[0].code,'KeyA');assert.equal(h.messages[0].down,true);assert.equal(h.messages[1].down,false);assert.equal(h.messages[2].x,32768);assert.equal(h.messages[2].y,32768);assert.equal(h.messages[2].button,2);assert.equal(h.messages[2].frame,'a'.repeat(32))});
test('blur and the release shortcut disable capture and release held inputs',()=>{const h=setup();h.connect();h.enable();h.run("ui.setFrame('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')");h.event('keydown',{code:'ControlLeft'});h.win.blur();assert.equal(h.messages.at(-1).type,'release');assert.equal(h.toggle.checked,false);h.enable();const e=h.event('keydown',{code:'ShiftLeft',ctrlKey:true,altKey:true,shiftKey:true});assert.equal(e.prevented,true);assert.equal(h.messages.at(-1).type,'release');assert.equal(h.timers.size,0)});
test('reconnect requires enabling again and ignores old-generation acknowledgments',()=>{const h=setup();h.connect();h.enable();h.run("ui.update({type:'console-status',state:'reconnecting',generation:1,input_enabled:false});ui.update({type:'console-status',state:'connected',generation:2,input_enabled:false});ui.update({type:'input-status',generation:1,enabled:true})");assert.equal(h.toggle.checked,false);assert.equal(h.messages.length,0);h.event('keydown',{code:'Enter'});assert.equal(h.messages.length,0)});
test('frequent input acknowledgments cannot postpone the heartbeat lease',()=>{const h=setup();h.connect();h.enable();const timer=[...h.timers.keys()][0];h.enable();h.enable();assert.equal([...h.timers.keys()][0],timer);[...h.timers.values()][0]();assert.equal(h.messages.at(-1).type,'input-heartbeat')});

test('pointer events wait for a displayed crop and reconnect clears its identity',()=>{const h=setup();h.connect();h.enable();h.event('pointerdown',{clientX:10,clientY:20,button:0});assert.equal(h.messages.length,0);h.run("ui.setFrame('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')");h.event('pointerdown',{clientX:10,clientY:20,button:0});assert.equal(h.messages.length,1);h.run("ui.update({type:'console-status',generation:2,state:'connected',input_enabled:false})");h.run("ui.update({type:'input-status',generation:2,enabled:true})");h.event('pointerdown',{clientX:10,clientY:20,button:0});assert.equal(h.messages.length,1)});
test('viewer fit fills available space while preserving aspect ratio',()=>{const canvas={width:720,height:424,style:{}},screen={clientWidth:1200,clientHeight:600};const context=vm.createContext({$:id=>id==='console-canvas'?canvas:screen});const source=fs.readFileSync('apps/web/static/app.js','utf8');vm.runInContext(source.slice(source.indexOf('function fitConsoleViewport'),source.indexOf('function observeConsoleSize'))+'fitConsoleViewport();',context);assert.equal(canvas.style.height,'600px');assert.ok(Math.abs(parseFloat(canvas.style.width)-1018.8679)<.001);screen.clientWidth=400;screen.clientHeight=500;vm.runInContext('fitConsoleViewport()',context);assert.equal(canvas.style.width,'400px');assert.ok(Math.abs(parseFloat(canvas.style.height)-235.5556)<.001)});

test('pointer mapping follows the current displayed size and crop after resizing',()=>{
 const h=setup();h.connect();h.enable();
 for(const [width,height] of [[1125,660],[471,276],[328,251]]){
  const box={left:100,top:150,width,height};h.canvas.getBoundingClientRect=()=>box;
  h.run("ui.setFrame('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb')");
  h.event('pointerdown',{clientX:box.left+width/2,clientY:box.top+height/2,button:0});
  const middle=h.messages.at(-1);assert.equal(middle.x,32768);assert.equal(middle.y,32768);assert.equal(middle.frame,'b'.repeat(32));
  h.event('pointerup',{clientX:box.left+width,clientY:box.top+height,button:0});
  assert.equal(h.messages.at(-1).x,65535);assert.equal(h.messages.at(-1).y,65535);
 }
});
