# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Portable, device-only legacy HTTPS transport; no global TLS changes."""
import http.cookiejar,ssl,urllib.request,urllib.error,urllib.parse,warnings

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def exchange(device,path,data=None):
    cookies=device.directory/'cookies-stdlib'
    jar=http.cookiejar.MozillaCookieJar(str(cookies))
    if cookies.exists():jar.load(ignore_discard=True)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname=False;context.verify_mode=ssl.CERT_NONE
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',DeprecationWarning)
        context.minimum_version=ssl.TLSVersion.TLSv1;context.maximum_version=ssl.TLSVersion.TLSv1
    context.set_ciphers('DEFAULT:@SECLEVEL=0')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=context),urllib.request.HTTPCookieProcessor(jar),NoRedirect())
    request=urllib.request.Request('https://'+device.host+path,data=data,headers={'Content-Type':'application/x-www-form-urlencoded'} if data is not None else {})
    try:
        try:response=opener.open(request,timeout=20)
        except urllib.error.HTTPError as error:response=error
        with response:
            status=response.code;location=response.headers.get('Location','');body=response.read(8_000_001)
        if len(body)>8_000_000:raise RuntimeError('Device response exceeded size limit')
        jar.save(ignore_discard=True);cookies.chmod(0o600)
    except (OSError,urllib.error.URLError) as error:raise RuntimeError('Device HTTPS connection failed') from None
    if status in (301,302,303):
        dest=urllib.parse.urlsplit(urllib.parse.urljoin('https://'+device.host,location))
        expected='/cgi-bin/webcgi/main' if data is not None else '/cgi-bin/webcgi/login'
        if path in ('/cgi-bin/webcgi/login','/cgi-bin/webcgi/unlock','/cgi-bin/webcgi/logout') and dest.hostname==device.host and dest.path==expected:return b''
        raise RuntimeError('Device session unavailable; redirect to '+dest.path)
    if status!=200:raise RuntimeError('Device HTTP '+str(status))
    return body
