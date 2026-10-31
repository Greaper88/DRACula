# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch
from dracula.launcher import Device, xml_properties, parse_launch_descriptor

class LauncherTests(unittest.TestCase):
    def test_rejects_unapproved_requests_before_network(self):
        with patch('subprocess.run') as run:
            device=Device('192.0.2.253')
            for path in ('/cgi-bin/webcgi/power','/cgi-bin/webcgi/vkvm?state=1','https://evil.invalid/'):
                with self.assertRaises(ValueError):device.request(path)
            with self.assertRaises(ValueError):device.request('/cgi-bin/webcgi/vkvmconfig',b'Enabled=0')
            run.assert_not_called()
            device.close()
    def test_rejects_url_injection(self):
        for host in ('192.0.2.253/evil','user@192.0.2.253','127.0.0.1:443'):
            with self.assertRaises(ValueError):Device(host)
    def test_entity_documents_are_rejected(self):
        with self.assertRaises(ValueError):xml_properties(b'<!DOCTYPE drac><drac/>')
    def test_parses_token_without_printing_or_substituting_password(self):
        xml=b'<drac><object><property name="vKvmSessionId"><value>12345</value></property></object></drac>'
        self.assertEqual(xml_properties(xml)['vKvmSessionId'],'12345')

    def descriptor(self, host='192.0.2.253', main='com.avocent.drac5.kvm.Main'):
        args={'ip':host,'user':'a'*32,'passwd':'','kmport':'5900','vport':'5901','version':'1','apcp':'0','sslv3':'1'}
        return ('<jnlp xmlns="urn:legacy"><application-desc main-class="'+main+'">'+''.join('<argument>'+k+'='+v+'</argument>' for k,v in args.items())+'</application-desc></jnlp>').encode()
    def test_rejects_different_application_and_target(self):
        for data in (self.descriptor(main='evil.Main'),self.descriptor(host='192.0.2.254')):
            with self.assertRaises(ValueError):parse_launch_descriptor(data,'192.0.2.253')
    def test_namespaced_descriptor_is_validated(self):
        self.assertEqual(parse_launch_descriptor(self.descriptor(),'192.0.2.253')['kmport'],'5900')

class OwnedLogoutTests(unittest.TestCase):
    def setUp(self):
        from dracula.launcher import CACHE
        CACHE.mkdir(exist_ok=True)
        self.device=Device('192.0.2.252');self.device._auth=('root','synthetic-password')
    def tearDown(self):self.device.close()
    def document(self,index='42',owner='root',record='42'):
        return ('<drac><mysidIndex>'+index+'</mysidIndex><session><index>'+record+'</index><user>'+owner+'</user></session></drac>').encode()
    def test_logout_closes_only_authenticated_own_index_and_confirms_token_invalid(self):
        expired=RuntimeError('Device session unavailable; redirect to /cgi-bin/webcgi/timeout')
        with patch.object(self.device,'_exchange',side_effect=[self.document(),b'<drac/>',expired]) as exchange:
            self.device.logout()
            self.assertEqual(exchange.call_args_list[1].args[0],'/cgi-bin/webcgi/ssninfo?index=42&cat=C01&tab=T10&id=P21')
            self.assertEqual(exchange.call_args_list[-1].args[0],'/cgi-bin/webcgi/main')
            self.assertIsNone(self.device._auth)
    def test_locked_token_is_unlocked_without_allocating_another_login(self):
        locked=RuntimeError('Device session unavailable; redirect to /cgi/unlock.html')
        expired=RuntimeError('Device session unavailable; redirect to /cgi-bin/webcgi/timeout')
        with patch.object(self.device,'_exchange',side_effect=[locked,b'',self.document(),b'<drac/>',expired]) as exchange:
            self.device.logout()
            self.assertEqual(exchange.call_args_list[1].args,('/cgi-bin/webcgi/unlock',b'password=synthetic-password'))
            self.assertFalse(any(c.args[0]=='/cgi-bin/webcgi/login' for c in exchange.call_args_list))
    def test_bad_or_other_user_session_identity_never_reaches_close_request(self):
        for data in (self.document(index='42&amp;index=7'),self.document(record='43'),self.document(owner='another-user'),b'<!DOCTYPE drac><drac/>'):
            with self.subTest(data=data),patch.object(self.device,'_exchange',return_value=data) as exchange:
                with self.assertRaises(ValueError):self.device.logout()
                exchange.assert_called_once_with('/cgi-bin/webcgi/ssninfo')
    def test_a_still_valid_token_is_not_reported_as_successful_logout(self):
        with patch.object(self.device,'_exchange',side_effect=[self.document(),b'<drac/>',b'<drac><privilege/></drac>']):
            with self.assertRaises(RuntimeError):self.device.logout()
    def test_public_transport_still_rejects_arbitrary_session_termination_and_unlock(self):
        with patch('subprocess.run') as run:
            with self.assertRaises(ValueError):self.device.request('/cgi-bin/webcgi/ssninfo?index=7&cat=C01&tab=T10&id=P21')
            with self.assertRaises(ValueError):self.device.request('/cgi-bin/webcgi/unlock',b'password=synthetic')
            run.assert_not_called()
    def test_already_invalidated_token_needs_no_new_login_or_termination(self):
        expired=RuntimeError('Device session unavailable; redirect to /cgi-bin/webcgi/timeout')
        with patch.object(self.device,'_exchange',side_effect=expired) as exchange:
            self.device.logout()
            exchange.assert_called_once_with('/cgi-bin/webcgi/ssninfo')
            self.assertIsNone(self.device._auth)
