# Architecture

Desktop UI -> local application service -> shared core -> DRAC
Browser UI -> modern authenticated HTTPS backend -> shared core -> DRAC

The web backend owns credentials and sessions; it returns normalized status and
opaque DRACula console session identifiers. Never relay device cookies, JNLP
credentials, original device pages or raw launch arguments to the frontend.

Console workers run the legacy viewer in a private display/process environment.
A modern authenticated display bridge streams output to the browser. Begin with
an isolated Java viewer and evaluate rendering capture before choosing WebRTC or
a framebuffer bridge. DRAC's proprietary video ports are not evidence of VNC.
View-only access requires input blocking at the worker/transport boundary;
hiding UI controls is insufficient. Disable clipboard and virtual media until
separately authorized and implemented.

Keep legacy cryptography confined to the worker's device connection and managed
Java profile. The public backend uses modern TLS. Restrict workers to their
assigned device, give sessions finite lifetimes, and clean up processes and
sessions after disconnect. An old viewer must not receive unrestricted backend
filesystem access. Never fetch arbitrary frontend-provided device or JAR URLs.

Adapters publish capabilities with evidence and unknown/unavailable states.
Prefer structured DRAC XML where available, then IPMI where enabled; HTTP page
inference must report provenance and freshness. No assumption of Redfish support.

Future mutation operations need a separate server-side authorization path, target
identity, explicit approval, audit trail and operation-specific validation.
Firmware and power controls remain unimplemented during read-only bring-up.
