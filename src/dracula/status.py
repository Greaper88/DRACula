"""Read-only DRAC 5 page catalog and normalized status rows shared by UIs."""
from dataclasses import dataclass
import re
from xml.etree import ElementTree as ET
from .launcher import Device

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
 'IpAddrSource':'Address source','DhcpEnabled':'DHCP enabled','IpmiLanEnabled':'IPMI over LAN enabled',
 'SOLEnabled':'Serial over LAN enabled','KMPortNumber':'Keyboard / mouse port','VideoPortNumber':'Video port',
 'PSLocation':'Location','PSWattage':'Rated power (W)','PSState':'State','PSType':'Supply type',
}

def label(value):
    if value in LABELS:return LABELS[value]
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])',' ',value).replace('_',' ')

def status_rows(data: bytes) -> list[tuple[str,str,str]]:
    """Retain repeated log/sensor records; never execute device XSL or HTML."""
    if len(data)>8_000_000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unsafe or oversized device XML')
    root=ET.fromstring(data)
    if root.tag!='drac' or root.find('LOGIN') is not None:
        raise ValueError('Expected authenticated DRAC status XML')
    rows=[]
    def visit(node,scope):
        name=node.get('name',node.tag)
        if node.tag in SKIP or SECRET.search(name):return
        if node.tag=='property':
            value=node.findtext('value',default='')
            rows.append((scope,label(name),display_value(name,value.strip()) if value.strip() else 'Not reported'))
            return
        if not list(node):
            text=(node.text or '').strip()
            unit=node.get('unit','')
            if unit:text=(text+' '+unit).strip()
            rows.append((scope,label(name),display_value(name,text) if text else 'Not reported'))
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

def fetch_page(device,page):
    rows=[];errors=[]
    for endpoint in page.endpoints:
        try:
            data=device.request('/cgi-bin/webcgi/'+endpoint)
            for scope,name,value in status_rows(data):
                if page.key=='firmware' and not any(word in name.lower() for word in ('firmware','bios')):continue
                rows.append((label(endpoint)+((' / '+scope) if scope else ''),name,value))
        except Exception as exc:
            errors.append(endpoint+': '+str(exc))
    return rows,errors
