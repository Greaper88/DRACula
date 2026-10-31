# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import io,os,ssl,tempfile,unittest,urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from dracula.stdlib_http import exchange,NoRedirect

class Response(io.BytesIO):
    def __init__(self,body=b'<drac/>',status=200,location=''):
        super().__init__(body);self.code=status;self.headers={'Location':location}

class PortableHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.device=SimpleNamespace(host='192.0.2.10',directory=Path(self.temp.name))
    def tearDown(self):self.temp.cleanup()
    def test_legacy_context_is_private_proxy_free_and_cookie_file_is_private(self):
        before=ssl.create_default_context().minimum_version
        opener=Mock();opener.open.return_value=Response()
        with patch('urllib.request.build_opener',return_value=opener) as build:
            self.assertEqual(exchange(self.device,'/cgi-bin/webcgi/main'),b'<drac/>')
            handlers=build.call_args.args
            https=next(h for h in handlers if hasattr(h,'_context'));self.assertEqual(https._context.minimum_version,ssl.TLSVersion.TLSv1);self.assertEqual(https._context.maximum_version,ssl.TLSVersion.TLSv1);self.assertFalse(https._context.check_hostname)
            proxy=next(h for h in handlers if hasattr(h,'proxies'));self.assertEqual(proxy.proxies,{})
        self.assertEqual(ssl.create_default_context().minimum_version,before)
        self.assertEqual((self.device.directory/'cookies-stdlib').stat().st_mode&0o777,0o600)
    def test_post_body_is_not_in_url_and_redirects_are_never_followed(self):
        opener=Mock();opener.open.return_value=Response(status=302,location='/cgi-bin/webcgi/main')
        with patch('urllib.request.build_opener',return_value=opener):
            self.assertEqual(exchange(self.device,'/cgi-bin/webcgi/login',b'user=operator&password=synthetic'),b'')
        request=opener.open.call_args.args[0];self.assertEqual(request.data,b'user=operator&password=synthetic');self.assertNotIn('synthetic',request.full_url)
        self.assertIsNone(NoRedirect().redirect_request(None,None,None,None,None,None))
        for location in ('https://other.invalid/cgi-bin/webcgi/main','/cgi/unlock.html'):
            opener.open.return_value=Response(status=302,location=location)
            with patch('urllib.request.build_opener',return_value=opener),self.assertRaisesRegex(RuntimeError,'session unavailable'):exchange(self.device,'/cgi-bin/webcgi/login',b'password=synthetic')
    def test_error_and_oversized_responses_do_not_expose_response_or_retry(self):
        opener=Mock()
        for response,message in ((Response(b'private details',500),'Device HTTP 500'),(Response(b'x'*8_000_001),'size limit')):
            opener.open.reset_mock();opener.open.return_value=response
            with patch('urllib.request.build_opener',return_value=opener),self.assertRaisesRegex(RuntimeError,message):exchange(self.device,'/cgi-bin/webcgi/main')
            opener.open.assert_called_once()
    def test_public_request_validation_still_runs_before_portable_transport(self):
        from dracula.launcher import Device,CACHE
        CACHE.mkdir(exist_ok=True)
        with patch.dict(os.environ,{'DRACULA_HTTP_TRANSPORT':'stdlib'}),patch('dracula.stdlib_http.exchange') as transport:
            device=Device('192.0.2.10')
            try:
                with self.assertRaises(ValueError):device.request('/cgi-bin/webcgi/power',b'action=reset')
                transport.assert_not_called()
            finally:device.close()
