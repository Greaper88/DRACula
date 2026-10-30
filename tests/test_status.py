import unittest
from unittest.mock import patch
from dracula.status import status_rows,StatusDevice,PAGES,fetch_page

class StatusTests(unittest.TestCase):
    def test_repeated_logs_keep_record_identity(self):
        data=b'<drac><object name="sel"><log><property name="Description"><value>first</value></property></log><log><property name="Description"><value>second</value></property></log></object></drac>'
        rows=status_rows(data)
        self.assertEqual([r[2] for r in rows],['first','second'])
        self.assertNotEqual(rows[0][0],rows[1][0])
    def test_units_and_sensor_location_are_kept(self):
        rows=status_rows(b'<drac><TemperatureProbeList><Probe><ProbeLocation>Ambient</ProbeLocation><ProbeReading unit="C">26</ProbeReading><ProbeStatus>2</ProbeStatus></Probe></TemperatureProbeList></drac>')
        self.assertTrue(any(r[2]=='26 C' and 'Ambient' in r[0] for r in rows))
        self.assertTrue(any(r[2]=='OK (code 2)' for r in rows))
    def test_secrets_and_privileges_do_not_escape(self):
        data=b'<drac><privilege><login>1</login></privilege><mysidIndex>private</mysidIndex><object name="nic"><property name="EncryptionKey"><value>secret1</value></property><property name="CommunityName"><value>secret2</value></property><property name="FirmwareVersion"><value>1.65</value></property></object></drac>'
        self.assertEqual(status_rows(data),[('nic','Firmware Version','1.65')])
    def test_expired_session_not_reported_as_data(self):
        with self.assertRaises(ValueError):status_rows(b'<drac><LOGIN><RC>0</RC></LOGIN></drac>')
    def test_partial_failures_are_explicit(self):
        class Broken:
            def request(self,path):raise OSError('unreachable')
        rows,errors=fetch_page(Broken(),PAGES[0]);self.assertEqual(rows,[]);self.assertIn('unreachable',errors[0])
    def test_mutation_post_rejected_on_status_device(self):
        from dracula.launcher import CACHE
        CACHE.mkdir(exist_ok=True)
        d=StatusDevice('192.168.1.253')
        try:
            with patch('subprocess.run') as run:
                with self.assertRaises(ValueError):d.request('/cgi-bin/webcgi/power',b'action=reset')
                with self.assertRaises(ValueError):d.request('/cgi-bin/webcgi/vkvm?state=3')
                run.assert_not_called()
        finally:d.close()
    def test_bridge_response_terminator_has_no_extra_fields(self):
        import io
        from contextlib import redirect_stdout
        from dracula.manager_bridge import emit
        output=io.StringIO()
        with redirect_stdout(output):emit('END')
        self.assertEqual(output.getvalue(),'END\n')
