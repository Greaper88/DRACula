# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Shared management session: protocol adapters expose only their capabilities.

DRAC 5 HTTP handles vendor settings/KVM metadata; IPMI independently authenticates
and supplies standard BMC status/power. Future Redfish adapters belong here, not
in either UI. A failed write is never routed to a second adapter.
"""
from .configuration import ConfigEditor
from .ipmi import IpmiAdapter
from .power import Drac5Power,PowerController
from .status import BY_KEY,fetch_page,FieldRow
from .ipmi import READS

class ManagementSession:
    def __init__(self,device,user,password):
        self.device=device;self.ipmi=IpmiAdapter(device.host,user,password);self.http_ready=False;self.source='Unavailable';self.closed=False
        try:device.login(user,password);self.http_ready=True;self.source='DRAC HTTP'
        except Exception:
            try:self.ipmi.probe();self.source='IPMI'
            except Exception:
                device.close();self.ipmi.close();raise RuntimeError('Neither DRAC HTTP nor IPMI could authenticate with the saved credentials.') from None
        self.editor=ConfigEditor(device)
        self.power=PowerController(device.host,Drac5Power(device) if self.http_ready else None,self.ipmi)
        self.power_model=None;self._ipmi_pages=None
    def capabilities(self):
        if self.http_ready:return {'pages':list(BY_KEY),'kvm':True,'settings':True,'source':'DRAC HTTP','sol':False}
        if self._ipmi_pages is None:
            self._ipmi_pages=['power']
            for key in READS:
                if key=='power':continue
                try:
                    rows,errors=self.ipmi.page(key)
                    if rows and not errors:self._ipmi_pages.append(key)
                except Exception:pass
        return {'pages':self._ipmi_pages,'kvm':False,'settings':False,'source':'IPMI','sol':False}
    def page(self,key):
        self.power_model=None
        if key=='power':
            self.power_model=self.power.status();p=self.power_model;self.source=p['source']
            if self.source=='IPMI':self.http_ready=False
            return [FieldRow('Power','Power state',p['state'],changeability='read-only'),FieldRow('Connection','Source',p['source'],changeability='read-only')],([] if p['state']!='UNKNOWN' else ['Power status is unavailable.'])
        if self.http_ready:
            page=BY_KEY[key]
            try:
                if any(a.startswith('Apply ') or a=='Edit user' for a in page.actions):
                    rows=self.editor.read(key);errors=[]
                else:rows,errors=fetch_page(self.device,page,detailed=True)
                if not errors:self.source='DRAC HTTP';return rows,errors
                if rows:self.source='DRAC HTTP';return rows,errors
            except Exception:pass
            self.http_ready=False
        try:
            rows,errors=self.ipmi.page(key);self.source='IPMI'
            return rows,['DRAC HTTP unavailable; showing supported IPMI status only.',*errors]
        except Exception:return [],['This page is unavailable through DRAC HTTP and IPMI.']
    def close(self):
        if self.closed:return
        self.closed=True;self.power.close();self.editor.close();self.device.close();self.ipmi.close()
