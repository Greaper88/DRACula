# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Single-admin LAN management; Settings require selected-target reviewed confirmation. Browser receives no DRAC tickets."""
import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,hmac,ipaddress,json,logging,os,secrets,threading,time
from pathlib import Path
from urllib.parse import urlsplit
from anyio import CancelScope
from cryptography.fernet import Fernet
from fastapi import FastAPI,Request,Response,HTTPException,WebSocket,WebSocketDisconnect
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field,StrictBool,StrictStr
from .status import StatusDevice,PAGES,BY_KEY,fetch_page
from .web_setup import paths
from .configuration import ConfigEditor,ConfigError,writable
from .management import ManagementSession
from .sol import SolSession

ROOT=Path(__file__).resolve().parents[2]
STATIC=ROOT/'apps/web/static'
DATA,KEYS=paths()
BLOCKED={host.strip() for host in os.getenv('DRACULA_BLOCKED_HOSTS','').split(',') if host.strip()}
COOKIE='dracula_session'
SESSIONS={};ATTEMPTS={};CONNECTIONS={};WORKERS={}
STORE_LOCK=threading.RLock()

class Profile(BaseModel):
    name:str=Field(min_length=1,max_length=80)
    address:str
    username:str=Field(default='root',min_length=1,max_length=128)
    password:str|None=Field(default=None,max_length=4096)

class ConfigReview(BaseModel):
    revision:str=Field(min_length=1,max_length=128)
    changes:dict[str,StrictStr]

class PowerReview(BaseModel):
    revision:str=Field(min_length=1,max_length=128)
    action:str=Field(min_length=1,max_length=32)

class ConfigConfirm(BaseModel):
    token:str=Field(min_length=1,max_length=128)
    confirmed:StrictBool

class Login(BaseModel):
    password:str=Field(max_length=4096)

def checked_host(value):
    try:host=str(ipaddress.IPv4Address(value))
    except ValueError:raise HTTPException(422,'Enter a valid IPv4 address')
    if host in BLOCKED:raise HTTPException(403,'This device is excluded from access for now')
    return host

def store():
    file=DATA/'devices.json'
    if not file.exists():return []
    return json.loads(file.read_text())

def persist(profiles):
    DATA.mkdir(parents=True,exist_ok=True)
    temp=DATA/('devices.'+secrets.token_hex(8)+'.tmp')
    try:temp.write_text(json.dumps(profiles));temp.chmod(0o600);temp.replace(DATA/'devices.json')
    finally:temp.unlink(missing_ok=True)

def cipher():
    try:return Fernet((KEYS/'credentials.key').read_bytes())
    except OSError:raise HTTPException(503,'Run the local web setup command first')

def public(profile):return {k:profile[k] for k in ('id','name','address','username')}|{'has_password':bool(profile.get('secret')),'settings_writable':writable(profile['address'])}
def get_profile(identifier):
    with STORE_LOCK:
        for profile in store():
            if hmac.compare_digest(profile['id'],identifier):checked_host(profile['address']);return profile
    raise HTTPException(404,'Device not found')

def origin_ok(origin,host):
    if not origin:return False
    parsed=urlsplit(origin)
    allowed=os.getenv('DRACULA_PUBLIC_ORIGIN','').rstrip('/')
    return origin.rstrip('/')==allowed if allowed else parsed.scheme in ('http','https') and parsed.netloc==host

def session(token):
    found=SESSIONS.get(token or '')
    if not found or time.monotonic()>found['expires']:
        SESSIONS.pop(token or '',None);return None
    return found

def authorized(request):
    found=session(request.cookies.get(COOKIE))
    if not found:raise HTTPException(401,'Sign in to continue')
    return found

class Connection:
    def __init__(self,profile):
        if not profile.get('secret'):raise HTTPException(400,'Set this device’s password in Manage devices first')
        self.device=StatusDevice(profile['address']);self.lock=threading.RLock();self.closed=False;self.last=time.monotonic()
        try:self.management=ManagementSession(self.device,profile['username'],cipher().decrypt(profile['secret'].encode()).decode())
        except Exception:self.device.close();raise HTTPException(502,'Device connection failed through DRAC HTTP and IPMI')
        self.editor=self.management.editor;self.power=self.management.power
    def page(self,key):
        with self.lock:
            if self.closed:raise HTTPException(409,'Reconnect this device')
            self.last=time.monotonic()
            return self.management.page(key)
    def close(self):
        with self.lock:
            if self.closed:return
            self.closed=True;self.management.close()

