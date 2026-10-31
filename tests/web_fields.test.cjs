// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
function render(row){
 const document={createElement:tag=>({tag,children:[],attrs:{},setAttribute(name,value){this.attrs[name]=value;},append(...children){this.children.push(...children);}})};
 const source=fs.readFileSync('apps/web/static/app.js','utf8');const context=vm.createContext({document,fieldEditable:()=>false});
 vm.runInContext(source.slice(source.indexOf('function accessLabel'),source.indexOf('function renderRows')),context);
 context.row=row;return vm.runInContext('fieldValueNode(row)',context);
}
test('binary values render disabled switches with accessible labels',()=>{
 for(const checked of [true,false]){
  const node=render({field:'SSH',value:checked?'Enabled':'Disabled',checked});const toggle=node.children[0];
  assert.equal(toggle.attrs.role,'switch');assert.equal(toggle.checked,checked);assert.equal(toggle.disabled,true);assert.match(toggle.attrs['aria-label'],/SSH/);
 }
});
test('counters and unrecognized states remain text instead of a false switch',()=>{
 for(const value of ['1','0','Unknown (code 2)','Not reported']){
  const node=render({field:'Reported value',value,checked:null});assert.equal(node.textContent,value);assert.equal(node.children.length,0);
 }
});
test('existing health status badges retain their meaning',()=>{
 const node=render({field:'Health',value:'Warning (code 3)',checked:null});assert.equal(node.textContent,'Warning');assert.match(node.className,/value-warning/);
});
