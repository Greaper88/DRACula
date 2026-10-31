# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Staged DRAC 5 settings with selected-target, single-use exact-change confirmations."""
import copy,hashlib,ipaddress,json,re,secrets,threading,time
from dataclasses import dataclass,replace
from urllib.parse import urlencode
from xml.etree import ElementTree as ET
from .field_schema import SPECS,field_spec
from .status import BY_KEY,SECRET,field_rows,label,FieldRow

TTL=120
PERMISSIONS=('login','cfg','cfguser','clearlog','servercontrol','console','vmedia','testalert','debug')
PERMISSION_INPUTS=('loginDrac','configureDrac','configureDracUsers','clearDracLogs','executeDracServerControls','accessDracConsole','accessDracMedia','testDracAlerts','executeDracDiags')
ROUTES={'nic','services','serial','sol','ad','user','adrgconfig','vkvmconfig','vmconfig','listpef','pef','pefdest','pefemail','lpefemail'}
GLOBAL_ENDPOINTS={'nic','services','serial','sol','ad','vkvmconfig','vmconfig'}
ALIASES={'serial':{'SerialEnabled':'Enabled'},'lpefdest':{'entryEnable':'EnableDestination','AlertingIPAddr':'DestIPAddress1'},'lpefemail':{'entryEnable':'EnableEmailAlert','emailAddr':'EmailAddress','emailDesc':'EmailDesc'},'listpef':{'PEFAlertingEnable':'alertsEnable','evtFltrActionAlert':'GenerateAlert'}}
LENGTHS={'UserName':16,'RacName':63,'DomainName':254,'RootDomain':254,'RacDomain':254,'DomainController':254,'GlobalCatalog':254,'RoleGroupName':254,'RoleGroupDomain':254,'LoginCommand':128,'EscapeKey':3,'emailAddr':64,'emailDesc':32}
NUMBERS={'VLanId':(1,4094),'VLanPriority':(0,7),'WebServerTimeout':(60,1920),'SshTimeout':(60,1920),'TelnetTimeout':(60,1920),'SerialTimeout':(60,1920),'HistBufSize':(0,8192),'Timeout':(15,300)}
IPS={'IpAddress','Gateway','SubnetMask','Server1','Server2','SMTPAddress','AlertingIPAddr'}
BAUD={'BaudRate':('9600','19200','57600','115200'),'SerialBaudRate':('9600','28800','57600','115200')}

FORM_FIELDS={
 'nic':'Mode Enabled IpAddrSource IpAddress Gateway SubnetMask Speed Duplex AutoNegotiation DhcpEnabled Server1 Server2 DnsEnabled RacName DomainNameDhcp DomainName IpmiLanEnabled MinPrivilege EncryptionKey VLanEnabled VLanId VLanPriority',
 'services':'LocalCfgUsingRomDisabled LocalCfgUsingRACADMDisabled WebServerEnabled WebServerTimeout HttpPortNumber HttpsPortNumber SshEnabled SshTimeout SshPortNumber TelnetEnabled TelnetTimeout TelnetPortNumber RacadmEnabled SnmpEnabled CommunityName AsrEnabled',
 'serial':'ConnectionMode BaudRate FlowControl ChannelPrivLimit SerialEnabled RedirectEnabled SerialTimeout SerialBaudRate EscapeKey HistBufSize LoginCommand',
 'sol':'Enabled BaudRate ChannelPrivLimit',
 'ad':'Enabled SSOEnabled RacName RootDomain RacDomain Timeout Type FilterEnable DomainController GlobalCatalog',
 'vkvmconfig':'Enabled KMPortNumber VideoPortNumber EncryptionEnabled LocalServerVideo PluginType AuthorizeMultipleSessions',
 'vmconfig':'Attached PortNumber SslPortNumber KeyEnabled BootOnceEnabled PluginType',
 'user':'UserID Enabled UserName RacPrivilege LanPrivilege SerialPrivilege SOLEnabled IsPasswordSet',
 'adrgconfig':'RoleGroupId RoleGroupName RoleGroupDomain RoleGroupPrivilge',
 'listpef':'PEFAlertingEnable',
 'pef':'filterNumber filterKey evtFltrActionAlert evtFltrActionPwrCycl evtFltrActionReset evtFltrActionPwrOff evtFltrActionPwrReduction',
 'pefdest':'destSelector entryEnable AlertingIPAddr',
 'pefemail':'destSelector entryEnable emailAddr emailDesc',
 'lpefemail':'SMTPAddress',
}

