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

## Runtime separation and presentation

Preferred desktop direction: a modern Java manager (a compatible host JVM, with
an optional bundled modern runtime) spawning a private 32-bit Java 8 console
worker. A bootstrap launcher can later retrieve verified application JARs and
runtimes. Python currently supplies bring-up tooling, not the final desktop UI.

Desktop console presentation is a dedicated view-only window initially;
embedding is optional later. Web deployments run that worker on a private display
and expose a browser-compatible stream (for example a framebuffer bridge over
WebSocket). Do not expose the Java protocol, device cookies, or legacy TLS to
the browser. The browser bridge is not implemented yet. A modern Java desktop manager now
uses the shared Python read-only bridge for status and profile selection.


## Implemented desktop management boundary

The Java manager passes a selected device's credentials to a local Python bridge
through stdin. The bridge owns its web session and exposes only catalogued read
operations. It returns normalized rows with secrets omitted, not device HTML or
session cookies. Selection closes the previous bridge; responses are tagged by a
connection generation so stale results cannot populate the new device's tables.
The KVM worker is separate and has its own bounded cleanup path.

The desktop profile store separates non-secret addresses/usernames from an
AES-GCM credential vault unlocked by the user. Saving a password is optional.
All hardware-changing controls remain disabled and have no backend write route.
