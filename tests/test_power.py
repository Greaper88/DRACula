# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import subprocess,sys,unittest
from unittest.mock import Mock,patch
from urllib.parse import parse_qs
from dracula.power import PowerController,Drac5Power
from dracula.configuration import ConfigError

class Adapter:
    host='192.0.2.1';name='IPMI'
    def __init__(self,state='ON',allowed=True):self.state=state;self.allowed=allowed;self.sent=[];self.fail=False
    def power_status(self):return self.state,self.allowed
    def submit_power(self,action):
        self.sent.append(action)
        if self.fail:raise RuntimeError('connection lost')
        if action in ('on','off'):self.state=action.upper()
class PowerTests(unittest.TestCase):
    def test_http_power_reaches_binary_transport_with_encoded_form(self):
        from dracula.status import StatusDevice
        device=StatusDevice('192.0.2.1');real_run=subprocess.run
        # Run a local stdin consumer instead of curl. This exercises the real
        # Device._exchange input contract without contacting any hardware.
        def local_transport(command,**options):
            self.assertEqual(command[-1],'https://192.0.2.1/cgi-bin/webcgi/power')
            self.assertIsInstance(options['input'],bytes)
            self.assertEqual(parse_qs(options['input'].decode())['action'],['1'])
            (device.directory/'body').write_bytes(b'<drac/>')
            return real_run([sys.executable,'-c',"import sys; assert sys.stdin.buffer.read().endswith(b'action=1'); sys.stdout.write('200')"],**options)
        try:
            with patch('dracula.launcher.subprocess.run',side_effect=local_transport) as run:
                Drac5Power(device).submit_power('on')
                self.assertEqual(run.call_count,1)
        finally:device.close()
    def setup_power(self,state='ON'):
        ipmi=Adapter(state);http=Adapter(state);http.name='DRAC HTTP'
        return PowerController(http.host,http,ipmi),http,ipmi
    def review(self,p,action):return p.review(action,p.status()['revision'],'owner')
    def test_state_rules_permission_and_disagreement(self):
        for state in ('ON','OFF','UNKNOWN'):
            p,http,ipmi=self.setup_power(state);model=p.status()
            self.assertEqual({a['id'] for a in model['actions'] if a['enabled']},{'off','reset','cycle','soft'} if state=='ON' else {'on'} if state=='OFF' else set())
            self.assertEqual(http.sent+ipmi.sent,[])
        http.allowed=ipmi.allowed=False;self.assertFalse(any(a['enabled'] for a in p.status()['actions']))
        ipmi.state='OFF';self.assertFalse(any(a['enabled'] for a in p.status()['actions']))
    def test_review_cancel_and_false_confirmation_never_submit(self):
        p,h,i=self.setup_power();r=self.review(p,'off')
        for confirmed in (False,1,'true',None):
            with self.assertRaises(ConfigError):p.confirm(r['token'],'owner',confirmed)
        with self.assertRaises(ConfigError):p.confirm(r['token'],'another',True)
        p.cancel(r['token'],'owner')
        with self.assertRaises(ConfigError):p.confirm(r['token'],'owner',True)
        self.assertEqual(h.sent+i.sent,[])
    def test_only_reviewed_action_runs_once_and_verifies_on_off(self):
        p,h,i=self.setup_power();r=self.review(p,'off');result=p.confirm(r['token'],'owner',True)
        self.assertEqual(result['status'],'verified');self.assertEqual(h.sent,['off']);self.assertEqual(i.sent,[])
        with self.assertRaises(ConfigError):p.confirm(r['token'],'owner',True)
    def test_graceful_uses_ipmi_and_reset_is_not_claimed_verified(self):
        p,h,i=self.setup_power();r=self.review(p,'soft');self.assertIn('ACPI',r['warning']);self.assertEqual(p.confirm(r['token'],'owner',True)['status'],'submitted');self.assertEqual(i.sent,['soft']);self.assertEqual(h.sent,[])
        r=self.review(p,'reset');self.assertEqual(p.confirm(r['token'],'owner',True)['status'],'submitted')
    def test_lost_response_never_falls_back_or_retries(self):
        p,h,i=self.setup_power();h.fail=True;r=self.review(p,'cycle')
        self.assertEqual(p.confirm(r['token'],'owner',True)['status'],'unknown');self.assertEqual(h.sent,['cycle']);self.assertEqual(i.sent,[])
        with self.assertRaises(ConfigError):p.confirm(r['token'],'owner',True)
    def test_stale_state_permissions_expiry_target_and_transport_rejected(self):
        for mutation in ('state','permissions','host','transport','expiry'):
            p,h,i=self.setup_power();r=self.review(p,'reset')
            if mutation=='state':h.state=i.state='OFF'
            if mutation=='permissions':h.allowed=False
            if mutation=='host':p.host='192.0.2.2'
            if mutation=='transport':p.http=None
            if mutation=='expiry':
                plan=list(p.plans[r['token']]);plan[0]=0;p.plans[r['token']]=tuple(plan)
            with self.assertRaises(ConfigError,msg=mutation):p.confirm(r['token'],'owner',True)
            self.assertEqual(h.sent+i.sent,[])
    def test_http_failure_selects_ipmi_before_review(self):
        p,h,i=self.setup_power();h.power_status=Mock(side_effect=RuntimeError('HTTP down'));r=self.review(p,'reset');self.assertIn('IPMI',r['changes'][0]['after']);p.confirm(r['token'],'owner',True);self.assertEqual(i.sent,['reset']);self.assertEqual(h.sent,[])
    def test_exact_drac_form_mapping_and_unknown_status_fails_closed(self):
        d=Mock();d.host='192.0.2.1';adapter=Drac5Power(d)
        d.request.return_value=b'<drac><privilege servercontrol="1"/><PowerStatus>ON</PowerStatus></drac>'
        self.assertEqual(adapter.power_status(),('ON',True))
        for action,code in [('on','1'),('off','0'),('cycle','3'),('reset','2')]:
            adapter.submit_power(action);path,payload=d._exchange.call_args.args;self.assertEqual(path,'/cgi-bin/webcgi/power');self.assertEqual(parse_qs(payload.decode('ascii'))['action'],[code])
        with self.assertRaises(ConfigError):adapter.submit_power('soft')
        d.request.return_value=b'<drac><privilege servercontrol="1"/><PowerStatus>?</PowerStatus></drac>'
        self.assertEqual(adapter.power_status()[0],'UNKNOWN')
