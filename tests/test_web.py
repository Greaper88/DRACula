# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import base64,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
try:
    from cryptography.fernet import Fernet
    from fastapi.testclient import TestClient
    from dracula import web_api as api
except (ImportError,RuntimeError) as exc:
    raise unittest.SkipTest('Web tests require apps/web/requirements-test.txt') from exc


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.directory=Path(self.temp.name)
        self.patches=[patch.object(api,'DATA',self.directory),patch.object(api,'KEYS',self.directory),patch.object(api,'BLOCKED',{'192.0.2.251'})]
        for p in self.patches:p.start()
        salt=b'test-salt-1234567'
        (self.directory/'auth.json').write_text(json.dumps({'salt':salt.hex(),'hash':hashlib.pbkdf2_hmac('sha256',b'test-password',salt,250000).hex()}))
        (self.directory/'credentials.key').write_bytes(Fernet.generate_key())
        api.persist([{'id':'primary','name':'Synthetic controller','address':'192.0.2.253','username':'operator','secret':None}])
        api.SESSIONS.clear();api.CONNECTIONS.clear();api.WORKERS.clear();api.ATTEMPTS.clear()
        self.client=TestClient(api.app);self.origin={'Origin':'http://testserver'}
    def tearDown(self):
        self.client.close()
        for p in self.patches:p.stop()
        self.temp.cleanup()
    def login(self):
        r=self.client.post('/api/login',json={'password':'test-password'},headers=self.origin)
        self.assertEqual(r.status_code,200)
    def test_fresh_install_and_removing_last_device_stay_empty(self):
        (self.directory/'devices.json').unlink()
        self.login()
        with patch.object(api,'StatusDevice') as device:
            self.assertEqual(self.client.get('/api/devices').json(),[])
            result=self.client.post('/api/devices',headers=self.origin,json={'name':'Synthetic','address':'192.0.2.10','username':'operator','password':'synthetic-only'})
            self.assertEqual(result.status_code,200)
            self.assertEqual(self.client.delete('/api/devices/'+result.json()['id'],headers=self.origin).status_code,200)
            self.assertEqual(api.store(),[])
            self.assertEqual(self.client.get('/api/devices').json(),[])
            device.assert_not_called()
    def test_authentication_and_origin_boundary(self):
        self.assertEqual(self.client.get('/api/devices').status_code,401)
        self.assertEqual(self.client.post('/api/login',json={'password':'test-password'},headers={'Origin':'http://evil.invalid'}).status_code,403)
        self.login();self.assertIn('HttpOnly',self.client.cookies.jar._cookies['testserver.local']['/'][api.COOKIE]._rest)
        self.assertEqual(len(self.client.get('/api/catalog').json()),28)
    def test_profiles_encrypt_password_and_never_return_it(self):
        self.login();r=self.client.put('/api/devices/primary',headers=self.origin,json={'name':'Lab','address':'192.0.2.253','username':'root','password':'synthetic-drac-password'})
        self.assertEqual(r.status_code,200);self.assertNotIn('synthetic-drac-password',r.text)
        self.assertNotIn('synthetic-drac-password',(self.directory/'devices.json').read_text())
        self.assertNotIn('secret',r.json());self.assertTrue(r.json()['has_password'])
        saved=api.store()[0];self.assertEqual(api.cipher().decrypt(saved['secret'].encode()),b'synthetic-drac-password')
    def test_blocked_device_and_non_ip_targets_are_rejected(self):
        self.login()
        for address,status in [('192.0.2.251',403),('https://192.0.2.253/',422),('127.0.0.1:22',422)]:
            r=self.client.post('/api/devices',headers=self.origin,json={'name':'test','address':address,'username':'root','password':'x'})
            self.assertEqual(r.status_code,status)
    def test_read_pages_use_shared_core_and_report_errors(self):
        self.login()
        class Fake:
            last=0
            def page(self,key):
                from dracula.status import FieldRow
                return [FieldRow('system','Firmware','1.65')],['sensor unavailable']
        api.CONNECTIONS['primary']=Fake()
        r=self.client.get('/api/devices/primary/pages/overview');self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['rows'][0]['value'],'1.65');self.assertEqual(r.json()['errors'],['sensor unavailable'])
        self.assertEqual(self.client.get('/api/devices/primary/pages/power/reset').status_code,404)
        self.assertEqual(self.client.post('/api/devices/primary/pages/power',headers=self.origin,json={'action':'reset'}).status_code,405)
    def test_status_connection_does_not_offer_kvm_or_arbitrary_paths(self):
        from dracula.status import StatusDevice
        from dracula.launcher import CACHE
        CACHE.mkdir(exist_ok=True)
        device=StatusDevice('192.0.2.253')
        try:
            with patch('subprocess.run') as run:
                for path in ('/cgi-bin/webcgi/vkvmjnlp?id=1','/cgi-bin/webcgi/vkvm?state=3','/cgi-bin/webcgi/power?action=reset'):
                    with self.assertRaises(ValueError):device.request(path)
                run.assert_not_called()
        finally:device.close()
    def test_console_rejects_wrong_session_origin_and_input(self):
        self.login();token=self.client.cookies.get(api.COOKIE)
        class Worker:
            owner=token;attached=False;device_id='primary';stopped=False
            def stop(self):self.stopped=True
            def expired(self):return False
            def status(self):return {'state':'starting'}
            async def capture(self):
                import asyncio
                r=asyncio.StreamReader();return r
        worker=Worker();api.WORKERS['test']=worker
        with self.assertRaises(Exception):
            with self.client.websocket_connect('/api/kvm/test/stream',headers={'Origin':'http://evil.invalid'}):pass
        with self.client.websocket_connect('/api/kvm/test/stream',headers=self.origin) as ws:
            ws.receive_json()
            ws.send_text('{"key":"Enter"}')
            from starlette.websockets import WebSocketDisconnect
            with self.assertRaises(WebSocketDisconnect):ws.receive_bytes()
        self.assertTrue(worker.stopped)
    def test_local_profile_changes_do_not_contact_hardware(self):
        self.login()
        with patch.object(api,'StatusDevice') as device:
            self.client.put('/api/devices/primary',headers=self.origin,json={'name':'Local edit','address':'192.0.2.253','username':'root','password':'test'})
            device.assert_not_called()
    def test_500_is_controller_error_not_credentials_echo(self):
        from dracula.launcher import Device
        from dracula.status import fetch_page,BY_KEY
        class Broken:
            def request(self,path):raise RuntimeError('Device HTTP 500')
        rows,errors=fetch_page(Broken(),BY_KEY['overview'])
        self.assertEqual(rows,[]);self.assertIn('Device HTTP 500',errors[0])
    def test_console_does_not_require_live_status_login(self):
        self.login()
        self.client.put('/api/devices/primary',headers=self.origin,json={'name':'Lab','address':'192.0.2.252','username':'root','password':'synthetic'})
        with patch('dracula.web_worker.ConsoleWorker') as factory:
            worker=factory.return_value;worker.device_id='primary'
            r=self.client.post('/api/devices/primary/kvm',headers=self.origin)
            self.assertEqual(r.status_code,200)
            self.assertFalse(r.json()['read_only']);self.assertFalse(r.json()['input_enabled'])
            worker.start.assert_called_once()
            profile,password=worker.start.call_args.args[2]()
            self.assertEqual(profile['address'],'192.0.2.252')
            self.assertEqual(password,'synthetic')
            api.WORKERS.clear()
    def test_expired_device_read_reauthenticates_once_using_saved_credentials(self):
        from dracula.status import StatusDevice
        from dracula.launcher import Device,CACHE
        CACHE.mkdir(exist_ok=True)
        device=StatusDevice('192.0.2.252')
        device._credentials=('root','synthetic-password')
        try:
            for redirect in ('/cgi-bin/webcgi/timeout','/cgi/unlock.html'):
                with patch.object(Device,'request',side_effect=[RuntimeError('Device session unavailable; redirect to '+redirect),b'fresh-status']) as request, patch.object(Device,'login') as login:
                    self.assertEqual(device.request('/cgi-bin/webcgi/sysinfo'),b'fresh-status')
                    login.assert_called_once_with('root','synthetic-password')
                    self.assertEqual(request.call_count,2)
            with patch.object(Device,'request',side_effect=RuntimeError('Device HTTP 500')), patch.object(Device,'login') as login:
                with self.assertRaises(RuntimeError):device.request('/cgi-bin/webcgi/sysinfo')
                login.assert_not_called()
            with patch.object(Device,'logout') as logout:
                device.close()
                logout.assert_called_once_with()
        finally:
            device._credentials=None
            device.close()

    def settings_fixture(self):
        import threading
        from dracula.configuration import ConfigEditor
        from test_configuration import Device
        device=Device();editor=ConfigEditor(device)
        class Conn:
            closed=False;lock=threading.RLock()
        connection=Conn();connection.device=device;connection.editor=editor
        api.persist([{'id':'test252','name':'Test','address':'192.0.2.252','username':'root','secret':None},*({'id':'test'+suffix,'name':'Read only','address':'192.0.2.'+suffix,'username':'root','secret':None} for suffix in ('253','254'))])
        api.CONNECTIONS['test252']=connection
        row=next(r for r in editor.read('sol') if r.field=='Baud Rate')
        return device,editor,{'revision':row.edit['revision'],'changes':{row.key:'19200'}}
    def test_settings_api_enforces_target_review_confirmation_and_one_use(self):
        self.login();device,editor,body=self.settings_fixture()
        response=self.client.post('/api/devices/test252/pages/sol/review',json=body,headers=self.origin);self.assertEqual(response.status_code,200,response.text);self.assertFalse(device.writes)
        token=response.json()['token']
        for confirmed,status in [(False,409),(1,422),('true',422)]:
            self.assertEqual(self.client.post('/api/devices/test252/settings/confirm',json={'token':token,'confirmed':confirmed},headers=self.origin).status_code,status)
        self.assertFalse(device.writes)
        response=self.client.post('/api/devices/test252/settings/confirm',json={'token':token,'confirmed':True},headers=self.origin)
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['status'],'verified');self.assertEqual(len(device.writes),1)
        self.assertEqual(self.client.post('/api/devices/test252/settings/confirm',json={'token':token,'confirmed':True},headers=self.origin).status_code,409)
    def test_cancelled_review_and_another_session_cannot_submit(self):
        self.login();device,editor,body=self.settings_fixture();path='/api/devices/test252'
        result=self.client.post(path+'/pages/sol/review',json=body,headers=self.origin).json();token=result['token']
        self.client.delete(path+'/settings/review/'+token,headers=self.origin)
        self.assertEqual(self.client.post(path+'/settings/confirm',json={'token':token,'confirmed':True},headers=self.origin).status_code,409)
        token=self.client.post(path+'/pages/sol/review',json=body,headers=self.origin).json()['token']
        self.login()  # New dashboard session, same user; approval is bound to the original session.
        self.assertEqual(self.client.post(path+'/settings/confirm',json={'token':token,'confirmed':True},headers=self.origin).status_code,409)
        self.assertFalse(device.writes)
    def test_profile_target_change_blocks_an_existing_approval(self):
        self.login();device,editor,body=self.settings_fixture();path='/api/devices/test252'
        token=self.client.post(path+'/pages/sol/review',json=body,headers=self.origin).json()['token']
        profiles=api.store();profiles[0]['address']='192.0.2.254';api.persist(profiles)
        self.assertEqual(self.client.post(path+'/settings/confirm',json={'token':token,'confirmed':True},headers=self.origin).status_code,409)
        self.assertFalse(device.writes)

    def test_other_configured_addresses_have_no_hardcoded_write_block(self):
        import threading
        from dracula.configuration import ConfigEditor
        from test_configuration import Device
        self.login();self.settings_fixture()
        for suffix in ('253','254'):
            device=Device('192.0.2.'+suffix);editor=ConfigEditor(device)
            class Conn:
                closed=False;lock=threading.RLock()
            connection=Conn();connection.device=device;connection.editor=editor;api.CONNECTIONS['test'+suffix]=connection
            row=next(r for r in editor.read('sol') if r.field=='Baud Rate')
            path='/api/devices/test'+suffix
            response=self.client.post(path+'/pages/sol/review',json={'revision':row.edit['revision'],'changes':{row.key:'19200'}},headers=self.origin)
            self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['target'],device.host);self.assertFalse(device.writes)
            response=self.client.post(path+'/settings/confirm',json={'token':response.json()['token'],'confirmed':True},headers=self.origin)
            self.assertEqual(response.status_code,200,response.text);self.assertEqual(len(device.writes),1)
    def test_power_routes_require_review_explicit_confirmation_and_current_target(self):
        from dracula.power import PowerController
        from test_power import Adapter
        self.login();device,editor,_=self.settings_fixture();connection=api.CONNECTIONS['test252']
        h=Adapter();h.host=device.host;h.name='DRAC HTTP';i=Adapter();i.host=device.host;connection.power=PowerController(device.host,h,i)
        path='/api/devices/test252/power';revision=connection.power.status()['revision']
        r=self.client.post(path+'/review',json={'action':'off','revision':revision},headers=self.origin);self.assertEqual(r.status_code,200,r.text);token=r.json()['token'];self.assertEqual(h.sent,[])
        for confirmed,code in [(False,409),(1,422),('true',422)]:self.assertEqual(self.client.post(path+'/confirm',json={'token':token,'confirmed':confirmed},headers=self.origin).status_code,code)
        self.assertEqual(h.sent,[])
        self.assertEqual(self.client.post(path+'/confirm',json={'token':token,'confirmed':True},headers={'Origin':'http://elsewhere'}).status_code,403)
        result=self.client.post(path+'/confirm',json={'token':token,'confirmed':True},headers=self.origin);self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['status'],'verified');self.assertEqual(h.sent,['off'])
        self.assertEqual(self.client.post(path+'/confirm',json={'token':token,'confirmed':True},headers=self.origin).status_code,409)
        i.state='OFF'
        token=self.client.post(path+'/review',json={'action':'on','revision':connection.power.status()['revision']},headers=self.origin).json()['token']
        profiles=api.store();profiles[0]['address']='192.0.2.22';api.persist(profiles)
        self.assertEqual(self.client.post(path+'/confirm',json={'token':token,'confirmed':True},headers=self.origin).status_code,409);self.assertEqual(h.sent,['off'])
    def test_capabilities_and_power_metadata_are_normalized_without_credentials(self):
        import threading
        from unittest.mock import Mock
        self.login();m=Mock();m.capabilities.return_value={'pages':['overview','power'],'kvm':False,'settings':False,'source':'IPMI','sol':False};m.power_model={'state':'ON','revision':'opaque','actions':[]}
        c=Mock();c.management=m;c.lock=threading.RLock();c.page.return_value=([],[]);api.CONNECTIONS['primary']=c
        r=self.client.get('/api/devices/primary/capabilities');self.assertEqual(r.json()['pages'],['overview','power']);self.assertFalse(r.json()['kvm'])
        r=self.client.get('/api/devices/primary/pages/power');self.assertEqual(r.json()['power']['state'],'ON');self.assertEqual(r.json()['capabilities']['source'],'IPMI')
        m.http_ready=False
        self.assertEqual(self.client.post('/api/devices/primary/kvm',headers=self.origin).status_code,409)

    def test_console_input_is_bound_to_owner_and_validated_by_worker(self):
        import asyncio
        from unittest.mock import Mock
        self.login();token=self.client.cookies.get(api.COOKIE)
        class Worker:
            owner=token;attached=False;device_id='primary';stopped=False
            def stop(self):self.stopped=True
            def expired(self):return False
            def status(self):return {'type':'console-status','state':'connected','generation':1,'input_enabled':False}
            def input_message(self,message):
                from dracula.web_input import validate
                validate(message);return {'type':'input-status','generation':1,'enabled':message.get('enabled',False)}
            async def capture(self):return asyncio.StreamReader()
        w=Worker();api.WORKERS['input-test']=w
        with self.client.websocket_connect('/api/kvm/input-test/stream',headers=self.origin) as ws:
            ws.receive_json();ws.send_json({'type':'input-control','enabled':True,'generation':1});reply=ws.receive_json();self.assertEqual(reply['type'],'input-status');self.assertTrue(reply['enabled'])
            ws.send_json({'type':'key','code':'unknown','down':True,'generation':1})
            from starlette.websockets import WebSocketDisconnect
            with self.assertRaises(WebSocketDisconnect):ws.receive_json()
        self.assertTrue(w.stopped)
    def test_console_stream_sends_crop_identity_with_its_jpeg(self):
        import asyncio
        from dracula.console_geometry import viewport,encode_frame
        self.login();token=self.client.cookies.get(api.COOKIE);region=viewport((100,80,720,424),(2048,1536));jpeg=b'\xff\xd8synthetic-frame\xff\xd9'
        class Worker:
            owner=token;attached=False;device_id='primary';generation=1
            def stop(self):pass
            def expired(self):return False
            def status(self):return {'type':'console-status','state':'connected','generation':1}
            async def capture(self):
                reader=asyncio.StreamReader();payload=encode_frame(region,jpeg);reader.feed_data(len(payload).to_bytes(4,'big')+payload);return reader
        api.WORKERS['crop-test']=Worker();seen=[]
        with self.client.websocket_connect('/api/kvm/crop-test/stream',headers=self.origin) as ws:
            while True:
                message=ws.receive()
                if message.get('text'):seen.append(json.loads(message['text']))
                elif message.get('bytes'):
                    self.assertEqual(message['bytes'],jpeg);break
            info=next(item for item in seen if item['type']=='frame-info');self.assertEqual(info['frame'],region.id);self.assertEqual(info['generation'],1)
            self.assertNotIn('x',info);self.assertNotIn('y',info)
