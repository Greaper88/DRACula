# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Read-only DRAC 5 page catalog and normalized status rows shared by UIs."""
from dataclasses import dataclass
import hashlib
import re
from xml.etree import ElementTree as ET
from .launcher import Device
from .field_schema import field_spec

@dataclass(frozen=True)
class Page:
    key: str
    section: str
    title: str
    endpoints: tuple[str, ...]
    actions: tuple[str, ...] = ()

PAGES = (
    Page('overview','System','Overview',('sysinfo',)),
    Page('power','System','Power',('power',),('Power on','Power off','Power cycle','Reset','Graceful shutdown')),
    Page('sel','Logs','System events',('sel',),('Clear system event log',)),
    Page('post','Logs','POST history',('postlog',)),
    Page('raclog','Logs','DRAC events',('raclog',),('Clear DRAC log',)),
    Page('battery','Hardware','Batteries',('listbat',)),
    Page('fans','Hardware','Fans',('listfan',)),
    Page('intrusion','Hardware','Intrusion',('intrlist',)),
    Page('performance','Hardware','Performance',('hpinfo',)),
    Page('power_monitor','Hardware','Power monitoring',('listpower','poweraverage')),
    Page('supplies','Hardware','Power supplies',('pwrsup',)),
    Page('temperatures','Hardware','Temperatures',('listtemp',)),
    Page('voltages','Hardware','Voltages',('listvolt',)),
    Page('rac','Controller','DRAC information',('rac',),('Reset controller',)),
    Page('network','Controller','Network',('nic',),('Apply network settings',)),
    Page('services','Controller','Services',('services',),('Apply service settings',)),
    Page('serial','Controller','Serial',('serial',),('Apply serial settings',)),
    Page('sol','Controller','Serial over LAN',('sol',),('Apply SOL settings',)),
    Page('users','Access','Users',('users',),('Add user','Edit user','Delete user')),
    Page('directory','Access','Directory services',('ad',),('Apply directory settings',)),
    Page('certificate','Access','Certificate',('get_certview',),('Upload certificate','Generate certificate request')),
    Page('sessions','Access','Sessions',('ssninfo',),('Terminate session',)),
    Page('alerts','Alerts','Platform event filters',('listpef',),('Apply alert filters',)),
    Page('alert_destinations','Alerts','Trap destinations',('lpefdest',),('Apply trap settings','Send test trap')),
    Page('alert_email','Alerts','Email alerts',('lpefemail',),('Apply email settings','Send test email')),
    Page('console','Console','KVM settings',('vkvmconfig',),('Apply KVM settings',)),
    Page('media','Console','Virtual media',('vmconfig',),('Attach media','Detach media','Apply media settings')),
    Page('firmware','Maintenance','Firmware',('sysinfo',),('Upload firmware','Flash firmware')),
)
BY_KEY={page.key:page for page in PAGES}
READ_ENDPOINTS=frozenset('/cgi-bin/webcgi/'+e for p in PAGES for e in p.endpoints)
class StatusDevice(Device):
    READ_PATHS=READ_ENDPOINTS | {'/cgi-bin/webcgi/main','/cgi-bin/webcgi/logout'}
    def __init__(self,host):
        super().__init__(host)
        self._credentials=None
        self._refreshing=False
    def login(self,user,password):
        self._refreshing=True
        try:
            super().login(user,password)
            self._credentials=(user,password)
        finally:self._refreshing=False
    def request(self,path,data=None):
        try:return super().request(path,data)
        except RuntimeError as exc:
            expired=str(exc) in (
                'Device session unavailable; redirect to /cgi-bin/webcgi/login',
                'Device session unavailable; redirect to /cgi-bin/webcgi/timeout',
                'Device session unavailable; redirect to /cgi/unlock.html')
            if not expired or self._refreshing or not self._credentials or data is not None or path=='/cgi-bin/webcgi/logout':raise
            # Retry only an expired read, once, using server-side credentials.
            self.login(*self._credentials)
            return super().request(path)
    def close(self):
        if self._credentials:
            try:super().logout()
            except Exception:pass
            self._credentials=None
        super().close()

SECRET=re.compile(r'password|passwd|secret|token|sessionid|^sid$|mysidindex|privatekey|encryptionkey|community|credential|^cid$',re.I)
SKIP={'privilege','LOGIN','RESP','SMStatus','MsgStatus'}
HEALTH={'0':'Unknown','1':'Information','2':'OK','3':'Warning','4':'Critical','5':'Non-recoverable'}
STATUS_FIELDS={'ObjStatus','ProbeStatus','RedundencyStatus','Severity'}

def display_value(name,value):
    if name in STATUS_FIELDS:return HEALTH.get(value,'Unknown')+' (code '+value+')'
    return value

