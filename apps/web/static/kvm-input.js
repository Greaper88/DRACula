// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
'use strict';
/** Browser capture is limited to the focused console, with an explicit input gate. */
class KvmInput {
 constructor(canvas,toggle,label,send){
  this.canvas=canvas;this.toggle=toggle;this.label=label;this.send=send;this.generation=0;this.connected=false;this.enabled=false;this.pending=false;this.timer=null;this.lastMove=0;this.frame=null;
  toggle.onchange=()=>{const enabled=toggle.checked;if(!this.connected)return this.reset();this.pending=true;toggle.disabled=true;label.textContent=enabled?'Enabling input…':'Releasing input…';this.emit({type:'input-control',enabled});};
  const key=down=>event=>{if(!this.enabled)return;if(event.ctrlKey&&event.altKey&&event.shiftKey){event.preventDefault();this.release();return;}
   if(!/^(Key[A-Z]|Digit[0-9]|F([1-9]|1[0-2])|Numpad[0-9]|Enter|NumpadEnter|Escape|Backspace|Tab|Space|Shift(Left|Right)|Control(Left|Right)|Alt(Left|Right)|Meta(Left|Right)|Arrow(Left|Right|Up|Down)|Home|End|PageUp|PageDown|Insert|Delete|CapsLock|NumLock|ScrollLock|PrintScreen|Pause|ContextMenu|Minus|Equal|BracketLeft|BracketRight|Backslash|Semicolon|Quote|Backquote|Comma|Period|Slash|IntlBackslash|Numpad(Add|Subtract|Multiply|Divide|Decimal))$/.test(event.code))return;
   event.preventDefault();if(!event.repeat)this.emit({type:'key',code:event.code,down});};
  canvas.addEventListener('keydown',key(true));canvas.addEventListener('keyup',key(false));
  const point=event=>{const r=canvas.getBoundingClientRect();return {x:Math.max(0,Math.min(65535,Math.round((event.clientX-r.left)*65535/r.width))),y:Math.max(0,Math.min(65535,Math.round((event.clientY-r.top)*65535/r.height)))};};
  canvas.addEventListener('pointermove',event=>{if(!this.enabled||Date.now()-this.lastMove<32)return;this.lastMove=Date.now();this.pointer({type:'pointer',action:'move',...point(event)});});
  const button=down=>event=>{if(!this.enabled||event.button<0||event.button>2)return;event.preventDefault();canvas.focus({preventScroll:true});if(down)canvas.setPointerCapture?.(event.pointerId);this.pointer({type:'pointer',action:'button',button:event.button,down,...point(event)});};
  canvas.addEventListener('pointerdown',button(true));canvas.addEventListener('pointerup',button(false));
  canvas.addEventListener('pointercancel',()=>this.release());canvas.addEventListener('contextmenu',event=>{if(this.enabled)event.preventDefault();});
  canvas.addEventListener('wheel',event=>{if(!this.enabled)return;event.preventDefault();this.pointer({type:'pointer',action:'wheel',steps:Math.sign(event.deltaY),...point(event)});},{passive:false});
  canvas.addEventListener('blur',()=>this.release());window.addEventListener('blur',()=>this.release());document.addEventListener('visibilitychange',()=>{if(document.hidden)this.release();});this.paint();
 }
 setFrame(frame){if(typeof frame==='string'&&/^[0-9a-f]{32}$/.test(frame))this.frame=frame;}
 pointer(message){if(this.frame)this.emit({...message,frame:this.frame});}
 emit(message){if(this.generation)this.send({...message,generation:this.generation});}
 paint(){this.toggle.checked=this.enabled;this.toggle.disabled=!this.connected||this.pending;this.label.textContent=this.enabled?'Keyboard and mouse enabled · Ctrl+Alt+Shift to release':'View only · Enable input to control this machine';this.canvas.classList.toggle('input-enabled',this.enabled);}
 update(info){
  if(info.type==='console-status'){
   if(this.generation!==info.generation||info.state!=='connected'){this.frame=null;this.reset();}
   this.generation=info.generation||0;this.connected=info.state==='connected';
  }else if(info.generation!==this.generation)return;
  if(typeof info.enabled==='boolean'||typeof info.input_enabled==='boolean'){
   const was=this.enabled;this.enabled=Boolean(info.enabled??info.input_enabled)&&this.connected;this.pending=false;
   if(this.enabled&&!was)this.canvas.focus({preventScroll:true});
  }
  if(this.enabled&&!this.timer)this.timer=setInterval(()=>this.emit({type:'input-heartbeat'}),1000);else if(!this.enabled){clearInterval(this.timer);this.timer=null;}this.paint();
 }
 release(){if(this.enabled||this.pending)this.emit({type:'release'});this.reset();}
 reset(disconnected=false){if(disconnected){this.connected=false;this.frame=null;}clearInterval(this.timer);this.timer=null;this.enabled=false;this.pending=false;this.paint();}
}
