# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""DRAC 5 console launcher. Legacy TLS is scoped to a single device client."""
import argparse
import getpass
import hashlib
import ipaddress
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get('DRACULA_CACHE',str(ROOT / '.local')))
VIEWER_SHA256 = '7843d243f5c35ed25a2e891d829bd67ccecf1170d50998d7bc46587fab15220e'
JAVA_NAME = 'zulu8.98.0.107-ca-jdk8.0.512-linux_i686'
JAVA_SHA256 = '791ddba1fd02ce0cf84301c57ce3315839a0966afb960174f4354016a579148c'
JAVA_URL = f'https://cdn.azul.com/zulu/bin/{JAVA_NAME}.tar.gz'

class Device:
    READ_PATHS = {'/cgi-bin/webcgi/main', '/cgi-bin/webcgi/sysinfo', '/cgi-bin/webcgi/vkvmconfig',
                  '/cgi-bin/webcgi/vkvmload?cat=C00&tab=T05&id=P07', '/cgi-bin/webcgi/vkvm?state=0', '/cgi-bin/webcgi/vkvmjnlp?id=1', '/plugins/vkvm/avctDRAC5Viewer.jar',
                  '/cgi-bin/webcgi/logout'}
    def __init__(self, host):
        self.host = str(ipaddress.IPv4Address(host))
        self._auth = None
        self.work = tempfile.TemporaryDirectory(prefix='http-', dir=CACHE)
        self.directory = Path(self.work.name)
    def close(self):
        self._auth = None
        self.work.cleanup()
    def request(self, path, data=None):
        if data is not None:
            if path != '/cgi-bin/webcgi/login':
                raise ValueError('Only authentication POST is permitted')
        elif path not in self.READ_PATHS:
            raise ValueError('Endpoint not allowed in read-only launcher')
        return self._exchange(path, data)

    def _exchange(self, path, data=None):
        """Internal transport; public reads and owned-session auth flows validate paths."""
        if os.environ.get('DRACULA_HTTP_TRANSPORT')=='stdlib':
            from .stdlib_http import exchange
            return exchange(self,path,data)
        headers=self.directory/'headers'
        body=self.directory/'body'
        cookies=self.directory/'cookies'
        cmd=['curl','-q','-ksS','--noproxy','*','--tlsv1.0','--tls-max','1.0',
             '--ciphers','DEFAULT:@SECLEVEL=0','--connect-timeout','5','--max-time','20',
             '--max-filesize','8000000','-b',str(cookies),'-c',str(cookies),
             '-D',str(headers),'-o',str(body),'-w','%{http_code}']
        if data is not None:
            cmd+=['--data-binary','@-']
        cmd+=['https://'+self.host+path]
        result=subprocess.run(cmd,input=data,capture_output=True,timeout=25)
        if result.returncode:
            raise RuntimeError('Device connection failed (curl code '+str(result.returncode)+')')
        status=result.stdout.decode().strip()
        if status in ('301','302','303'):
            from email.parser import Parser
            raw=headers.read_text().split('\n',1)[1]
            location=Parser().parsestr(raw).get('Location','')
            dest=urllib.parse.urlsplit(urllib.parse.urljoin('https://'+self.host,location))
            expected='/cgi-bin/webcgi/main' if data is not None else '/cgi-bin/webcgi/login'
            if path in ('/cgi-bin/webcgi/login','/cgi-bin/webcgi/unlock','/cgi-bin/webcgi/logout') and dest.hostname==self.host and dest.path==expected:
                return b''
            raise RuntimeError('Device session unavailable; redirect to '+dest.path)
        if status!='200':
            raise RuntimeError('Device HTTP '+status)
        return body.read_bytes()

    def login(self, user, password):
        self._auth = None
        self.request('/cgi-bin/webcgi/login', urllib.parse.urlencode({'user':user,'password':password}).encode())
        self.request('/cgi-bin/webcgi/main')
        self._auth = (user, password)

    def logout(self):
        """End only the session identified by this authenticated cookie, not an arbitrary ID.

        DRAC 5's /logout redirect can leave its token usable. Its native session
        page supplies mysidIndex, allowing a verified close of our own login.
        """
        closed_redirects=(
            'Device session unavailable; redirect to /cgi-bin/webcgi/timeout',
            'Device session unavailable; redirect to /cgi-bin/webcgi/login',
            'Device session unavailable; redirect to /cgi/login.html')
        try:
            data = self._exchange('/cgi-bin/webcgi/ssninfo')
        except RuntimeError as exc:
            if str(exc) in closed_redirects:
                self._auth=None
                return  # The original token has already expired or been invalidated.
            if str(exc) not in (
                'Device session unavailable; redirect to /cgi/unlock.html',
                'Device session unavailable; redirect to /cgi-bin/webcgi/unlock') or not self._auth:
                raise
            # Unlock the same expired token; never allocate a second cleanup login.
            self._exchange('/cgi-bin/webcgi/unlock', urllib.parse.urlencode({'password':self._auth[1]}).encode())
            data = self._exchange('/cgi-bin/webcgi/ssninfo')
        if len(data)>8_000_000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
            raise ValueError('Unsafe session response')
        root = ET.fromstring(data)
        index = root.findtext('mysidIndex')
        owned = [node for node in root.findall('session') if node.findtext('index')==index]
        if root.tag!='drac' or not index or not re.fullmatch(r'[0-9]{1,10}',index) or len(owned)!=1:
            raise ValueError('Cannot identify our own authenticated session')
        if self._auth and owned[0].findtext('user')!=self._auth[0]:
            raise ValueError('Session owner does not match our login')
        path='/cgi-bin/webcgi/ssninfo?index='+index+'&cat=C01&tab=T10&id=P21'
        try:self._exchange(path)
        except RuntimeError as exc:
            if str(exc) not in closed_redirects:raise
        try:data=self._exchange('/cgi-bin/webcgi/main')
        except RuntimeError as exc:
            if str(exc) not in closed_redirects:raise
        else:
            if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper() or ET.fromstring(data).find('LOGIN') is None:
                raise RuntimeError('Own session logout could not be confirmed')
        self._auth=None


