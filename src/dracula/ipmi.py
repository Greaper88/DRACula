# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Bounded, device-scoped IPMI adapter. No shell or browser-facing credentials."""
import ipaddress,os,re,shutil,subprocess,time
from .status import FieldRow

class IpmiError(RuntimeError):pass

# Try authenticated/encrypted RMCP+ first, then legacy authenticated LAN.
TRANSPORTS=(('-I','lanplus','-C','17'),('-I','lanplus','-C','3'),('-I','lan','-A','MD5'))
READS={'overview':('mc','info'),'rac':('mc','info'),'power':('chassis','status'),
       'sel':('sel','elist'),'fans':('sdr','type','Fan'),'temperatures':('sdr','type','Temperature'),
       'voltages':('sdr','type','Voltage'),'supplies':('sdr','type','Power Supply'),
       'battery':('sdr','type','Battery'),'intrusion':('sdr','type','Physical Security')}
POWER={'on':'on','off':'off','reset':'reset','cycle':'cycle','soft':'soft'}

class IpmiAdapter:
    name='IPMI'
    def __init__(self,host,user,password):
        self.host=str(ipaddress.IPv4Address(host));self.user=user;self.password=password
        self.transport=None;self.privilege=None;self.failed_until=0
    def command(self,command,transport=None,privilege=None):
        binary=shutil.which('ipmitool')
        if not binary:raise IpmiError('IPMI requires ipmitool on the backend host.')
        env=os.environ.copy();env.pop('IPMITOOL_PASSWORD',None);env['IPMI_PASSWORD']=self.password;env['LC_ALL']='C'
        # -R 1 bounds the command response loop to its initial attempt. Never use
        # -R 0 (interpreted as default retries). No application retry after writes.
        args=[binary,* (transport or self.transport),'-H',self.host,'-U',self.user,'-E','-L',privilege or self.privilege,'-N','2','-R','1',*command]
        return args,env
    def _run(self,command,transport=None,privilege=None):
        args,env=self.command(command,transport,privilege)
        try:r=subprocess.run(args,env=env,capture_output=True,timeout=12,check=False)
        except (OSError,subprocess.TimeoutExpired):raise IpmiError('IPMI did not return a definite response.') from None
        if r.returncode:raise IpmiError('IPMI request failed or was not permitted.')
        if len(r.stdout)>2_000_000:raise IpmiError('IPMI response was too large.')
        return r.stdout.decode('utf-8','replace').strip()
    def sol_access(self):
        """Find enabled SOL over an authenticated, encrypted IPMI 2.0 transport."""
        if not shutil.which('ipmitool'):
            return None
        transports = [transport for transport in TRANSPORTS if transport[1] == 'lanplus']
        if self.transport in transports:
            transports.remove(self.transport)
            transports.insert(0, self.transport)
        privilege = self.privilege or 'ADMINISTRATOR'
        for transport in transports:
            try:
                output = self._run(('sol', 'info'), transport, privilege)
            except IpmiError:
                continue
            if re.search(r'^Enabled[ \t]*:[ \t]*true[ \t]*$', output, re.MULTILINE | re.IGNORECASE):
                return transport, privilege
            return None
        return None
    def probe(self):
        if self.transport:return self.state()
        if time.monotonic()<self.failed_until:raise IpmiError('IPMI is unavailable; retry after a minute.')
        if not shutil.which('ipmitool'):raise IpmiError('IPMI requires ipmitool on the backend host.')
        for privilege in ('ADMINISTRATOR','USER'):
            for transport in TRANSPORTS:
                try:
                    state=self._parse_state(self._run(('chassis','power','status'),transport,privilege))
                    self.transport=transport;self.privilege=privilege;return state
                except IpmiError:pass
        self.failed_until=time.monotonic()+60
        raise IpmiError('IPMI login/status unavailable with the saved credentials.')
    @staticmethod
    def _parse_state(output):
        match=re.fullmatch(r'Chassis Power is (on|off)',output,re.I)
        if not match:raise IpmiError('IPMI power state was not recognized.')
        return match[1].upper()
    def state(self):
        if not self.transport:return self.probe()
        return self._parse_state(self._run(('chassis','power','status')))
    def power_status(self):return self.probe(),self.privilege=='ADMINISTRATOR'
    def submit_power(self,action):
        if action not in POWER or not self.transport or self.privilege!='ADMINISTRATOR':raise IpmiError('IPMI power control is not available.')
        self._run(('chassis','power',POWER[action]))
    def page(self,key):
        if key not in READS:return [],['This page is not available through IPMI.']
        if not self.transport:self.probe()
        output=self._run(READS[key]);rows=[]
        for index,line in enumerate(output.splitlines()):
            if not line.strip() or re.search(r'not found|no (matching |sensor |SDR )?records|not supported',line,re.I):continue
            if '|' in line:
                fields=[p.strip() for p in line.split('|')];name=fields[0];value=' · '.join(fields[1:])
            elif ':' in line:name,value=(p.strip() for p in line.split(':',1))
            else:name,value='Record '+str(index+1),line.strip()
            # Status rows only; credentials/session material never leave adapter.
            if re.search(r'password|secret|token|session.?id|community|auth.*key',name,re.I):continue
            rows.append(FieldRow('IPMI',name,value,changeability='read-only',evidence='Reported by BMC via IPMI'))
        return rows,[]
    def close(self):self.password='';self.transport=None;self.privilege=None
