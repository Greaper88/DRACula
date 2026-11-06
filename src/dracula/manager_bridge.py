# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Local desktop bridge. Credentials enter stdin; normalized fields leave stdout."""
import base64
import json
import os
import signal
import sys
from .launcher import CACHE
from .configuration import ConfigEditor,ConfigError
from .management import ManagementSession
from .status import BY_KEY, PAGES, StatusDevice, fetch_page

def encode(text):return base64.b64encode(str(text).encode()).decode()
def emit(kind,*fields):
    print(kind+('\t'+'\t'.join(encode(f) for f in fields) if fields else ''),flush=True)
def read_field():
    line=sys.stdin.readline(8192)
    if not line or not line.endswith('\n'):raise ValueError('Invalid bridge input')
    return base64.b64decode(line.strip(),validate=True).decode()

def desktop_sol(host,user,password):
    import select
    import threading
    import time
    from .ipmi import IpmiAdapter
    from .sol import SolSession, available

    adapter=IpmiAdapter(host,user,password)
    worker=SolSession(host,'desktop')
    try:
        access=adapter.sol_access() if available() else None
        if not access:
            raise RuntimeError('SOL is unavailable with these credentials.')
        worker.start(adapter,access)

        def receive():
            pending=b''
            try:
                while not worker.shutdown.is_set() and not worker.done.is_set():
                    if not select.select([sys.stdin],[],[],.2)[0]:
                        continue
                    chunk=os.read(sys.stdin.fileno(),4096)
                    if not chunk:
                        return
                    pending+=chunk
                    while b'\n' in pending:
                        line, _, pending=pending.partition(b'\n')
                        if len(line)>4096:
                            raise ValueError('Invalid SOL message')
                        command, _, data=line.partition(b'\t')
                        if command==b'QUIT' and not data:
                            return
                        if command in (b'ENABLE',b'DISABLE') and not data:
                            worker.message({'type':'enable','enabled':command==b'ENABLE'})
                        elif command==b'INPUT':
                            worker.message({'type':'input','data':base64.b64decode(data,validate=True).decode()})
                        else:
                            raise ValueError('Invalid SOL message')
                    if len(pending)>4096:
                        raise ValueError('Invalid SOL message')
            except (OSError,ValueError):
                worker._end('failed','The SOL input channel stopped.')
            finally:
                worker.shutdown.set()

        threading.Thread(target=receive,daemon=True).start()
        previous=None
        while True:
            status=worker.snapshot()
            if status!=previous:
                emit('SOL',status['state'],str(status['input_enabled']).lower(),status['text'],status['error'])
                previous=status
            if status['state'] in ('closed','failed') or worker.shutdown.is_set():
                break
            time.sleep(.1)
    finally:
        worker.stop()
        adapter.close()

def main():
    os.umask(0o077);CACHE.mkdir(mode=0o700,exist_ok=True)
    device=None;editor=None;management=None
    stopping=False
    def terminate(signum,frame):
        nonlocal stopping
        stopping=True
        raise SystemExit(143)
    signal.signal(signal.SIGTERM,terminate)
    try:
        host,user,password=read_field(),read_field(),read_field()
        if sys.argv[1:]==['--sol']:
            desktop_sol(host,user,password)
            return
        if sys.argv[1:]==['--console-managed']:
            from .desktop_console import run
            run(host,user,password,lambda value:emit('CONSOLE',value),lambda info:emit('CONSOLE_META',info['state'],info['attempt'],info['retry_in']))
            return
        if sys.argv[1:]==['--console']:
            from .launcher import main as console_main
            console_main([host,'--user',user,'--legacy-tls','--interactive'], credentials=(user,password))
            return
        device=StatusDevice(host)
        management=ManagementSession(device,user,password)
        del password
        editor=management.editor
        emit('READY',device.host)
        capabilities=management.capabilities();emit('FEATURES',str(capabilities['kvm']).lower(),str(capabilities['settings']).lower(),capabilities['source'],str(capabilities['sol']).lower())
        for page in PAGES:
            if page.key in capabilities['pages']:emit('PAGE',page.key,page.section,page.title,'; '.join(page.actions))
        emit('END')
        for command in sys.stdin:
            command=command.rstrip('\n')
            if len(command)>65536:emit('ERROR','Local request is too large');emit('END');continue
            if command=='QUIT':break
            if command.startswith('SETTINGS\t'):
                try:
                    request=json.loads(base64.b64decode(command[9:],validate=True))
                    op=request.get('op')
                    if op=='power-review':result=management.power.review(request['action'],request['revision'],'desktop')
                    elif op=='power-confirm':result=management.power.confirm(request['token'],'desktop',request.get('confirmed'))
                    elif op=='power-cancel':management.power.cancel(request['token'],'desktop');result={'ok':True}
                    elif op=='review':
                        if not management.http_ready:raise ConfigError('DRAC settings are unavailable through IPMI')
                        result=editor.review(request['page'],request['changes'],'desktop',request['revision'])
                    elif op=='confirm':result=editor.confirm(request['token'],'desktop',request.get('confirmed'))
                    elif op=='cancel':editor.cancel(request['token'],'desktop');result={'ok':True}
                    else:raise ConfigError('Unknown settings operation')
                    if op in ('review','power-review'):
                        emit('REVIEW',result['token'],result['target'],result['page'],result['expires_in'],result['warning'])
                        for item in result['changes']:emit('CHANGE',item['group'],item['field'],item['before'],item['after'])
                    else:emit('RESULT',result.get('status','cancelled'),result.get('message','Review cancelled'),result.get('verified_operations',0))
                except ConfigError as exc:emit('ERROR',str(exc))
                except Exception:emit('ERROR','Settings operation failed. No automatic retry was attempted; check the controller before trying again.')
                emit('END');continue
            if not command.startswith('READ\t') or command[5:] not in BY_KEY:
                emit('ERROR','Unknown read-only page');emit('END');continue
            page=BY_KEY[command[5:]]
            rows,errors=management.page(page.key)
            caps=management.capabilities();emit('FEATURES',str(caps['kvm']).lower(),str(caps['settings']).lower(),caps['source'],str(caps['sol']).lower())
            for key in caps['pages']:emit('CAPABILITY',key)
            if management.power_model:
                p=management.power_model;emit('POWER',p['revision'],p['state'],p['source'])
                for action in p['actions']:
                    if not action['supported']:continue
                    emit('POWER_ACTION',action['id'],action['label'],str(action['enabled']).lower(),action['reason'],action['source'])
            for row in rows:
                emit('FIELD',row.group,row.field,row.value,'' if row.checked is None else str(row.checked).lower(),row.changeability,row.evidence,row.key)
                if row.edit:
                    e=row.edit;emit('EDIT',row.key,e['type'],e['value'],e['revision'],e.get('min',''),e.get('max',''),str(e.get('allow_zero',False)).lower(),e.get('max_length',''),e.get('on',''),e.get('off',''))
                    for choice in e.get('choices',[]):emit('OPTION',row.key,choice['value'],choice['label'])
            for error in errors:emit('ERROR',error)
            emit('END')
    except Exception as exc:
        emit('ERROR',str(exc));emit('END')
        raise SystemExit(1)
    finally:
        if management:management.close()
        elif device:device.close()

if __name__=='__main__':main()