class ConfigError(ValueError):pass

def writable(host):
    try:ipaddress.IPv4Address(host);return True
    except (ValueError,TypeError):return False

def require_write(host):
    if not writable(host):raise ConfigError('Select a valid configured device before applying settings.')

def parse(data):
    if len(data)>8_000_000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ConfigError('Unsafe settings response')
    root=ET.fromstring(data)
    if root.tag!='drac' or root.find('LOGIN') is not None:raise ConfigError('Authenticated settings could not be read')
    return root

def flat(node):
    result={}
    for n in node:
        if n.tag=='property':result[n.get('name')]=n.findtext('value','').strip()
        elif not list(n):result[n.tag]=(n.text or '').strip()
    return result

def truth(value):
    if value not in ('0','1','true','false'):raise ConfigError('An unsupported flag value prevents safe submission')
    return value in ('1','true')

def canonical(name,value,spec):
    if spec.control in ('switch','truth'):return '1' if truth(value) else '0'
    return value

def constraint(endpoint,name,record):
    spec=field_spec(endpoint,name)
    if spec.changeability!='configurable' or SECRET.search(name):return None
    result={'type':'text','max_length':LENGTHS.get(name,254)}
    if spec.control in ('switch','truth'):result={'type':'boolean','on':'True' if spec.control=='truth' else 'Enabled','off':'False' if spec.control=='truth' else 'Disabled'}
    elif spec.choices:
        choices=list(spec.choices)
        if endpoint=='nic' and name=='Mode' and record.get('NumberOfNics')=='1':choices=[p for p in choices if p[0]!='1']
        if endpoint=='vmconfig' and name=='BootOnceEnabled':
            if record.get('BootOnceSupport')!='1':choices=[(k,'Virtual media' if k=='1' else v) for k,v in choices if k in ('0','1','4')]
            else:choices=[(k,'vFlash' if k=='1' else v) for k,v in choices]
        result={'type':'choice','choices':[{'value':k,'label':v} for k,v in choices]}
    elif name in BAUD:result={'type':'choice','choices':[{'value':v,'label':v+' bps'} for v in BAUD[name]]}
    elif name.endswith('PortNumber'):result={'type':'number','min':1,'max':65535}
    elif name in NUMBERS:
        low,high=NUMBERS[name];result={'type':'number','min':low,'max':high,'allow_zero':name in ('SshTimeout','TelnetTimeout','SerialTimeout')}
    return result