def disconnect_device(identifier):
    connection=CONNECTIONS.pop(identifier,None)
    if connection:connection.close()
    for key,worker in list(WORKERS.items()):
        if worker.device_id==identifier:WORKERS.pop(key,None);worker.stop()

async def reap():
    while True:
        await asyncio.sleep(15)
        for identifier,connection in list(CONNECTIONS.items()):
            if time.monotonic()-connection.last>900:await asyncio.to_thread(disconnect_device,identifier)
        for key,worker in list(WORKERS.items()):
            if worker.expired():WORKERS.pop(key,None);await asyncio.to_thread(worker.stop)
        for token in list(SESSIONS):session(token)

@asynccontextmanager
async def lifespan(app):
    os.umask(0o077);DATA.mkdir(parents=True,exist_ok=True)
    task=asyncio.create_task(reap())
    yield
    task.cancel()
    for key in list(CONNECTIONS):await asyncio.to_thread(disconnect_device,key)
    for worker in list(WORKERS.values()):await asyncio.to_thread(worker.stop)

app=FastAPI(title='DRACula',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)

@app.middleware('http')
async def boundaries(request,call_next):
    if request.method in ('POST','PUT','PATCH','DELETE') and not origin_ok(request.headers.get('origin'),request.headers.get('host','')):
        return JSONResponse({'detail':'Same-origin requests only'},status_code=403)
    if request.headers.get('content-length','0').isdigit() and int(request.headers.get('content-length','0'))>65536:
        return JSONResponse({'detail':'Request too large'},status_code=413)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return response

@app.get('/healthz')
def health():return {'status':'ok','read_only':False,'confirmation_required':True,'kvm_read_only':False,'kvm_input_default':False}

@app.get('/api/session')
def current(request:Request):return {'authenticated':bool(session(request.cookies.get(COOKIE))),'configured':(DATA/'auth.json').exists(),'read_only':False,'confirmation_required':True,'kvm_read_only':False,'kvm_input_default':False}

@app.post('/api/login')
def login(body:Login,request:Request,response:Response):
    address=request.client.host if request.client else 'unknown';now=time.monotonic()
    attempts=[t for t in ATTEMPTS.get(address,[]) if now-t<60]
    if len(attempts)>=10:raise HTTPException(429,'Too many attempts; wait a minute')
    ATTEMPTS[address]=attempts+[now]
    try:auth=json.loads((DATA/'auth.json').read_text())
    except OSError:raise HTTPException(503,'Run the local web setup command first')
    digest=hashlib.pbkdf2_hmac('sha256',body.password.encode(),bytes.fromhex(auth['salt']),250_000).hex()
    if not hmac.compare_digest(digest,auth['hash']):raise HTTPException(401,'Incorrect dashboard password')
    ATTEMPTS.pop(address,None)
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
    SESSIONS[token]={'expires':now+8*3600,'csrf':csrf}
    response.set_cookie(COOKIE,token,httponly=True,samesite='strict',secure=os.getenv('DRACULA_SECURE_COOKIES','0')=='1',max_age=8*3600)
    return {'authenticated':True}

@app.post('/api/logout')
async def logout(request:Request,response:Response):
    authorized(request);token=request.cookies.get(COOKIE);SESSIONS.pop(token,None)
    for key,worker in list(WORKERS.items()):
        if worker.owner==token:WORKERS.pop(key,None);await asyncio.to_thread(worker.stop)
    response.delete_cookie(COOKIE)
    return {'ok':True}

@app.get('/api/catalog')
def catalog(request:Request):authorized(request);return [{'id':p.key,'section':p.section,'title':p.title,'actions':list(p.actions)} for p in PAGES]

@app.get('/api/devices')
def devices(request:Request):
    authorized(request)
    with STORE_LOCK:return [public(p)|{'connected':p['id'] in CONNECTIONS} for p in store() if p['address'] not in BLOCKED]

@app.post('/api/devices')
def add(body:Profile,request:Request):
    authorized(request);address=checked_host(body.address)
    with STORE_LOCK:
        profiles=store()
        if any(p['address']==address for p in profiles):raise HTTPException(409,'That address is already configured')
        profile={'id':secrets.token_hex(12),'name':body.name,'address':address,'username':body.username,'secret':cipher().encrypt(body.password.encode()).decode() if body.password else None}
        profiles.append(profile);persist(profiles);return public(profile)

