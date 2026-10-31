# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import subprocess,unittest
from unittest.mock import Mock,patch
from dracula.ipmi import IpmiAdapter,IpmiError,TRANSPORTS
from dracula.management import ManagementSession
from dracula.status import FieldRow

class IpmiTests(unittest.TestCase):
    def test_password_is_child_environment_only_and_no_retry_fallback_after_write(self):
        a=IpmiAdapter('192.0.2.1','root','private-test-password');a.transport=TRANSPORTS[0];a.privilege='ADMINISTRATOR'
        with patch('dracula.ipmi.shutil.which',return_value='/usr/bin/ipmitool'),patch('dracula.ipmi.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'Chassis Power is on\n',b'')) as run,patch.dict('os.environ',{'IPMITOOL_PASSWORD':'wrong'}):
            self.assertEqual(a.state(),'ON');args=run.call_args.args[0];options=run.call_args.kwargs
            self.assertNotIn(a.password,args);self.assertIn('-E',args);self.assertEqual(args[args.index('-R')+1],'1');self.assertEqual(options['env']['IPMI_PASSWORD'],a.password);self.assertNotIn('IPMITOOL_PASSWORD',options['env'])
            run.side_effect=subprocess.TimeoutExpired(args,12)
            with self.assertRaises(IpmiError):a.submit_power('reset')
            self.assertEqual(run.call_count,2);self.assertEqual(run.call_args.args[0][-3:],['chassis','power','reset'])
    def test_read_only_probe_prefers_new_transport_and_can_authenticate_user(self):
        a=IpmiAdapter('192.0.2.1','reader','pw')
        def probe(command,transport=None,privilege=None):
            if (privilege or a.privilege)=='USER' and (transport or a.transport)==TRANSPORTS[0]:return 'Chassis Power is off'
            raise IpmiError('not available')
        a._run=Mock(side_effect=probe);self.assertEqual(a.probe(),'OFF');self.assertFalse(a.power_status()[1]);self.assertTrue(all(c.args[0]==('chassis','power','status') for c in a._run.call_args_list))
    def test_no_raw_error_or_secrets_exposed(self):
        a=IpmiAdapter('192.0.2.1','root','private-test-password');a.transport=TRANSPORTS[0];a.privilege='ADMINISTRATOR'
        with patch('dracula.ipmi.shutil.which',return_value='ipmitool'),patch('dracula.ipmi.subprocess.run',return_value=subprocess.CompletedProcess([],1,b'',b'private-test-password token=secret')):
            with self.assertRaisesRegex(IpmiError,'IPMI request failed'):a.state()
        a.close();self.assertEqual(a.password,'')
class ManagementTests(unittest.TestCase):
    def test_http_login_failure_falls_back_and_hides_vendor_features(self):
        d=Mock();d.host='192.0.2.1';d.login.side_effect=RuntimeError('HTTP 500')
        with patch('dracula.management.IpmiAdapter') as cls:
            cls.return_value.page.side_effect=lambda key:([FieldRow('IPMI','Device','BMC')],[]) if key in ('overview','rac') else ([],[])
            session=ManagementSession(d,'root','pw');caps=session.capabilities()
            self.assertEqual(set(caps['pages']),{'overview','rac','power'});self.assertFalse(caps['kvm']);self.assertFalse(caps['settings']);self.assertNotIn('services',caps['pages']);cls.return_value.probe.assert_called_once();session.close();cls.return_value.close.assert_called_once()
    def test_existing_http_connection_falls_back_on_page_failure(self):
        d=Mock();d.host='192.0.2.1'
        with patch('dracula.management.IpmiAdapter') as cls,patch('dracula.management.fetch_page',return_value=([],['HTTP unavailable'])):
            cls.return_value.page.return_value=([FieldRow('IPMI','Device','BMC')],[])
            session=ManagementSession(d,'root','pw');rows,errors=session.page('overview');self.assertEqual(rows[0].group,'IPMI');self.assertFalse(session.http_ready);self.assertIn('IPMI',errors[0]);session.close()
