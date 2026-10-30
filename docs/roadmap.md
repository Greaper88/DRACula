# Current milestone

The Linux view-only launcher now authenticates to .253 and opens the vendor
video window using private 32-bit Java and a private SSLv3 compatibility profile.
The current remote result is **No Signal**; verify visible Linux video before
claiming complete rendering validation. Do not send a wake key without approval.

Remaining work:

1. Confirm .253 video output and verify the expected login prompt.
2. Finish portable runtime/native dependency packaging and Windows/macOS profiles.
3. Add the modern Java manager that starts the isolated legacy worker and opens
   a console dialog. Host Java may be used if compatible, with a bundled fallback.
4. Add the server-side private display and authenticated browser stream.
5. Extend status reads with IPMI where already enabled.
6. Test any mutation support only after explicit approval, eventually on .252.