@app.put('/api/devices/{identifier}')
async def edit(identifier:str,body:Profile,request:Request):
    authorized(request);address=checked_host(body.address)
    with STORE_LOCK:
        profiles=store();profile=next((p for p in profiles if p['id']==identifier),None)
        if profile is None:raise HTTPException(404,'Device not found')
        if any(p['address']==address and p['id']!=identifier for p in profiles):raise HTTPException(409,'That address is already configured')
        profile.update(name=body.name,address=address,username=body.username)
        if body.password is not None:profile['secret']=cipher().encrypt(body.password.encode()).decode() if body.password else None
        persist(profiles)
    await asyncio.to_thread(disconnect_device,identifier)
    return public(profile)

@app.delete('/api/devices/{identifier}')
async def remove(identifier:str,request:Request):
    authorized(request);get_profile(identifier)
    with STORE_LOCK:persist([p for p in store() if p['id']!=identifier])
    await asyncio.to_thread(disconnect_device,identifier);return {'ok':True}

@app.post('/api/devices/{identifier}/connect')
async def connect(identifier:str,request:Request):
    authorized(request);profile=get_profile(identifier)
    await asyncio.to_thread(disconnect_device,identifier)
    CONNECTIONS[identifier]=await asyncio.to_thread(Connection,profile)
    return {'connected':True}

@app.post('/api/devices/{identifier}/disconnect')
async def disconnect(identifier:str,request:Request):
    authorized(request);await asyncio.to_thread(disconnect_device,identifier);return {'connected':False}

@app.get('/api/devices/{identifier}/pages/{page}')
async def page(identifier:str,page:str,request:Request):
    authorized(request);get_profile(identifier)
    if page not in BY_KEY:raise HTTPException(404,'Unknown read-only page')
    connection=CONNECTIONS.get(identifier)
    if not connection:raise HTTPException(409,'Connect this device first')
    def read():
        # Keep rows, power revision and capabilities from the same serialized read.
        if not hasattr(connection,'management'):
            rows,errors=connection.page(page);return rows,errors,{}
        with connection.lock:
            rows,errors=connection.page(page)
            return rows,errors,{'capabilities':connection.management.capabilities(),'power':connection.management.power_model}
    rows,errors,metadata=await asyncio.to_thread(read)
    return metadata|{'rows':[asdict(row) for row in rows],'errors':errors,'updated':datetime.now(timezone.utc).isoformat(),'read_only':not any(row.edit is not None for row in rows)}

def settings_connection(identifier):
    profile=get_profile(identifier)
    if not writable(profile['address']):raise HTTPException(403,'Invalid configuration target')
    connection=CONNECTIONS.get(identifier)
    if not connection or connection.closed or not writable(connection.device.host) or connection.device.host!=profile['address']:raise HTTPException(409,'Reconnect the selected device before editing settings')
    return connection

@app.post('/api/devices/{identifier}/pages/{page}/review')
async def review_config(identifier:str,page:str,body:ConfigReview,request:Request):
    authorized(request);connection=settings_connection(identifier)
    def prepare():
        with connection.lock:
            if hasattr(connection,'management') and not connection.management.http_ready:raise HTTPException(409,'DRAC settings are unavailable on an IPMI connection')
            try:return connection.editor.review(page,body.changes,request.cookies[COOKIE],body.revision)
            except ConfigError as exc:raise HTTPException(409,str(exc))
            except Exception:raise HTTPException(502,'Settings review failed; no configuration was sent')
    return await asyncio.to_thread(prepare)

@app.post('/api/devices/{identifier}/settings/confirm')
async def confirm_config(identifier:str,body:ConfigConfirm,request:Request):
    authorized(request);connection=settings_connection(identifier)
    def apply():
        with connection.lock:
            try:return connection.editor.confirm(body.token,request.cookies[COOKIE],body.confirmed)
            except ConfigError as exc:raise HTTPException(409,str(exc))
            except Exception:raise HTTPException(502,'Apply stopped. Check the controller before trying again.')
    return await asyncio.to_thread(apply)

@app.delete('/api/devices/{identifier}/settings/review/{token}')
def cancel_config(identifier:str,token:str,request:Request):
    authorized(request);connection=settings_connection(identifier);connection.editor.cancel(token,request.cookies[COOKIE]);return {'ok':True}