def validate(endpoint,name,value,record):
    if type(value) is not str or len(value)>254 or re.search(r'[\x00-\x1f\x7f]',value):raise ConfigError('Invalid setting value')
    c=constraint(endpoint,name,record)
    if not c:raise ConfigError('That field is not available for editing')
    if c['type']=='boolean':
        if value not in ('0','1'):raise ConfigError('Choose an on or off value')
    elif c['type']=='choice':
        if value not in {p['value'] for p in c['choices']}:raise ConfigError('Choose one of the supported options')
    elif c['type']=='number':
        if not re.fullmatch(r'0|[1-9][0-9]*',value) or not(c['min']<=int(value)<=c['max'] or c.get('allow_zero') and value=='0'):raise ConfigError(label(name)+' is outside its supported range')
    elif len(value)>c['max_length']:raise ConfigError(label(name)+' is too long')
    if name in IPS:
        try:ipaddress.IPv4Address(value)
        except ValueError:raise ConfigError(label(name)+' needs an IPv4 address')
    if name=='SubnetMask':
        try:ipaddress.IPv4Network('0.0.0.0/'+value)
        except ValueError:raise ConfigError('Use a contiguous subnet mask')
    if name in ('RacName','DomainName','RootDomain','RacDomain','DomainController','GlobalCatalog') and value and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*',value):raise ConfigError(label(name)+' contains unsupported characters')
    if name=='UserName' and (not value or not re.fullmatch(r'[A-Za-z0-9_.-]{1,16}',value)):raise ConfigError('Use a non-empty username of up to 16 letters, digits, dots, underscores or hyphens')
    if name=='emailAddr' and value and not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+',value):raise ConfigError('Enter a valid email address')
    if name=='EscapeKey' and not re.fullmatch(r'\^[@A-Z\[\\\]\^_]|[\x20-\x7e]{1,3}',value):raise ConfigError('Enter a supported serial escape sequence')
    return value

@dataclass
class Record:
    endpoint:str
    route:str
    selector:str
    selector_value:str
    values:dict
    permission:str='cfg'
    def identity(self):return (self.endpoint,self.route,self.selector,self.selector_value)

@dataclass
class Snapshot:
    page:str
    rows:list
    bindings:dict
    records:dict
    roots:dict
    revision:str
    target:str


def record_for(endpoint,node,parents):
    current=node
    while current is not None:
        if endpoint=='users' and current.tag=='object' and current.get('name')=='user':
            values=flat(current);return Record(endpoint,'user','index',values.get('UserID',''),values,'cfguser')
        if endpoint=='ad' and current.tag=='RoleGroupList':
            values=flat(current);return Record(endpoint,'adrgconfig','RoleGroupId',values.get('RoleGroupId',''),values)
        if endpoint=='listpef' and current.tag=='eventFilterList':
            values=flat(current);return Record(endpoint,'pef','PefIndex',values.get('filterNumber',''),values)
        if endpoint=='lpefdest' and current.tag=='LANAlertDestList':
            values=flat(current);return Record(endpoint,'pefdest','PefDestIndex',values.get('destSelector',''),values)
        if endpoint=='lpefemail' and current.tag=='EmailAlertDestList':
            values=flat(current);return Record(endpoint,'pefemail','EmailAlertIndex',values.get('destSelector',''),values)
        current=parents.get(current)
    if endpoint in GLOBAL_ENDPOINTS:
        matches=[n for n in parents if n.tag=='object']
        if len(matches)!=1:raise ConfigError('Settings record is ambiguous')
        return Record(endpoint,endpoint,'','',flat(matches[0]))
    if endpoint=='listpef':
        root=next(n for n in parents.values() if n.tag=='drac')
        return Record(endpoint,endpoint,'','',{'PEFAlertingEnable':root.findtext('.//PEFAlertingEnable','')})
    if endpoint=='lpefemail':
        root=next(n for n in parents.values() if n.tag=='drac')
        return Record(endpoint,endpoint,'','',{'SMTPAddress':root.findtext('SMTPAddress','')})
    raise ConfigError('No reviewed submission form for this field')

def permission(root,record):
    privileges=root.find('privilege')
    return privileges is not None and privileges.get(record.permission)=='1' and record.values.get('SCLEnabled','0') not in ('1','true')

def preserved(record):
    """Only stable configuration and identity enter the concurrency fingerprint."""
    values={k:v for k,v in record.values.items() if (record.endpoint,k) in SPECS and SPECS[record.endpoint,k].changeability=='configurable' or SECRET.search(k) and 'session' not in k.lower()}
    for key in ('UserID','RacPrivilege','RoleGroupId','RoleGroupPrivilge','index','filterNumber','filterKey','destSelector','NumberOfNics','BootOnceSupport','SCLEnabled'):
        if key in record.values:values[key]=record.values[key]
    return values

