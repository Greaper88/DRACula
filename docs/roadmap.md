# Current milestone

The Linux view-only launcher now authenticates to .253 and opens the vendor
video window using private 32-bit Java and a private SSLv3 compatibility profile.
The Linux login prompt on .253 is now visually verified. Initial No Signal was
resolved by the owner-authorized NumLock wake cycle. The normal launcher does not
send wake input; future wake actions still require authorization.

Remaining work:

1. Improve console status and window sizing, then finish release packaging.
2. Finish portable runtime/native dependency packaging and Windows/macOS profiles.
3. Add the modern Java manager that starts the isolated legacy worker and opens
   a console dialog. Host Java may be used if compatible, with a bundled fallback.
4. Add the server-side private display and authenticated browser stream.
5. Extend status reads with IPMI where already enabled.
6. Test any mutation support only after explicit approval, eventually on .252.