@app.get('/api/devices/{identifier}/capabilities')
async def capabilities(identifier:str,request:Request):
    authorized(request);get_profile(identifier);connection=CONNECTIONS.get(identifier)
    if not connection:raise HTTPException(409,'Connect this device first')
    def read():
        with connection.lock:return connection.management.capabilities()
    return await asyncio.to_thread(read)

@app.post('/api/devices/{identifier}/power/review')
async def review_power(identifier:str,body:PowerReview,request:Request):
    authorized(request);connection=settings_connection(identifier)
    def prepare():
        with connection.lock:
            connection.last=time.monotonic()
            try:return connection.power.review(body.action,body.revision,request.cookies[COOKIE])
            except ConfigError as exc:raise HTTPException(409,str(exc))
    return await asyncio.to_thread(prepare)

@app.post('/api/devices/{identifier}/power/confirm')
async def confirm_power(identifier:str,body:ConfigConfirm,request:Request):
    authorized(request);connection=settings_connection(identifier)
    def send():
        with connection.lock:
            connection.last=time.monotonic()
            try:return connection.power.confirm(body.token,request.cookies[COOKIE],body.confirmed)
            except ConfigError as exc:raise HTTPException(409,str(exc))
    return await asyncio.to_thread(send)

@app.delete('/api/devices/{identifier}/power/review/{token}')
def cancel_power(identifier:str,token:str,request:Request):
    authorized(request);connection=settings_connection(identifier)
    with connection.lock:connection.power.cancel(token,request.cookies[COOKIE])
    return {'ok':True}

@app.post('/api/devices/{identifier}/kvm')
async def start_kvm(identifier:str,request:Request):
    authorized(request);profile=get_profile(identifier)
    connection=CONNECTIONS.get(identifier)
    if connection and hasattr(connection,'management') and not connection.management.http_ready:raise HTTPException(409,'KVM is unavailable through IPMI')
    if not profile.get('secret'):raise HTTPException(400,'Set this device’s password in Manage devices first')
    if len(WORKERS)>=2 or any(w.device_id==identifier for w in WORKERS.values()):raise HTTPException(409,'A console is already open, or all worker slots are in use')
    from .web_worker import ConsoleWorker
    worker=ConsoleWorker(identifier,request.cookies[COOKIE])
    key=secrets.token_urlsafe(24);WORKERS[key]=worker
    def credentials():
        latest=get_profile(identifier)
        return latest,cipher().decrypt(latest['secret'].encode()).decode()
    try:await asyncio.to_thread(worker.start,profile,cipher().decrypt(profile['secret'].encode()).decode(),credentials)
    except Exception:
        WORKERS.pop(key,None);await asyncio.to_thread(worker.stop)
        raise HTTPException(502,'Console worker could not start; check the server runtime and device availability')
    return {'id':key,'read_only':False,'input_enabled':False}

@app.delete('/api/kvm/{key}')
async def stop_kvm(key:str,request:Request):
    authorized(request);worker=WORKERS.get(key)
    if isinstance(worker,SolSession):raise HTTPException(404,'Console not found')
    if worker and worker.owner!=request.cookies.get(COOKIE):raise HTTPException(403,'Console belongs to another browser session')
    if worker:WORKERS.pop(key,None);await asyncio.to_thread(worker.stop)
    return {'ok':True}