def state_values(record):
    values=preserved(record)
    for name,value in list(values.items()):
        spec=field_spec(record.endpoint,name)
        if spec.control in ('switch','truth'):values[name]=canonical(name,value,spec)
    if record.route in ('user','adrgconfig'):
        name='RacPrivilege' if record.route=='user' else 'RoleGroupPrivilge'
        try:mask=int(record.values[name],16) if record.values[name].lower().startswith('0x') else int(record.values[name])
        except (KeyError,ValueError):raise ConfigError('Unsupported privilege mask')
        values[name]=str(mask)
        for i,flag in enumerate(PERMISSIONS):values[flag]='1' if mask&(1<<i) else '0'
    return values

def fingerprint(record):return hashlib.sha256(json.dumps(state_values(record),sort_keys=True).encode()).hexdigest()

def expected_record(record,proposed):
    result=copy.deepcopy(record);result.values.update(proposed)
    if record.route in ('user','adrgconfig'):
        name='RacPrivilege' if record.route=='user' else 'RoleGroupPrivilge'
        mask=int(state_values(record)[name])
        for i,flag in enumerate(PERMISSIONS):
            if flag in proposed:mask=mask|(1<<i) if proposed[flag]=='1' else mask&~(1<<i)
        result.values[name]=str(mask)
    return result

def permitted_names(record):
    return [name for (endpoint,name),spec in SPECS.items() if endpoint==record.endpoint and spec.changeability=='configurable' and name in record.values and not SECRET.search(name)]

def form_payload(record,proposed):
    values=copy.deepcopy(record.values);values.update(proposed);route=record.route
    if route not in FORM_FIELDS or not set(FORM_FIELDS[route].split())<=record.values.keys():raise ConfigError('Incomplete settings form; refusing to submit missing fields')
    if route=='pef' and 'evtFltrActionPwrReduction' in proposed and truth(proposed['evtFltrActionPwrReduction']) and values.get('filterKey') not in ('1048835','524547'):raise ConfigError('Power reduction is not supported for this filter')
    params={'caller':'','pageCode':'','pageName':''}
    if route not in ('nic','pef','pefdest','pefemail','listpef','adrgconfig','lpefemail'):params['pageId']='1' if route=='ad' else ''
    if record.selector:
        if not re.fullmatch(r'[0-9]{1,3}',record.selector_value):raise ConfigError('Invalid settings record identifier')
        limits={'user':(2,16),'adrgconfig':(1,5),'pef':(0,17),'pefdest':(0,4),'pefemail':(0,4)}
        if route not in limits or not limits[route][0]<=int(record.selector_value)<=limits[route][1]:raise ConfigError('Unsupported settings record identifier')
        params[record.selector]=record.selector_value
    if route=='user':
        if not 2<=int(record.selector_value)<=16:raise ConfigError('The reserved user slot is not editable')
        params['UserID']=record.selector_value;params['Password']='';params['ConfirmPassword']=''
        if truth(values.get('Enabled','0')) and (not values.get('UserName') or not truth(values.get('IsPasswordSet','0'))):raise ConfigError('Enabling a user requires an existing name and password. Password creation is not part of this editor.')
    names=permitted_names(record)
    if route=='ad':names=[n for n in names if n not in PERMISSIONS+('RoleGroupName','RoleGroupDomain')]
    if route=='adrgconfig':names=[n for n in names if n in PERMISSIONS+('RoleGroupName','RoleGroupDomain')]
    if route=='listpef':names=['PEFAlertingEnable']
    if route=='pef':names=['evtFltrActionAlert']
    if route=='lpefemail':names=['SMTPAddress']
    for name in names:
        if name in PERMISSIONS:continue
        spec=field_spec(record.endpoint,name);key=ALIASES.get(record.endpoint,{}).get(name,name)
        if spec.control in ('switch','truth'):
            if truth(values[name]):
                # DRAC flags are successful checkbox controls; absent means unchecked.
                params[key]='' if route in ('sol','listpef') else 'on' if route=='ad' else '1'
        else:params[key]=values[name]
    if route in ('nic','services'):
        key='EncryptionKey' if route=='nic' else 'CommunityName';secret=record.values.get(key)
        if secret is None or re.fullmatch(r'\*+|[xX]{4,}',secret or ''):raise ConfigError('An unchanged secret is unavailable; refusing to overwrite this form')
        params[key]=secret
    if route in ('user','adrgconfig'):
        mask_name='RacPrivilege' if route=='user' else 'RoleGroupPrivilge'
        try:mask=int(record.values[mask_name],0) if record.values[mask_name].startswith('0x') else int(record.values[mask_name])
        except (KeyError,ValueError):raise ConfigError('The current privilege mask could not be preserved')
        if not 0<=mask<=511:raise ConfigError('Unsupported privilege mask')
        for i,name in enumerate(PERMISSIONS):
            if name in proposed:mask=(mask|(1<<i)) if truth(proposed[name]) else (mask&~(1<<i))
            if mask&(1<<i):params[PERMISSION_INPUTS[i]]='1'
        params[mask_name]=str(mask) if mask in (0,1,249,511) else '15'
    if route=='pef':
        actions=('evtFltrActionPwrOff','evtFltrActionReset','evtFltrActionPwrCycl','evtFltrActionPwrReduction');active=[i+1 for i,n in enumerate(actions) if truth(values.get(n,'false'))]
        if len(active)>1:raise ConfigError('Choose at most one event power action')
        params['ShutdownMode']=str(active[0] if active else 0)
    # Basic cross-field constraints from the original forms.
    for a,b in (('HttpPortNumber','HttpsPortNumber'),('KMPortNumber','VideoPortNumber'),('PortNumber','SslPortNumber')):
        if a in values and b in values:
            if values[a]==values[b] or (a in proposed and proposed[a]==record.values.get(b)) or (b in proposed and proposed[b]==record.values.get(a)):raise ConfigError('Those ports must be distinct and cannot be swapped in one Apply')
    if route=='ad' and truth(values.get('SSOEnabled','0')) and not truth(values.get('Enabled','0')):raise ConfigError('Directory services must be enabled before SSO')
    return urlencode(params).encode()

