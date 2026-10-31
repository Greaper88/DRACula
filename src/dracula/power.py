# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared target-bound, single-use confirmation for power capabilities."""
import secrets,time
from urllib.parse import urlencode
from .configuration import ConfigError,parse

ACTIONS=(('on','Power on'),('off','Power off'),('cycle','Power cycle'),('reset','Reset'),('soft','Graceful shutdown'))
HTTP_VALUES={'on':'1','off':'0','reset':'2','cycle':'3'}

class Drac5Power:
    name='DRAC HTTP'
    def __init__(self,device):self.device=device
    @property
    def host(self):return self.device.host
    def power_status(self):
        root=parse(self.device.request('/cgi-bin/webcgi/power'));values=[]
        for n in root.iter():
            if n.get('name',n.tag)=='PowerStatus':values.append((n.findtext('value') if n.tag=='property' else n.text or '').strip().upper())
        state=values[0] if len(values)==1 and values[0] in ('ON','OFF') else 'UNKNOWN'
        privilege=root.find('privilege');allowed=privilege is not None and privilege.get('servercontrol')=='1'
        return state,allowed
    def submit_power(self,action):
        if action not in HTTP_VALUES:raise ConfigError('Unsupported DRAC power action')
        self.device._exchange('/cgi-bin/webcgi/power',urlencode({'caller':'','pageCode':'','pageId':'','pageName':'','action':HTTP_VALUES[action]}).encode('ascii'))

class PowerController:
    def __init__(self,host,http,ipmi):self.host=host;self.http=http;self.ipmi=ipmi;self.snapshot=None;self.plans={}
    def _read(self):
        states={}
        if self.http:
            try:states['DRAC HTTP']=(*self.http.power_status(),self.http)
            except Exception:pass
        # Probe IPMI for graceful shutdown, or for all controls if HTTP is down.
        try:states['IPMI']=(*self.ipmi.power_status(),self.ipmi)
        except Exception:pass
        primary=states.get('DRAC HTTP')
        if not primary or primary[0]=='UNKNOWN':primary=states.get('IPMI',('UNKNOWN',False,None))
        state=primary[0];actions=[];bindings={}
        conflict=any(s[0] in ('ON','OFF') and s[0]!=state for s in states.values())
        for key,label in ACTIONS:
            selected=states.get('IPMI') if key=='soft' else primary
            source='IPMI' if key=='soft' or primary[2] is self.ipmi else 'DRAC HTTP'
            enabled=bool(selected and selected[1] and state in ('ON','OFF') and not conflict and (state=='OFF' if key=='on' else state=='ON'))
            reason='' if enabled else ('Power sources disagree; refresh before acting.' if conflict else 'Power state is unknown.' if state=='UNKNOWN' else 'Unavailable through this connection or permission.' if not selected or not selected[1] else 'Requires the machine to be '+('off.' if key=='on' else 'on.'))
            actions.append({'id':key,'label':label,'supported':selected is not None,'enabled':enabled,'reason':reason,'source':source})
            if enabled:bindings[key]=selected[2]
        return {'target':self.host,'state':state,'source':primary[2].name if primary[2] else 'Unavailable','actions':actions},bindings
    def status(self):
        model,bindings=self._read();revision=secrets.token_urlsafe(24);model['revision']=revision
        self.snapshot=(model,bindings);return model
    @staticmethod
    def _same(a,b):return {k:v for k,v in a.items() if k!='revision'}=={k:v for k,v in b.items() if k!='revision'}
    def review(self,action,revision,owner):
        if not self.snapshot or self.snapshot[0]['revision']!=revision:raise ConfigError('Refresh power status before reviewing an action.')
        old,_=self.snapshot;model,bindings=self._read()
        if not self._same(old,model):raise ConfigError('Power state or permissions changed. Refresh and review again.')
        if action not in bindings:raise ConfigError('That power action is unavailable in the current state.')
        token=secrets.token_urlsafe(32);label=dict(ACTIONS)[action]
        self.plans={k:v for k,v in self.plans.items() if v[0]>time.monotonic()}
        self.plans[token]=(time.monotonic()+120,owner,self.host,action,model,bindings[action])
        warning=('Requires a running OS with ACPI shutdown support. No forced shutdown will follow.' if action=='soft' else 'This may interrupt the running machine and cause unsaved data to be lost.' if action in ('off','cycle','reset') else 'This will turn on the selected machine.')
        return {'token':token,'target':self.host,'page':'Power','expires_in':120,'warning':warning+' No automatic retry will be attempted.','changes':[{'group':'Power','field':label,'before':model['state'],'after':label+' via '+bindings[action].name}]}
    def cancel(self,token,owner):
        if token in self.plans and self.plans[token][1]==owner:self.plans.pop(token)
    def confirm(self,token,owner,confirmed):
        plan=self.plans.get(token)
        if confirmed is not True or not plan or plan[1]!=owner:raise ConfigError('A matching explicit power confirmation is required.')
        self.plans.pop(token);expiry,_,host,action,before,adapter=plan
        if time.monotonic()>expiry or host!=self.host or adapter.host!=host:raise ConfigError('Power review expired or the selected device changed.')
        current,bindings=self._read()
        if not self._same(before,current) or bindings.get(action) is not adapter:raise ConfigError('Power state, permissions or transport changed. Refresh and review again.')
        try:adapter.submit_power(action)
        except Exception:return {'status':'unknown','message':'Power command outcome is unknown. Check current status/KVM before trying again. No retry was attempted.','verified_operations':0}
        self.snapshot=None
        if action in ('on','off'):
            try:state,_=adapter.power_status()
            except Exception:state='UNKNOWN'
            if state==('ON' if action=='on' else 'OFF'):return {'status':'verified','message':'Power '+state.lower()+' verified.','verified_operations':1}
        return {'status':'submitted','message':'Power request submitted. Refresh status or watch KVM to verify completion. No retry will be attempted.','verified_operations':0}
    def close(self):self.snapshot=None;self.plans.clear()
