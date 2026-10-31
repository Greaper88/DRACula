# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import copy,unittest
from unittest.mock import patch
from urllib.parse import parse_qs
from dracula.configuration import ConfigEditor,ConfigError,form_payload,Record

class Device:
    def __init__(self,host='192.0.2.252'):
        self.host=host;self.values={'Enabled':'1','BaudRate':'9600','ChannelPrivLimit':'4'};self.writes=[];self.extra=False;self.drop=False;self.reads=0
    def request(self,path):
        self.reads+=1
        props=''.join(f'<property name="{k}"><value>{v}</value></property>' for k,v in self.values.items())
        return ('<drac><privilege cfg="1" cfguser="1"/><object name="sol">'+props+'</object></drac>').encode()
    def _exchange(self,path,data):
        self.writes.append((path,data));params=parse_qs(data.decode(),keep_blank_values=True)
        self.values.update({k:params[k][0] for k in ('BaudRate','ChannelPrivLimit') if k in params});self.values['Enabled']='1' if 'Enabled' in params else '0'
        if self.extra:self.values['ChannelPrivLimit']='2'
        if self.drop:raise RuntimeError('synthetic connection lost after submission')
        return b'<drac/>'

def proposal(editor,value='19200'):
    rows=editor.read('sol');row=next(r for r in rows if r.field=='Baud Rate')
    return row,{row.key:value},row.edit['revision']

def review(editor,value='19200',owner='owner'):
    row,changes,revision=proposal(editor,value)
    return editor.review('sol',changes,owner,revision)

