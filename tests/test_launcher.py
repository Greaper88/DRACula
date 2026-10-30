import unittest
from unittest.mock import patch
from dracula.launcher import Device, xml_properties, parse_launch_descriptor

class LauncherTests(unittest.TestCase):
    def test_rejects_unapproved_requests_before_network(self):
        with patch('subprocess.run') as run:
            device=Device('192.168.1.253')
            for path in ('/cgi-bin/webcgi/power','/cgi-bin/webcgi/vkvm?state=1','https://evil.invalid/'):
                with self.assertRaises(ValueError):device.request(path)
            with self.assertRaises(ValueError):device.request('/cgi-bin/webcgi/vkvmconfig',b'Enabled=0')
            run.assert_not_called()
            device.close()
    def test_rejects_url_injection(self):
        for host in ('192.168.1.253/evil','user@192.168.1.253','127.0.0.1:443'):
            with self.assertRaises(ValueError):Device(host)
    def test_entity_documents_are_rejected(self):
        with self.assertRaises(ValueError):xml_properties(b'<!DOCTYPE drac><drac/>')
    def test_parses_token_without_printing_or_substituting_password(self):
        xml=b'<drac><object><property name="vKvmSessionId"><value>12345</value></property></object></drac>'
        self.assertEqual(xml_properties(xml)['vKvmSessionId'],'12345')

    def descriptor(self, host='192.168.1.253', main='com.avocent.drac5.kvm.Main'):
        args={'ip':host,'user':'a'*32,'passwd':'','kmport':'5900','vport':'5901','version':'1','apcp':'0','sslv3':'1'}
        return ('<jnlp xmlns="urn:legacy"><application-desc main-class="'+main+'">'+''.join('<argument>'+k+'='+v+'</argument>' for k,v in args.items())+'</application-desc></jnlp>').encode()
    def test_rejects_different_application_and_target(self):
        for data in (self.descriptor(main='evil.Main'),self.descriptor(host='192.168.1.254')):
            with self.assertRaises(ValueError):parse_launch_descriptor(data,'192.168.1.253')
    def test_namespaced_descriptor_is_validated(self):
        self.assertEqual(parse_launch_descriptor(self.descriptor(),'192.168.1.253')['kmport'],'5900')
