"""Local desktop bridge. Credentials enter stdin; normalized fields leave stdout."""
import base64
import os
import signal
import sys
from .launcher import CACHE
from .status import BY_KEY, PAGES, StatusDevice, fetch_page

def encode(text):return base64.b64encode(str(text).encode()).decode()
def emit(kind,*fields):
    print(kind+('\t'+'\t'.join(encode(f) for f in fields) if fields else ''),flush=True)
def read_field():
    line=sys.stdin.readline(8192)
    if not line or not line.endswith('\n'):raise ValueError('Invalid bridge input')
    return base64.b64decode(line.strip(),validate=True).decode()

def main():
    os.umask(0o077);CACHE.mkdir(mode=0o700,exist_ok=True)
    device=None
    stopping=False
    def terminate(signum,frame):
        nonlocal stopping
        stopping=True
        raise SystemExit(143)
    signal.signal(signal.SIGTERM,terminate)
    try:
        host,user,password=read_field(),read_field(),read_field()
        if sys.argv[1:]==['--console']:
            from .launcher import main as console_main
            console_main([host,'--user',user,'--legacy-tls'], credentials=(user,password))
            return
        device=StatusDevice(host)
        device.login(user,password)
        del password
        emit('READY',device.host)
        for page in PAGES:emit('PAGE',page.key,page.section,page.title,'; '.join(page.actions))
        emit('END')
        for command in sys.stdin:
            command=command.rstrip('\n')
            if command=='QUIT':break
            if not command.startswith('READ\t') or command[5:] not in BY_KEY:
                emit('ERROR','Unknown read-only page');emit('END');continue
            page=BY_KEY[command[5:]]
            rows,errors=fetch_page(device,page)
            for row in rows:emit('ROW',*row)
            for error in errors:emit('ERROR',error)
            emit('END')
    except Exception as exc:
        emit('ERROR',str(exc));emit('END')
        raise SystemExit(1)
    finally:
        if device:
            try:
                if not stopping:device.request('/cgi-bin/webcgi/logout')
            except (Exception,SystemExit):pass
            finally:device.close()

if __name__=='__main__':main()
