# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared read-only Java session supervisor for native desktop and private web displays."""
import asyncio,json,math,os,select,secrets,signal,socket,struct,subprocess,sys,tempfile,threading,time
from pathlib import Path
from .launcher import ROOT,CACHE,JAVA_NAME

START_LOCK=threading.Lock()
RETRY_DELAYS=(2,5,10,20,40,60,60,60)
class ConsoleSession:
    def __init__(self,device_id,owner):
        self.device_id=device_id;self.owner=owner;self.created=time.monotonic();self.attached=False
        self.directory=None;self.xvfb=None;self.viewer=None;self.capturer=None;self.log=None;self.env=None;self.stopped=False
        self.lock=threading.RLock();self.shutdown=threading.Event();self.supervisor=None
        self.input_process=None;self.input_endpoint=None;self.input_state=None
        self.state="starting";self.generation=0;self.failures=0;self.next_retry=0;self.launched=0;self.connected_since=None;self.credentials=None;self.drop_seen=None;self.stop_on_close=False;self.max_lifetime=1800
    def expired(self):return self.stopped or self.state=='failed' or (self.max_lifetime is not None and time.monotonic()-self.created>self.max_lifetime) or (not self.attached and time.monotonic()-self.created>60)
    def start(self,profile,password,credentials=None,display_env=None,stop_on_close=False):
        self.stop_on_close=stop_on_close
        self.credentials=credentials or (lambda:(profile,password))
        if not (CACHE/'runtime32'/JAVA_NAME/'bin/java').exists():raise RuntimeError('Portable Java is not installed')
        self.directory=tempfile.TemporaryDirectory(prefix='web-kvm-',dir=CACHE);work=Path(self.directory.name)
        self.log=open(work/'worker.log','w+')
        self.env=os.environ.copy() if display_env is None else display_env.copy()
        if display_env is None:
            auth=work/'Xauthority';cookie=secrets.token_bytes(16)
            fields=(socket.gethostname().encode(),b'',b'MIT-MAGIC-COOKIE-1',cookie)
            auth.write_bytes(struct.pack('>H',256)+b''.join(struct.pack('>H',len(v))+v for v in fields));auth.chmod(0o600)
            read,write=os.pipe()
            try:
                self.xvfb=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','2048x1536x24','-nolisten','tcp','-auth',str(auth),'-noreset'],pass_fds=(write,),stdout=self.log,stderr=self.log,start_new_session=True)
                os.close(write);write=-1
                if not select.select([read],[],[],8)[0]:raise RuntimeError('Private display did not start')
                number=os.read(read,32).decode().strip()
                if not number.isdecimal():raise RuntimeError('Invalid private display')
            finally:
                os.close(read)
                if write>=0:os.close(write)
            self.env.update(DISPLAY=':'+number,XAUTHORITY=str(auth))
        self.env.update(PYTHONPATH=str(ROOT/'src'),PYTHONUNBUFFERED='1',DRACULA_CLASSES=str(work/'classes'))
        for name in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS'):self.env.pop(name,None)
        self.env['DRACULA_INPUT_CAPABLE']='1'
        self.env['DRACULA_VIEWER_CHROME']='0' if display_env is None else '1'
        self.env['DRACULA_VIEWER_STATE']=str(work/'viewer-state')
        self.env['DRACULA_FRAME_REGION']=str(work/'capture-region.json')
        self.supervisor=threading.Thread(target=self._supervise,name='dracula-console',daemon=True)
        self.supervisor.start()
    def status(self):
        return {'type':'console-status','state':self.state,'generation':self.generation,'attempt':self.failures,'input_enabled':self.input_enabled(),'input_supported':True,'retry_in':max(0,math.ceil(self.next_retry-time.monotonic())) if self.viewer is None and self.state=='reconnecting' else 0}
    def input_enabled(self):
        if self.state!='connected' or not self.input_state:return False
        try:return self.input_state.read_text().strip()=='enabled'
        except OSError:return False
    def input_message(self,message):
        from .web_input import validate
        validate(message)
        with self.lock:
            if self.stopped or self.expired() or message['generation']!=self.generation or self.state!='connected':
                return {'type':'input-status','enabled':False,'generation':self.generation}
            if self.xvfb is None:raise ValueError('Browser input requires its own private display')
            if self.input_process is None or self.input_process.poll() is not None:
                self.input_process=subprocess.Popen([sys.executable,'-m','dracula.web_input'],env=self.env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1,start_new_session=True)
            try:
                self.input_process.stdin.write(json.dumps(message)+'\n');self.input_process.stdin.flush()
                if not select.select([self.input_process.stdout],[],[],3)[0]:raise RuntimeError('Input worker unresponsive')
                result=json.loads(self.input_process.stdout.readline(1024))
            except Exception:
                self._stop_input();return {'type':'input-status','enabled':False,'generation':self.generation,'error':'Console input stopped. Enable it again when connected.'}
            return {'type':'input-status','generation':self.generation,**result}
    def _stop_input(self):
        process=self.input_process;self.input_process=None
        if process:
            try:
                process.stdin.close();process.wait(timeout=2)
            except Exception:
                process.terminate()
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            finally:process.stdout.close()
    def _launch(self):
        self._stop_input()
        profile,password=self.credentials()
        work=Path(self.directory.name);self.input_endpoint=work/('input-endpoint-'+str(self.generation+1));self.input_state=work/('input-state-'+str(self.generation+1))
        self.env.update(DRACULA_INPUT_ENDPOINT=str(self.input_endpoint),DRACULA_INPUT_STATE=str(self.input_state))
        (Path(self.directory.name)/'viewer-state').unlink(missing_ok=True)
        # Every invocation authenticates and retrieves a new JNLP in the shared launcher.
        with START_LOCK:
            self.viewer=subprocess.Popen([sys.executable,'-m','dracula.manager_bridge','--console'],cwd=ROOT,env=self.env,stdin=subprocess.PIPE,stdout=self.log,stderr=self.log,text=True,start_new_session=True)
            import base64
            try:
                for value in (profile['address'],profile['username'],password):self.viewer.stdin.write(base64.b64encode(value.encode()).decode()+'\n')
            finally:self.viewer.stdin.close()
        self.generation+=1;self.launched=time.monotonic();self.connected_since=None;self.drop_seen=None
        self.state='starting' if self.generation==1 else 'reconnecting'
    @staticmethod
    def _terminate(process):
        if process and process.poll() is None:
            try:
                # Signal the wrapper first: it closes Java and logs out its own DRAC login.
                # Killing the whole group early can interrupt that logout.
                process.terminate();process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait()
            except ProcessLookupError:pass
    def _retry(self,now):
        self._stop_input();self._terminate(self.viewer);self.viewer=None
        if self.failures>=len(RETRY_DELAYS):self.state='failed';return
        self.next_retry=now+RETRY_DELAYS[self.failures];self.failures+=1
        self.state='reconnecting';self.connected_since=None
    def _tick(self,now):
        if self.stopped or self.state=='failed':return
        if self.viewer is None:
            if now>=self.next_retry:
                try:self._launch()
                except Exception:self._retry(now)
            return
        try:signal_state=(Path(self.directory.name)/'viewer-state').read_text().strip()
        except OSError:signal_state=''
        if signal_state=='closed' and self.stop_on_close:
            self.state='closing'
            if self.drop_seen is None:self.drop_seen=now
            if self.viewer.poll() is not None or now-self.drop_seen>=30:
                self._terminate(self.viewer);self.state='closed';self.shutdown.set()
            return
        if self.viewer.poll() is not None:
            if self.stop_on_close and self.viewer.returncode==0:
                self.state='closed';self.shutdown.set();return
            self._retry(now);return
        if signal_state.startswith('disconnected') or signal_state=='closed':
            # Let Java close its sockets and the launcher log out its own web session.
            # Killing the wrapper immediately can strand that session on the DRAC.
            self.state='reconnecting'
            if self.drop_seen is None:self.drop_seen=now
            if now-self.drop_seen>=30:self._retry(now)
            return
        if self.state!='connected' and signal_state!='connected' and now-self.launched>75:
            self._retry(now);return
        if signal_state=='connected':
            self.state='connected'
            if self.connected_since is None:self.connected_since=now
            if now-self.connected_since>=60:self.failures=0
    def _supervise(self):
        while not self.shutdown.is_set():
            with self.lock:self._tick(time.monotonic())
            self.shutdown.wait(.5)
    async def capture(self):
        self.capturer=await asyncio.create_subprocess_exec(sys.executable,'-m','dracula.web_capture',env=self.env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,start_new_session=True)
        return self.capturer.stdout
    def stop(self):
        self.shutdown.set()
        with self.lock:
            if self.stopped:return
            self._stop_input()
            self.stopped=True;self.credentials=None
            if self.capturer and self.capturer.returncode is None:
                try:os.killpg(self.capturer.pid,signal.SIGTERM)
                except ProcessLookupError:pass
            self._terminate(self.viewer);self._terminate(self.xvfb)
            if self.log:self.log.close()
            if self.directory:self.directory.cleanup()
        if self.supervisor and self.supervisor is not threading.current_thread():self.supervisor.join(timeout=8)