@app.websocket('/api/kvm/{key}/stream')
async def console_stream(websocket:WebSocket,key:str):
    token=websocket.cookies.get(COOKIE);worker=WORKERS.get(key)
    if not session(token) or not worker or isinstance(worker,SolSession) or worker.owner!=token or worker.attached or not origin_ok(websocket.headers.get('origin'),websocket.headers.get('host','')):
        await websocket.close(code=1008);return
    worker.attached=True;await websocket.accept()
    async def receive():
        window=time.monotonic();count=0
        while True:
            message=await websocket.receive()
            if message['type']=='websocket.disconnect':return
            if not session(token):await websocket.close(code=1008);return
            now=time.monotonic()
            if now-window>=1:window=now;count=0
            count+=1
            try:
                raw=message.get('text','')
                if count>200 or not raw or len(raw)>2048:raise ValueError('Invalid input message')
                reply=await asyncio.to_thread(worker.input_message,json.loads(raw))
            except (ValueError,TypeError,AttributeError):
                await websocket.close(code=1008,reason='Invalid console input');return
            await websocket.send_json(reply)
    async def send():
        reader=await worker.capture()
        while session(token) and not worker.expired():
            header=await asyncio.wait_for(reader.readexactly(4),timeout=20)
            length=int.from_bytes(header,'big')
            if not 0<length<=4_000_000:raise ValueError('Invalid frame')
            from .console_geometry import decode_frame
            region,frame=decode_frame(await reader.readexactly(length))
            connection=CONNECTIONS.get(worker.device_id)
            if connection:connection.last=time.monotonic()
            await websocket.send_json({'type':'frame-info','frame':region.id,'generation':worker.generation})
            await websocket.send_bytes(frame)
        if session(token):await websocket.send_json({'type':'console-status','state':'failed' if worker.status()['state']=='failed' else 'expired'})
    async def status():
        previous=None
        while session(token):
            current=worker.status()
            if current!=previous:
                await websocket.send_json(current);previous=current
            await asyncio.sleep(.5)
    receiver=asyncio.create_task(receive());sender=asyncio.create_task(send());reporter=asyncio.create_task(status())
    try:
        done,_=await asyncio.wait((receiver,sender,reporter),return_when=asyncio.FIRST_COMPLETED)
        for completed in done:
            error=completed.exception()
            if error:
                logging.warning('Console stream ended: %s',type(error).__name__)
                try:await websocket.send_json({'type':'error','message':'The private console worker stopped. Close this window and try again.'})
                except Exception:pass
    finally:
        receiver.cancel();sender.cancel();reporter.cancel()
        with CancelScope(shield=True):
            await asyncio.gather(receiver,sender,reporter,return_exceptions=True)
            WORKERS.pop(key,None);await asyncio.to_thread(worker.stop)
            try:await websocket.close()
            except Exception:pass

@app.websocket('/api/devices/{identifier}/sol')
async def sol_stream(websocket:WebSocket,identifier:str):
    token=websocket.cookies.get(COOKIE)
    if not session(token) or not origin_ok(websocket.headers.get('origin'),websocket.headers.get('host','')):
        await websocket.close(code=1008)
        return
    try:
        get_profile(identifier)
    except HTTPException:
        await websocket.close(code=1008)
        return
    connection=CONNECTIONS.get(identifier)
    if not connection or len(WORKERS)>=2 or any(worker.device_id==identifier for worker in WORKERS.values()):
        await websocket.accept()
        await websocket.send_json({'state':'failed','error':'Connect the device first and close any open console.'})
        await websocket.close()
        return

    key=secrets.token_urlsafe(24)
    worker=SolSession(identifier,token)
    WORKERS[key]=worker

    def start():
        with connection.lock:
            if connection.closed or worker.shutdown.is_set():
                raise RuntimeError('The device disconnected')
            access=connection.management.sol_access()
            if not access or worker.shutdown.is_set():
                raise RuntimeError('SOL is unavailable')
            worker.start(connection.management.ipmi,access)

    async def receive():
        window=time.monotonic()
        count=0
        while session(token) and not worker.shutdown.is_set():
            message=await websocket.receive()
            if message['type']=='websocket.disconnect':
                return
            now=time.monotonic()
            if now-window>=1:
                window,count=now,0
            count+=1
            raw=message.get('text')
            if count>100 or not raw or len(raw)>4096 or not session(token):
                raise ValueError('Invalid SOL message')
            worker.message(json.loads(raw))

    async def send():
        previous=None
        while session(token) and not worker.shutdown.is_set():
            current=worker.snapshot()
            if current!=previous:
                await websocket.send_json(current)
                previous=current
            if current['state'] in ('failed','closed'):
                return
            connection.last=time.monotonic()
            await asyncio.sleep(.1)

    tasks=[]
    try:
        await websocket.accept()
        await asyncio.to_thread(start)
        tasks=[asyncio.create_task(receive()),asyncio.create_task(send())]
        done,_=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (OSError, ValueError, RuntimeError, WebSocketDisconnect):
        try:
            await websocket.send_json({'state':'failed','error':'The SOL session could not continue. Check device access and try again.'})
        except (RuntimeError, WebSocketDisconnect):
            pass
    finally:
        worker.shutdown.set()
        for task in tasks:
            task.cancel()
        with CancelScope(shield=True):
            await asyncio.gather(*tasks,return_exceptions=True)
            try:
                await asyncio.to_thread(worker.stop)
            finally:
                WORKERS.pop(key,None)
            try:
                await websocket.close()
            except (RuntimeError, WebSocketDisconnect):
                pass

app.mount('/assets',StaticFiles(directory=STATIC),name='assets')
@app.get('/')
def index():return FileResponse(STATIC/'index.html')