LABELS={
 'ObjStatus':'Overall health','ProbeStatus':'Sensor health','ProbeReading':'Reading','ProbeLocation':'Location',
 'ProbeFormat':'Sensor type','ProbeReadingValue':'Raw reading','TemperatureProbeList':'Temperature sensors',
 'FanProbeList':'Fan sensors','VoltageProbeList':'Voltage sensors','CurrentProbeList':'Current sensors',
 'ProbeThresholds':'Thresholds','UNRThreshold':'Upper non-recoverable threshold','UCThreshold':'Upper critical threshold',
 'UNCThreshold':'Upper warning threshold','LNCThreshold':'Lower warning threshold','LCThreshold':'Lower critical threshold',
 'LNRThreshold':'Lower non-recoverable threshold','Redundency':'Redundancy flags','RedundencyState':'Redundancy',
 'RedundencyStatus':'Redundancy health','BiosVersion':'BIOS version','IpAddress':'IP address',
 'IpAddrSource':'DHCP for network address','DhcpEnabled':'DNS servers from DHCP','IpmiLanEnabled':'IPMI over LAN enabled',
 'SOLEnabled':'Serial over LAN enabled','KMPortNumber':'Keyboard / mouse port','VideoPortNumber':'Video port',
 'DnsEnabled':'DNS registration','DomainNameDhcp':'DNS domain from DHCP','Server1':'Preferred DNS server','Server2':'Alternate DNS server',
 'AutoNegotiation':'Automatic link negotiation','SCLEnabled':'System configuration lock enabled',
 'LocalCfgUsingRomDisabled':'Local configuration via ROM disabled','LocalCfgUsingRACADMDisabled':'Local configuration via RACADM disabled',
 'PEFAlertingEnable':'Platform event alerts','entryEnable':'Destination enabled','emailAddr':'Email address','emailDesc':'Email description',
 'login':'Log in to DRAC','cfg':'Configure DRAC','cfguser':'Configure users','clearlog':'Clear logs permission','servercontrol':'Server control permission','console':'Console access','vmedia':'Virtual media access','testalert':'Test alerts permission','debug':'Diagnostics permission',
 'evtFltrActionPwrCycl':'Power cycle on event','evtFltrActionReset':'Reset on event','evtFltrActionPwrOff':'Power off on event','evtFltrActionAlert':'Generate alert on event','evtFltrActionPwrReduction':'Reduce power on event',
 'PSLocation':'Location','PSWattage':'Rated power (W)','PSState':'State','PSType':'Supply type',
}

def label(value):
    if value in LABELS:return LABELS[value]
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])',' ',value).replace('_',' ')

@dataclass(frozen=True)
class FieldRow:
    group: str
    field: str
    value: str
    kind: str = 'text'
    checked: bool | None = None
    changeability: str = 'unknown'
    evidence: str = ''
    key: str = ''
    edit: dict | None = None

def field_rows(data: bytes, endpoint='', capture=None, *, root=None) -> list[FieldRow]:
    """Retain repeated log/sensor records; never execute device XSL or HTML."""
    if len(data)>8_000_000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unsafe or oversized device XML')
    if root is None:root=ET.fromstring(data)
    if root.tag!='drac' or root.find('LOGIN') is not None:
        raise ValueError('Expected authenticated DRAC status XML')
    rows=[]
    def append(scope,name,value,unit='',node=None):
        spec=field_spec(endpoint,name)
        rendered=display_value(name,value) if value else 'Not reported'
        checked=None;kind='text'
        if spec.control in ('switch','truth') or value.lower() in ('true','false'):
            kind='boolean'
            checked={'0':False,'1':True,'false':False,'true':True}.get(value.lower()) if not unit else None
            if checked is not None:
                rendered=('True' if checked else 'False') if spec.control=='truth' or (spec.control!='switch' and value.lower() in ('true','false')) else ('Enabled' if checked else 'Disabled')
            elif value:rendered='Unknown (code '+value+')'
        elif spec.control=='choice' and value:
            rendered=dict(spec.choices).get(value,'Unknown (code '+value+')')
            if set(dict(spec.choices))=={'0','1'} and value in ('0','1'):
                kind='binary-choice';checked=value=='1'
        key=hashlib.sha256((endpoint+'\0'+scope+'\0'+name).encode()).hexdigest()[:24]
        rows.append(FieldRow(scope,label(name),rendered,kind,checked,spec.changeability,spec.evidence,key))
        if capture is not None:capture(key,node,name)
    def visit(node,scope):
        name=node.get('name',node.tag)
        if node.tag in SKIP or SECRET.search(name):return
        if node.tag=='property':
            value=node.findtext('value',default='')
            append(scope,name,value.strip(),node=node)
            return
        if not list(node):
            text=(node.text or '').strip()
            unit=node.get('unit','')
            if unit:text=(text+' '+unit).strip()
            append(scope,name,text,unit,node)
            return
        counts={}
        for child in node:
            key=child.get('name',child.tag)
            counts[key]=counts.get(key,0)+1
            total=sum(c.get('name',c.tag)==key for c in node)
            location=child.findtext('ProbeLocation') or child.findtext('PSLocation') or child.findtext('IntrusionLoc')
            part=(location.strip() if location else label(key))+(f' [{counts[key]}]' if total>1 else '')
            child_scope=scope
            if list(child) and child.tag!='property':
                child_scope=(scope+' / '+part).strip(' /')
            visit(child,child_scope)
    visit(root,'')
    if not rows:raise ValueError('No status fields were reported')
    return rows

def status_rows(data: bytes) -> list[tuple[str,str,str]]:
    return [(row.group,row.field,row.value) for row in field_rows(data)]

def fetch_page(device,page,*,detailed=False):
    rows=[];errors=[]
    for endpoint in page.endpoints:
        try:
            data=device.request('/cgi-bin/webcgi/'+endpoint)
            for row in field_rows(data,endpoint):
                if page.key=='firmware' and not any(word in row.field.lower() for word in ('firmware','bios')):continue
                group=label(endpoint)+((' / '+row.group) if row.group else '')
                if detailed:rows.append(FieldRow(group,row.field,row.value,row.kind,row.checked,row.changeability,row.evidence,row.key,row.edit))
                else:rows.append((group,row.field,row.value))
        except Exception as exc:
            errors.append(endpoint+': '+str(exc))
    return rows,errors
