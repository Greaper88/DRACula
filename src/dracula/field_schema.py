# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Reviewed DRAC 5 form semantics; metadata never grants write permission.

Derived from the controller's static forms, not from whether a current value is 0/1.
See docs/drac5-fields.md for evidence and limits. Device XSL is never executed.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class FieldSpec:
    control: str = 'text'
    changeability: str = 'configurable'
    evidence: str = 'Mapped control in the original DRAC form; changes remain locked.'
    choices: tuple = ()

SPECS = {}
def fields(endpoint, names, control='text', **kwargs):
    for name in names.split():SPECS[endpoint,name]=FieldSpec(control=control,**kwargs)

def choices(endpoint,name,values):
    SPECS[endpoint,name]=FieldSpec(control='choice',choices=tuple(values.items()))

fields('nic','Enabled IpAddrSource DhcpEnabled DnsEnabled DomainNameDhcp AutoNegotiation IpmiLanEnabled VLanEnabled','switch')
fields('nic','IpAddress Gateway SubnetMask Server1 Server2 RacName DomainName VLanId VLanPriority')
choices('nic','Mode',{'0':'Shared NIC 1','1':'Shared NIC 1 / NIC 2','2':'Dedicated'})
choices('nic','Speed',{'0':'10 Mbps','1':'100 Mbps'})
choices('nic','Duplex',{'0':'Half duplex','1':'Full duplex'})
choices('nic','MinPrivilege',{'2':'User','3':'Operator','4':'Administrator'})
fields('services','WebServerEnabled SshEnabled TelnetEnabled RacadmEnabled SnmpEnabled AsrEnabled','switch')
fields('services','LocalCfgUsingRomDisabled LocalCfgUsingRACADMDisabled','truth')
fields('services','WebServerTimeout HttpPortNumber HttpsPortNumber SshTimeout SshPortNumber TelnetTimeout TelnetPortNumber')
fields('serial','SerialEnabled RedirectEnabled','switch')
fields('serial','SerialTimeout EscapeKey HistBufSize LoginCommand SerialBaudRate BaudRate')
choices('serial','ConnectionMode',{'0':'Terminal','1':'Basic'})
choices('serial','FlowControl',{'0':'None','1':'RTS/CTS'})
choices('serial','ChannelPrivLimit',{'2':'User','3':'Operator','4':'Administrator'})
fields('sol','Enabled','switch');fields('sol','BaudRate')
choices('sol','ChannelPrivLimit',{'2':'User','3':'Operator','4':'Administrator'})
fields('ad','Enabled SSOEnabled FilterEnable','switch')
fields('ad','RootDomain Timeout DomainController GlobalCatalog RacName RacDomain')
choices('ad','Type',{'1':'Extended schema','2':'Standard schema'})
fields('vkvmconfig','Enabled EncryptionEnabled LocalServerVideo','switch')
fields('vkvmconfig','KMPortNumber VideoPortNumber')
choices('vkvmconfig','PluginType',{'0':'Native','1':'Java'})
choices('vkvmconfig','AuthorizeMultipleSessions',{'0':'No access','1':'Read-only access','2':'Full access'})
fields('vmconfig','KeyEnabled','switch');fields('vmconfig','PortNumber SslPortNumber')
choices('vmconfig','PluginType',{'0':'Native','1':'Java'})
choices('vmconfig','Attached',{'0':'Detached','1':'Attached','2':'Auto attach'})
# Despite its name, this is a boot-device selector, not a boolean.
choices('vmconfig','BootOnceEnabled',{'0':'Disabled','1':'Virtual media / vFlash','2':'Virtual floppy','3':'Virtual CD','4':'PXE','5':'Hard drive','6':'Utility partition','7':'Default CD','8':'BIOS setup','9':'Primary removable media'})
fields('listpef','PEFAlertingEnable','switch')
fields('lpefemail','SMTPAddress')
fields('users','Enabled SOLEnabled','switch');fields('users','UserName')
for endpoint in ('users','ad'):
    fields(endpoint,'login cfg cfguser clearlog servercontrol console vmedia testalert debug','switch')
    for name in ('LanPrivilege','SerialPrivilege') if endpoint=='users' else ():
        choices(endpoint,name,{'2':'User','3':'Operator','4':'Administrator','15':'No access'})
fields('ad','RoleGroupName RoleGroupDomain')
fields('listpef','evtFltrActionAlert evtFltrActionPwrCycl evtFltrActionReset evtFltrActionPwrOff evtFltrActionPwrReduction','switch')
fields('lpefdest','entryEnable','switch');fields('lpefdest','AlertingIPAddr')
fields('lpefemail','entryEnable','switch');fields('lpefemail','emailAddr emailDesc')
# These controller capability/count fields have no matching editable input.
for endpoint in ('nic','services','serial','sol','users','ad','vkvmconfig','vmconfig'):
    fields(endpoint,'ActiveSessions MaxSessions WebServerActiveSessions WebServerMaxSessions SshActiveSessions SshMaxSessions TelnetActiveSessions TelnetMaxSessions RacadmActiveSessions RacadmMaxSessions SerialMaxSessions CurrentActiveSessions NumberOfNics MacAddress',changeability='read-only',evidence='Controller status or capability; no corresponding form input.')
    fields(endpoint,'SCLEnabled BootOnceSupport','truth',changeability='read-only',evidence='Controller capability flag; no corresponding form input.')

# Explicitly reviewed status flags without an editable control on these pages.
SPECS['serial','AuthDisabled']=FieldSpec(control='truth',changeability='unknown',evidence='Reported authentication-disabled flag; editability on this page is unverified.')
SPECS['sysinfo','Enabled']=FieldSpec(control='switch',changeability='read-only',evidence='Reported BMC enable state in system information; no editable control on this page.')

READ_ONLY_ENDPOINTS = frozenset(('sysinfo','power','sel','postlog','raclog','listbat','listfan','intrlist','hpinfo','listpower','poweraverage','pwrsup','listtemp','listvolt','rac','get_certview','ssninfo'))

def field_spec(endpoint,name):
    spec=SPECS.get((endpoint,name))
    if spec:return spec
    if endpoint in READ_ONLY_ENDPOINTS:return FieldSpec(changeability='read-only',evidence='Reported status; management actions are separate from these fields.')
    return FieldSpec(changeability='unknown',evidence='No reviewed matching form control. Editability has not been established.')