def xml_properties(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('DTD/entity documents not supported')
    root = ET.fromstring(data)
    if root.tag != 'drac':
        raise ValueError('Not a DRAC XML response')
    return {p.get('name'):p.findtext('value','') for p in root.findall('.//property')}


def parse_launch_descriptor(data, host):
    if len(data)>1_000_000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unsafe or oversized JNLP')
    root=ET.fromstring(data)
    for element in root.iter():
        element.tag=element.tag.rsplit('}',1)[-1]
    app=root.find('application-desc')
    if root.tag!='jnlp' or app is None or app.get('main-class')!='com.avocent.drac5.kvm.Main':
        raise ValueError('Unsupported console application')
    values={}
    for element in app.findall('argument'):
        key,sep,value=(element.text or '').partition('=')
        if not sep or key in values or any(c in value for c in ('\t','\n','\r')):
            raise ValueError('Invalid or duplicate console argument')
        values[key]=value
    if values.get('ip')!=host or values.get('passwd')!='':
        raise ValueError('Unexpected console target or password authentication')
    if not re.fullmatch(r'[0-9a-fA-F]{32}',values.get('user','')):
        raise ValueError('Device did not supply the expected KVM ticket')
    for key in ('kmport','vport'):
        v=values.get(key,'')
        if not v.isdecimal() or not 1<=int(v)<=65535:
            raise ValueError('Invalid console port')
    if any(values.get(k)!=v for k,v in {'version':'1','apcp':'0','sslv3':'1'}.items()):
        raise ValueError('Unknown viewer protocol profile')
    return values


def verified(path, digest):
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest


def setup_java():
    java = CACHE/'runtime32'/JAVA_NAME/'bin/java'
    if java.exists():
        return java
    archive = CACHE/'java32.tar.gz'
    if not verified(archive, JAVA_SHA256):
        with urllib.request.urlopen(JAVA_URL, timeout=120) as r:
            payload = r.read(180_000_001)
        if len(payload)>180_000_000 or hashlib.sha256(payload).hexdigest()!=JAVA_SHA256:
            raise ValueError('Runtime hash mismatch or oversize download')
        archive.write_bytes(payload)
    with tarfile.open(archive) as tar:
        # Reject archive paths and links that escape the intended runtime root.
        dest=(CACHE/'runtime32').resolve()
        for item in tar.getmembers():
            target=(dest/item.name).resolve()
            if not target.is_relative_to(dest):
                raise ValueError('Unsafe runtime archive path')
            if item.issym() or item.islnk():
                link=(target.parent/item.linkname).resolve() if item.issym() else (dest/item.linkname).resolve()
                if not link.is_relative_to(dest):
                    raise ValueError('Unsafe runtime archive link')
        tar.extractall(dest, filter='data')
    return java


def main(argv=None, credentials=None):
    p=argparse.ArgumentParser(description='DRAC 5 console, input starts off; Linux x86 portable Java 8')
    p.add_argument('host', nargs='?')
    p.add_argument('--user', default='root')
    p.add_argument('--verbose', action='store_true', help='Print redacted viewer diagnostics after closing')
    p.add_argument('--legacy-tls', action='store_true', help='Opt in to device-only TLS 1.0 without certificate verification')
    p.add_argument('--setup', action='store_true', help='Download and verify private 32-bit Java 8 only')
    p.add_argument('--interactive', action='store_true', help='Offer keyboard/mouse control and the original vendor menus; input starts disabled')
    p.add_argument('--inspect', action='store_true', help='Read KVM configuration without allocating a console ticket')
    p.add_argument('--seconds', type=int, default=0, help='Close automatically after this many seconds (0: until window closes)')
    args=p.parse_args(argv)
    if args.seconds < 0 or args.seconds > 86400:
        p.error('--seconds must be between 0 and 86400')
    os.umask(0o077)
    CACHE.mkdir(mode=0o700, exist_ok=True)
    if args.setup:
        print(setup_java())
        return
    if not args.host or not args.legacy_tls:
        p.error('Supply a device IPv4 address and --legacy-tls for this verified DRAC 5 profile')
    java=CACHE/'runtime32'/JAVA_NAME/'bin/java'
    if not args.inspect and not java.exists():
        p.error('Run with --setup first')
    device=Device(args.host)
    if credentials is not None:
        args.user,password=credentials
    else:
        password=getpass.getpass('DRAC password: ')
    ticket=''
    try:
        device.login(args.user,password)
        del password
        config=xml_properties(device.request('/cgi-bin/webcgi/vkvmconfig'))
        if config.get('Enabled')!='1':
            raise ValueError('Console is disabled; launcher will not enable it')
        if args.inspect:
            print(json.dumps({k:config[k] for k in ('Enabled','KMPortNumber','VideoPortNumber','ActiveSessions','EncryptionEnabled') if k in config},indent=2))
            return
        if config.get('EncryptionEnabled')!='0':
            raise ValueError('Encrypted viewer transport has not been validated in this profile')
        active=int(config.get('ActiveSessions','-1'))
        maximum=int(config.get('MaxSessions','0'))
        if active < 0 or active >= maximum:
            raise ValueError('Console session limit reached or unknown; refusing to displace a session')
        jar=CACHE/'viewer.jar'
        if not verified(jar,VIEWER_SHA256):
            payload=device.request('/plugins/vkvm/avctDRAC5Viewer.jar')
            if hashlib.sha256(payload).hexdigest()!=VIEWER_SHA256:
                raise ValueError('Unknown viewer version; read-only adapter must be reviewed before launch')
            with tempfile.NamedTemporaryFile(dir=CACHE,prefix='viewer-',delete=False) as downloaded:
                downloaded.write(payload)
                temporary_jar=Path(downloaded.name)
            temporary_jar.replace(jar)
        classes=Path(os.getenv('DRACULA_CLASSES',str(CACHE/'classes')))
        classes.mkdir(parents=True,exist_ok=True)
        # Compile adapter against the exact approved viewer with the private JDK.
        compiler=java.parent/'javac'
        env=os.environ.copy()
        env['DRACULA_INPUT_CAPABLE']='1' if args.interactive else '0'
        env['LD_LIBRARY_PATH']=str(CACHE/'lib32/usr/lib/i386-linux-gnu')
        env.pop('JAVA_TOOL_OPTIONS',None)
        env.pop('_JAVA_OPTIONS',None)
        env.pop('JDK_JAVA_OPTIONS',None)
        sources=sorted((ROOT/'launcher/java').glob('*.java'))
        subprocess.run([str(compiler),'-cp',str(jar),'-d',str(classes),*[str(s) for s in sources]],env=env,check=True)
        subprocess.run([str(java),'-Djava.awt.headless=true','-cp',str(classes)+os.pathsep+str(jar),'dracula.ReadOnlySelfTest'],cwd=CACHE,env=env,check=True,timeout=20,stdout=subprocess.DEVNULL)
        subprocess.run([str(java),'-Djava.awt.headless=true','-cp',str(classes)+os.pathsep+str(jar),'dracula.ConsoleControlSelfTest'],cwd=CACHE,env=env,check=True,timeout=20,stdout=subprocess.DEVNULL)
        device.request('/cgi-bin/webcgi/vkvmload?cat=C00&tab=T05&id=P07')
        props=xml_properties(device.request('/cgi-bin/webcgi/vkvm?state=0'))
        jnlp=device.request('/cgi-bin/webcgi/vkvmjnlp?id=1')
        values=parse_launch_descriptor(jnlp,device.host)
        ticket=values['user']
        print('Fresh JNLP retrieved; starting console with input disabled.',flush=True)
        ports=[]
        for key in ('KMPortNumber','VideoPortNumber'):
            value=props.get(key,config.get(key,''))
            if not value.isdecimal() or not 1<=int(value)<=65535:
                raise ValueError('Invalid console port')
            ports.append(value)
        if ports != [values['kmport'],values['vport']]:
            raise ValueError('Console ports disagree between status and launch descriptor')
        launch=['title=DRACula View Only','ip='+device.host,'user='+ticket,'passwd=',
                'kmport='+ports[0],'vport='+ports[1],'apcp=0','version=1','sslv3=1']
        cmd=[str(java),'-Djava.security.properties='+str(ROOT/'launcher/legacy-java.security'),'-cp',str(classes)+os.pathsep+str(jar),'dracula.ReadOnlyViewer']
        with tempfile.TemporaryDirectory(prefix='session-',dir=CACHE) as work:
            with open(Path(work)/'viewer.log','w+') as log:
                proc=subprocess.Popen(cmd[:1]+['-Duser.home='+work]+cmd[1:],cwd=work,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
                timed_out=False
                try:
                    proc.communicate('\t'.join(launch)+'\n',timeout=args.seconds or None)
                except subprocess.TimeoutExpired:
                    timed_out=True
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill(); proc.wait()
                except BaseException:
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill(); proc.wait()
                    raise
                log.flush(); log.seek(0)
                output=log.read(1_000_000)
            # Vendor logs may include launch arguments. Never print them unsanitized.
            output=output.replace(ticket,'[ticket]').replace(device.host,'[device]')
            if args.verbose: print(output,end='')
            if 'User login response: 0' in output:
                print('Console authentication succeeded; console window opened.')
            elif 'User login response:' in output:
                raise RuntimeError('Console authentication failed; no takeover attempted')
            if not timed_out and proc.returncode != 0:
                raise RuntimeError('Viewer exited unsuccessfully')
    finally:
        try: device.logout()
        except Exception: print('Logout unconfirmed; device session will expire.',file=sys.stderr)
        device.close()

if __name__=='__main__':
    try: main()
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError,ET.ParseError) as exc:
        print(f'Launcher: {exc}',file=sys.stderr)
        sys.exit(1)