class ConfigurationTests(unittest.TestCase):
    def test_review_is_read_only_and_confirmation_applies_exact_changes_once(self):
        device=Device();editor=ConfigEditor(device);plan=review(editor)
        self.assertFalse(device.writes);self.assertEqual(plan['target'],'192.0.2.252')
        self.assertEqual(plan['changes'][0]['before'],'9600 bps');self.assertEqual(plan['changes'][0]['after'],'19200 bps')
        result=editor.confirm(plan['token'],'owner',True)
        self.assertEqual(result['status'],'verified');self.assertEqual(len(device.writes),1)
        self.assertEqual(device.writes[0][0],'/cgi-bin/webcgi/sol');self.assertEqual(device.values['ChannelPrivLimit'],'4')
        with self.assertRaises(ConfigError):editor.confirm(plan['token'],'owner',True)
        self.assertEqual(len(device.writes),1)
    def test_each_selected_target_requires_its_own_exact_confirmation(self):
        for address in ('192.0.2.252','192.0.2.253','192.0.2.254'):
            device=Device(address);editor=ConfigEditor(device);plan=review(editor)
            self.assertEqual(plan['target'],address);self.assertFalse(device.writes)
            with self.assertRaises(ConfigError):editor.confirm(plan['token'],'owner',False)
            self.assertFalse(device.writes)
            self.assertEqual(editor.confirm(plan['token'],'owner',True)['status'],'verified')
            self.assertEqual(len(device.writes),1)
    def test_invalid_target_is_not_editable(self):
        device=Device('not-an-ip');editor=ConfigEditor(device)
        self.assertTrue(all(r.edit is None for r in editor.read('sol')))
        with self.assertRaises(ConfigError):editor.confirm('fake','owner',True)
        self.assertFalse(device.writes)
    def test_confirmation_must_match_owner_and_literal_true(self):
        device=Device();editor=ConfigEditor(device);plan=review(editor)
        for owner,confirmed in [('other',True),('owner',False),('owner','true'),('owner',1)]:
            with self.assertRaises(ConfigError):editor.confirm(plan['token'],owner,confirmed)
        self.assertFalse(device.writes)
    def test_expiry_cancel_disconnect_and_host_change_invalidate_confirmation(self):
        for action in ('expire','cancel','close','host'):
            device=Device();editor=ConfigEditor(device);plan=review(editor)
            if action=='expire':editor.plans[plan['token']]['expires']=0
            elif action=='cancel':editor.cancel(plan['token'],'owner')
            elif action=='close':editor.close()
            else:device.host='192.0.2.254'
            with self.assertRaises(ConfigError):editor.confirm(plan['token'],'owner',True)
            self.assertFalse(device.writes)
    def test_stale_loaded_values_and_stale_review_send_nothing(self):
        device=Device();editor=ConfigEditor(device);row,changes,revision=proposal(editor)
        device.values['ChannelPrivLimit']='2'
        with self.assertRaises(ConfigError):editor.review('sol',changes,'owner',revision)
        plan=review(editor);device.values['ChannelPrivLimit']='3'
        with self.assertRaises(ConfigError):editor.confirm(plan['token'],'owner',True)
        self.assertFalse(device.writes)
    def test_another_reader_cannot_replace_a_clients_original_snapshot(self):
        device=Device();editor=ConfigEditor(device);row,changes,revision=proposal(editor)
        device.values['ChannelPrivLimit']='2';editor.read('sol')
        with self.assertRaises(ConfigError):editor.review('sol',changes,'owner',revision)
    def test_unexpected_side_effect_stops_without_success_or_retry(self):
        device=Device();editor=ConfigEditor(device);plan=review(editor);device.extra=True
        self.assertEqual(editor.confirm(plan['token'],'owner',True)['status'],'unknown')
        self.assertEqual(len(device.writes),1)
        with self.assertRaises(ConfigError):editor.confirm(plan['token'],'owner',True)
    def test_lost_response_is_verified_by_readback_not_retried(self):
        device=Device();editor=ConfigEditor(device);plan=review(editor);device.drop=True
        self.assertEqual(editor.confirm(plan['token'],'owner',True)['status'],'verified');self.assertEqual(len(device.writes),1)
    def test_invalid_values_unknown_fields_and_wrong_revision_are_rejected(self):
        device=Device();editor=ConfigEditor(device)
        for value in ('12345','19200\nHost:bad'):
            with self.assertRaises(ConfigError):review(editor,value)
        row,changes,revision=proposal(editor)
        with self.assertRaises(ConfigError):editor.review('sol',{'unknown':'1'},'owner',revision)
        with self.assertRaises(ConfigError):editor.review('sol',changes,'owner','wrong')
        self.assertFalse(device.writes)
    def test_checkbox_off_is_omitted_and_all_other_settings_are_preserved(self):
        device=Device();editor=ConfigEditor(device);row=next(r for r in editor.read('sol') if r.field=='Enabled')
        plan=editor.review('sol',{row.key:'0'},'owner',row.edit['revision']);editor.confirm(plan['token'],'owner',True)
        self.assertNotIn('Enabled',parse_qs(device.writes[0][1].decode(),keep_blank_values=True));self.assertEqual(device.values['BaudRate'],'9600')
    def test_incomplete_forms_and_unavailable_secrets_are_never_submitted(self):
        record=Record('services','services','','',{'SshEnabled':'1'})
        with self.assertRaises(ConfigError):form_payload(record,{'SshEnabled':'0'})
    def test_permission_loss_after_review_prevents_any_post(self):
        device=Device();editor=ConfigEditor(device);plan=review(editor);original=device.request
        device.request=lambda path:original(path).replace(b'cfg="1"',b'cfg="0"')
        with self.assertRaises(ConfigError):editor.confirm(plan['token'],'owner',True)
        self.assertFalse(device.writes)

    def test_repeated_user_rows_bind_to_the_real_user_id_and_preserve_privileges(self):
        class Users(Device):
            def request(self,path):
                self.reads+=1;records=[]
                for index in (1,2,3):
                    fields={'UserID':str(index),'Enabled':'1','UserName':'user'+str(index),'RacPrivilege':'511','LanPrivilege':'4','SerialPrivilege':'4','SOLEnabled':'1','IsPasswordSet':'1'}
                    records.append('<object name="user"><index>'+str(index)+'</index>'+''.join(f'<property name="{k}"><value>{v}</value></property>' for k,v in fields.items())+'<login>1</login><cfg>1</cfg></object>')
                return ('<drac><privilege cfg="1" cfguser="1"/>'+''.join(records)+'</drac>').encode()
        device=Users();editor=ConfigEditor(device);rows=editor.read('users')
        edits=[r for r in rows if r.field=='Serial over LAN enabled' and r.edit]
        self.assertEqual(len(edits),2);self.assertNotEqual(edits[0].key,edits[1].key)
        row=edits[1];plan=editor.review('users',{row.key:'0'},'owner',row.edit['revision'])
        record,proposed,payload,_=editor.plans[plan['token']]['operations'][0]
        params=parse_qs(payload.decode(),keep_blank_values=True)
        self.assertEqual(params['UserID'],['3']);self.assertEqual(params['index'],['3']);self.assertEqual(params['RacPrivilege'],['511'])
        self.assertNotIn('SOLEnabled',params);self.assertNotIn('ChangePassword',params);self.assertFalse(device.writes)
        editor.confirm(plan['token'],'owner',True);self.assertEqual(device.writes[0][0],'/cgi-bin/webcgi/user?index=3')
    def test_repeated_alert_records_have_exact_identity_and_one_power_action(self):
        class Filters(Device):
            def request(self,path):
                flags='<evtFltrActionPwrCycl>false</evtFltrActionPwrCycl><evtFltrActionReset>false</evtFltrActionReset><evtFltrActionPwrOff>false</evtFltrActionPwrOff><evtFltrActionAlert>true</evtFltrActionAlert><evtFltrActionPwrReduction>false</evtFltrActionPwrReduction>'
                return ('<drac><privilege cfg="1"/><eventFilterListarray><PEFAlertingEnable>1</PEFAlertingEnable>'+''.join('<eventFilterList><filterNumber>'+str(i)+'</filterNumber><filterKey>1048835</filterKey>'+flags+'</eventFilterList>' for i in (1,2))+'</eventFilterListarray></drac>').encode()
        device=Filters();editor=ConfigEditor(device);rows=editor.read('alerts')
        off=[r for r in rows if r.field=='Power off on event'][1];reset=[r for r in rows if r.field=='Reset on event'][1]
        with self.assertRaises(ConfigError):editor.review('alerts',{off.key:'1',reset.key:'1'},'owner',off.edit['revision'])
        plan=editor.review('alerts',{off.key:'1'},'owner',off.edit['revision']);record,_,payload,_=editor.plans[plan['token']]['operations'][0]
        self.assertEqual(parse_qs(payload.decode())['PefIndex'],['2']);self.assertEqual(parse_qs(payload.decode())['ShutdownMode'],['1']);self.assertFalse(device.writes)
    def test_read_only_fields_and_secret_fields_cannot_be_injected_into_changes(self):
        device=Device();editor=ConfigEditor(device);row,changes,revision=proposal(editor)
        for key in ('Password','CommunityName','ActiveSessions','/cgi-bin/webcgi/power'):
            with self.assertRaises(ConfigError):editor.review('sol',{key:'1'},'owner',revision)
        self.assertFalse(device.writes)

    def test_destination_submission_pins_the_record_and_never_sends_a_test_alert(self):
        class Traps(Device):
            def request(self,path):
                return b'<drac><privilege cfg="1"/><EMPLANAltDestListObj><LANAlertDestListarray><LANAlertDestList><destSelector>2</destSelector><entryEnable>0</entryEnable><AlertingIPAddr>192.0.2.8</AlertingIPAddr></LANAlertDestList></LANAlertDestListarray></EMPLANAltDestListObj></drac>'
        device=Traps();editor=ConfigEditor(device);row=next(r for r in editor.read('alert_destinations') if r.field=='Destination enabled')
        plan=editor.review('alert_destinations',{row.key:'1'},'owner',row.edit['revision']);self.assertFalse(device.writes)
        editor.confirm(plan['token'],'owner',True)
        self.assertEqual(device.writes[0][0],'/cgi-bin/webcgi/pefdest?index=2&test=0')
        self.assertEqual(parse_qs(device.writes[0][1].decode())['PefDestIndex'],['2'])

    def test_loaded_snapshot_cannot_move_to_a_different_selected_target(self):
        device=Device();editor=ConfigEditor(device);row,changes,revision=proposal(editor)
        device.host='192.0.2.254'
        with self.assertRaises(ConfigError):editor.review('sol',changes,'owner',revision)
        self.assertFalse(device.writes)
