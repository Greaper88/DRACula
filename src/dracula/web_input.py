# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Input into one worker's authenticated private X display, never the host desktop."""
import json,os,re,socket,sys
from pathlib import Path
from .console_geometry import Viewport

class StaleFrame(ValueError):pass

KEYS={**{'Key'+c:c.lower() for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'},**{'Digit'+str(n):str(n) for n in range(10)},**{'F'+str(n):'F'+str(n) for n in range(1,13)},**{'Numpad'+str(n):'KP_'+str(n) for n in range(10)},
 'Enter':'Return','NumpadEnter':'KP_Enter','Escape':'Escape','Backspace':'BackSpace','Tab':'Tab','Space':'space',
 'ShiftLeft':'Shift_L','ShiftRight':'Shift_R','ControlLeft':'Control_L','ControlRight':'Control_R','AltLeft':'Alt_L','AltRight':'Alt_R','MetaLeft':'Super_L','MetaRight':'Super_R',
 'ArrowLeft':'Left','ArrowRight':'Right','ArrowUp':'Up','ArrowDown':'Down','Home':'Home','End':'End','PageUp':'Prior','PageDown':'Next','Insert':'Insert','Delete':'Delete',
 'CapsLock':'Caps_Lock','NumLock':'Num_Lock','ScrollLock':'Scroll_Lock','PrintScreen':'Print','Pause':'Pause','ContextMenu':'Menu',
 'Minus':'minus','Equal':'equal','BracketLeft':'bracketleft','BracketRight':'bracketright','Backslash':'backslash','Semicolon':'semicolon','Quote':'apostrophe','Backquote':'grave','Comma':'comma','Period':'period','Slash':'slash','IntlBackslash':'less',
 'NumpadAdd':'KP_Add','NumpadSubtract':'KP_Subtract','NumpadMultiply':'KP_Multiply','NumpadDivide':'KP_Divide','NumpadDecimal':'KP_Decimal'}

def validate(message):
    if not isinstance(message,dict):raise ValueError('Invalid console input')
    kind=message.get('type');fields={'generation','type'}
    def integer(name,low,high):
        value=message.get(name)
        if type(value) is not int or not low<=value<=high:raise ValueError('Invalid input value')
    if kind=='input-control':
        fields.add('enabled')
        if type(message.get('enabled')) is not bool:raise ValueError('Choose input enabled or disabled')
    elif kind=='key':
        fields|={'code','down'}
        if message.get('code') not in KEYS or type(message.get('down')) is not bool:raise ValueError('Unsupported key')
    elif kind=='pointer':
        fields|={'action','x','y','frame'}
        if type(message.get('frame')) is not str or not re.fullmatch('[0-9a-f]{32}',message['frame']):raise ValueError('Missing capture revision')
        integer('x',0,65535);integer('y',0,65535)
        if message.get('action')=='button':
            fields|={'button','down'};integer('button',0,2)
            if type(message.get('down')) is not bool:raise ValueError('Invalid mouse button')
        elif message.get('action')=='wheel':fields.add('steps');integer('steps',-3,3)
        elif message.get('action')!='move':raise ValueError('Unsupported pointer action')
    elif kind not in ('input-heartbeat','release'):raise ValueError('Unsupported console input')
    if set(message)-fields:raise ValueError('Unexpected console input fields')
    integer('generation',1,2**31-1)
    return message

class Injector:
    def __init__(self,endpoint):self.endpoint=Path(endpoint);self.connection=None;self.keys=set();self.buttons=set();self.enabled=False
    def control(self,operation):
        port,token=self.endpoint.read_text().splitlines()
        if not port.isdecimal() or not 1<=int(port)<=65535 or not re.fullmatch(r'[0-9a-f-]{36}',token):raise ValueError('Invalid private endpoint')
        with socket.create_connection(('127.0.0.1',int(port)),timeout=1) as channel:
            channel.sendall((token+' '+operation+'\n').encode());answer=channel.recv(32)
        self.enabled=answer==b'enabled\n';return self.enabled
    def connect(self):
        if self.connection:return
        from Xlib import display,XK,X
        from Xlib.ext import xtest
        self.connection=display.Display();self.XK=XK;self.X=X
        if not self.connection.has_extension('XTEST'):raise RuntimeError('Private display does not support input')
    def viewport(self):return Viewport.read(os.environ['DRACULA_FRAME_REGION'])
    def fake(self,kind,detail=0,**options):self.connection.xtest_fake_input(kind,detail,**options)
    def release(self):
        if self.connection:
            for key in self.keys:self.fake(self.X.KeyRelease,key)
            for button in self.buttons:self.fake(self.X.ButtonRelease,button)
            self.connection.sync()
        self.keys.clear();self.buttons.clear()
    def handle(self,message):
        validate(message);kind=message['type']
        if kind in ('release','input-control') and not message.get('enabled'):
            try:self.release()
            finally:self.control('disable')
        elif kind=='input-control':
            self.connect();self.control('enable')
        elif kind=='input-heartbeat':
            if not self.control('ping'):self.release()
        elif self.control('status'):
            self.connect()
            if kind=='key':
                key=self.connection.keysym_to_keycode(self.XK.string_to_keysym(KEYS[message['code']]))
                if not key:raise ValueError('Key unavailable in display layout')
                if message['down']:
                    if key not in self.keys:self.keys.add(key);self.fake(self.X.KeyPress,key)
                elif key in self.keys:self.keys.remove(key);self.fake(self.X.KeyRelease,key)
            else:
                region=self.viewport()
                if message['frame']!=region.id:raise StaleFrame('Viewer geometry changed')
                x,y=region.point(message['x'],message['y'])
                self.fake(self.X.MotionNotify,x=x,y=y)
                if message['action']=='button':
                    button=(1,2,3)[message['button']]
                    if message['down']:
                        if button not in self.buttons:self.buttons.add(button);self.fake(self.X.ButtonPress,button)
                    elif button in self.buttons:self.buttons.remove(button);self.fake(self.X.ButtonRelease,button)
                elif message['action']=='wheel':
                    for _ in range(abs(message['steps'])):
                        button=5 if message['steps']>0 else 4;self.fake(self.X.ButtonPress,button);self.fake(self.X.ButtonRelease,button)
            self.connection.sync()
        return self.enabled
    def close(self):
        try:self.release()
        except Exception:pass
        try:self.control('disable')
        except Exception:pass
        if self.connection:self.connection.close()
        self.connection=None;self.enabled=False

def main():
    injector=Injector(os.environ['DRACULA_INPUT_ENDPOINT'])
    try:
        for line in sys.stdin:
            try:
                if len(line)>2048:raise ValueError('Oversized input')
                result={'enabled':injector.handle(json.loads(line))}
            except StaleFrame:
                injector.close();result={'enabled':False,'error':'Viewer moved or resized. Enable input again on the current image.'}
            except Exception:
                injector.close();result={'enabled':False,'error':'Console input stopped; enable it again when connected.'}
            print(json.dumps(result),flush=True)
    finally:injector.close()
if __name__=='__main__':main()