class ConfigEditor:
    def __init__(self,device):
        self.device=device;self.lock=threading.RLock();self.snapshots={};self.plans={}
    def close(self):
        with self.lock:self.snapshots.clear();self.plans.clear()
    def _read(self,page):
        rows=[];bindings={};records={};roots={};revision=secrets.token_urlsafe(24)
        for endpoint in BY_KEY[page].endpoints:
            data=self.device.request('/cgi-bin/webcgi/'+endpoint);root=parse(data);roots[endpoint]=root
            parents={child:parent for parent in root.iter() for child in parent};captured={}
            parsed=field_rows(data,endpoint,lambda key,node,name:captured.__setitem__(key,(node,name)),root=root)
            if len({r.key for r in parsed})!=len(parsed):raise ConfigError('Ambiguous duplicate settings fields')
            for row in parsed:
                descriptor=None;evidence=row.evidence
                if writable(self.device.host) and row.changeability=='configurable':
                    node,name=captured[row.key]
                    try:
                        record=record_for(endpoint,node,parents)
                        if record.route=='user' and (not record.selector_value.isdecimal() or int(record.selector_value)<2):raise ConfigError('Reserved user')
                        if record.identity() in records:record=records[record.identity()]
                        else:records[record.identity()]=record
                        if not permission(root,record):raise ConfigError('Controller permissions or configuration lock prevent editing')
                        if name=='evtFltrActionPwrReduction' and record.values.get('filterKey') not in ('1048835','524547'):raise ConfigError('Unsupported filter control')
                        descriptor=constraint(endpoint,name,record.values)
                        raw=record.values.get(name,'');raw=canonical(name,raw,field_spec(endpoint,name))
                        if descriptor is None:raise ConfigError('No verified editor')
                        if descriptor['type'] in ('boolean','choice'):validate(endpoint,name,raw,record.values)
                        # Prove this form can preserve its unchanged data before enabling an editor.
                        form_payload(record,{})
                        descriptor=descriptor|{'value':raw,'revision':revision}
                        evidence='Reviewed form control. Changes are staged until you review and confirm Apply.'
                        bindings[row.key]=(record.identity(),name,row)
                    except ConfigError as exc:descriptor=None;evidence=row.evidence+' Editing unavailable: '+str(exc)
                rows.append(replace(row,group=label(endpoint)+((' / '+row.group) if row.group else ''),edit=descriptor,evidence=evidence))
        return Snapshot(page,rows,bindings,records,roots,revision,self.device.host)
    def read(self,page):
        with self.lock:
            snapshot=self._read(page);self.snapshots[snapshot.revision]=snapshot
            if len(self.snapshots)>32:self.snapshots.pop(next(iter(self.snapshots)))
            return snapshot.rows
    def review(self,page,changes,owner,revision):
        with self.lock:
            require_write(self.device.host)
            if page not in BY_KEY or type(changes) is not dict or not 1<=len(changes)<=100:raise ConfigError('Choose at least one valid settings change')
            before=self.snapshots.get(revision)
            if before is None or before.page!=page or before.target!=self.device.host:raise ConfigError('Refresh this device page before editing')
            now=self._read(page);groups={};summary=[]
            for key,value in changes.items():
                if key not in before.bindings or key not in now.bindings:raise ConfigError('A selected field is unavailable; refresh the page')
                identity,name,row=before.bindings[key];record=now.records.get(identity)
                if now.bindings[key][:2]!=(identity,name):raise ConfigError('Record identities changed; refresh the page')
                if not record or fingerprint(before.records[identity])!=fingerprint(record):raise ConfigError('Settings changed since they were loaded. Refresh and review again.')
                value=validate(record.endpoint,name,value,record.values)
                old=canonical(name,record.values[name],field_spec(record.endpoint,name))
                if value==old:continue
                groups.setdefault(identity,{})[name]=value
                spec=field_spec(record.endpoint,name)
                options={c['value']:c['label'] for c in constraint(record.endpoint,name,record.values).get('choices',[])}
                display=lambda v: ('True' if v=='1' else 'False') if spec.control=='truth' else ('Enabled' if v=='1' else 'Disabled') if spec.control=='switch' else options.get(v,v)
                summary.append({'group':row.group,'field':row.field,'before':display(old),'after':display(value)})
            if not groups:raise ConfigError('There are no changed values to apply')
            operations=[]
            for identity,proposed in groups.items():
                record=now.records[identity];payload=form_payload(record,proposed)
                operations.append((record,proposed,payload,fingerprint(record)))
            if any(r.route=='user' for r,_,_,_ in operations):
                names={}
                for r in now.records.values():
                    if r.route=='user':names[r.identity()]=r.values.get('UserName','')
                for r,proposed,_,_ in operations:
                    if r.route=='user':names[r.identity()]=proposed.get('UserName',names.get(r.identity(),''))
                nonempty=[n for n in names.values() if n]
                if len(nonempty)!=len(set(nonempty)):raise ConfigError('That username is already assigned to another user')
            token=secrets.token_urlsafe(32)
            self.plans={k:v for k,v in self.plans.items() if v['expires']>time.monotonic()}
            if len(self.plans)>=16:self.plans.clear()
            self.plans[token]={'owner':owner,'host':self.device.host,'page':page,'expires':time.monotonic()+TTL,'operations':operations}
            routes={r.route for r,_,_,_ in operations};warnings=['Only '+self.device.host+' will receive this reviewed batch.']
            if 'nic' in routes:warnings.append('Network changes can disconnect management. The app will continue using the current address and will not follow a changed address automatically.')
            if 'services' in routes:warnings.append('Disabling services or changing ports can remove management access. The app currently expects HTTPS on port 443.')
            if routes&{'user','ad','adrgconfig'}:warnings.append('Account or directory changes can remove login access, including your current account.')
            if 'vkvmconfig' in routes:warnings.append('These settings can disconnect KVM or make the legacy viewer incompatible.')
            if 'vmconfig' in routes:warnings.append('Media attachment and boot-device settings can affect connected media and the next server boot.')
            if routes&{'listpef','pef'}:warnings.append('Event filters can trigger server power actions when an event occurs.')
            if routes&{'serial','sol'}:warnings.append('Serial console access may be interrupted.')
            warnings.append('No automatic retry or rollback will be attempted.')
            return {'token':token,'target':self.device.host,'page':BY_KEY[page].title,'changes':summary,'expires_in':TTL,'warning':' '.join(warnings)}
    def cancel(self,token,owner):
        with self.lock:
            plan=self.plans.get(token)
            if plan and plan['owner']==owner:self.plans.pop(token,None)
    def confirm(self,token,owner,confirmed):
        with self.lock:
            require_write(self.device.host)
            plan=self.plans.get(token)
            if confirmed is not True or not plan or plan['owner']!=owner or plan['host']!=self.device.host:raise ConfigError('A matching explicit confirmation is required')
            self.plans.pop(token,None)  # Consume before reading or sending: never replay a write.
            if plan['expires']<=time.monotonic():raise ConfigError('This review expired. Review the changes again.')
            current=self._read(plan['page'])
            for record,_,_,digest in plan['operations']:
                actual=current.records.get(record.identity())
                if not actual or not permission(current.roots[record.endpoint],actual) or fingerprint(actual)!=digest:raise ConfigError('Settings changed after review. No settings were sent; refresh and review again.')
            completed=0
            for record,proposed,payload,digest in plan['operations']:
                require_write(self.device.host)
                latest=self._read(plan['page']);actual=latest.records.get(record.identity())
                if not actual or not permission(latest.roots[record.endpoint],actual) or fingerprint(actual)!=digest:
                    self.snapshots.clear()
                    return {'status':'stopped','verified_operations':completed,'message':'Settings changed during Apply. Remaining changes were not sent; refresh and review them again.'}
                path='/cgi-bin/webcgi/'+record.route
                if record.selector:
                    if not re.fullmatch(r'[0-9]{1,3}',record.selector_value):raise ConfigError('Invalid settings record identifier')
                    path+='?index='+record.selector_value
                    if record.route in ('pefdest','pefemail'):path+='&test=0'
                if record.route not in ROUTES:raise ConfigError('Unsupported settings form')
                # This is the sole configuration POST path. Public read clients remain read-only.
                try:self.device._exchange(path,payload)
                except Exception:pass  # A redirect/drop is ambiguous; read back, never repeat the POST.
                if record.route=='nic' and 'IpAddress' in proposed and proposed['IpAddress']!=self.device.host:
                    self.snapshots.clear()
                    return {'status':'unknown','verified_operations':completed,'message':'The address change was submitted once. This app will not follow a changed address automatically. Verify the controller at the new address before reconnecting.'}
                try:
                    after=self._read(plan['page']);actual=after.records.get(record.identity())
                    matched=actual is not None and fingerprint(actual)==fingerprint(expected_record(record,proposed))
                except Exception:matched=False
                if not matched:
                    self.snapshots.clear()
                    return {'status':'unknown','verified_operations':completed,'message':str(completed)+' earlier groups were verified. The latest submission outcome could not be verified. Remaining changes were stopped. Do not retry until the controller settings have been checked.'}
                completed+=1
            self.snapshots.clear()
            return {'status':'verified','verified_operations':completed,'message':'Changes applied and read back successfully.'}
