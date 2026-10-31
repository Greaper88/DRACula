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
the browser. The web backend now streams private Xvfb workers as JPEG frames over authenticated
WebSockets. Incoming WebSocket input is rejected, and no X server ports are exposed. A modern Java desktop manager now
uses the shared Python bridge for status, profiles and confirmed settings.


## Implemented desktop management boundary

The Java manager passes a selected device's credentials to a local Python bridge
through stdin. The bridge owns its web session and exposes catalogued reads plus
a separate staged settings protocol bound to the selected controller. It returns normalized rows with secrets omitted, not device HTML or
session cookies. Selection closes the previous bridge; responses are tagged by a
connection generation so stale results cannot populate the new device's tables.
The KVM worker is separate and has its own bounded cleanup path.

The desktop profile store separates non-secret addresses/usernames from an
AES-GCM credential vault unlocked by the user. Saving a password is optional.
Separate power, firmware, reset, log-clear and test-alert actions remain disabled.
The confirmed configuration boundary below is the only settings write path.


## Implemented web boundary

FastAPI serves both the self-contained JavaScript frontend and an authenticated
same-origin API. It reuses StatusDevice, fetch_page and the page catalog. Device
profiles are persisted with Fernet-encrypted passwords; the credential key lives
in a separate Docker volume. Browser session cookies are HttpOnly/SameSite=Strict;
mutating local-application routes require the matching Origin. Those local profile
routes do not implement hardware writes. Power uses a separate reviewed confirmation flow. Firmware, controller reset and log-clear actions remain unavailable. Configuration uses the
separate selected-target review/confirm routes described below.

Each KVM worker has a separate authenticated X display, Java process, class output
folder, temporary logs and lifetime. The image-capture process sees only that
private display. The browser gets JPEG frames, never a DRAC token or cookie.
The private Java security profile is process-scoped; normal backend/browser TLS
is unaffected. Configured blocked hosts are rejected in target validation and omitted from the fleet. No hosts are blocked by default.

A console has its own saved-credential login and does not require a live status
connection. The worker supervisor leaves healthy Java sessions untouched by web
login expiry. A process exit, transport-disconnect callback or private viewer
error dialog triggers backoff and a fresh launcher invocation, including a new
JNLP retrieval. Only safe connection state and a generation count reach the
browser. Closing the browser console cancels the supervisor and its retries.

The desktop's `--console-managed` bridge and the web's ConsoleWorker use the same
ConsoleSession supervisor. Each attempt invokes the one-shot `--console` launcher,
so retry supervision is never nested. Desktop receives the current display and
stops on a normal viewer exit; web uses private Xvfb and a bounded worker lifetime.

Normal authentication cleanup is restricted to the authenticated cookie's own
session index and verified login owner. It never accepts a caller-supplied index.
This avoids DRAC 5's ineffective ordinary logout redirect. Locked tokens can be
unlocked in place solely to end that same login; already invalidated tokens need
no new login. The public read transport still rejects arbitrary termination URLs.

## Confirmed configuration boundary

`configuration.ConfigEditor` is shared by both apps. Public device read methods
remain read-only. Only ConfigEditor.confirm can submit an allowlisted settings
form to the selected configured target after validating an unexpired, owner-bound,
single-use review token. A client supplies opaque field keys and proposed values,
not device URLs, form names, record selectors or preserved secrets. Confirmation
supplies only that review token and literal true; the server retains the exact
batch. A review performs reads only.

Stable full-record fingerprints protect against overwriting concurrent changes.
Each operation is checked again before its one POST. Readback must match the full
expected stable configuration, including unchanged fields. Unknown results stop
remaining writes; write retries and rollback are never automatic. Repeated forms
use verified record identifiers, with test-alert flags fixed off. Unavailable
secrets or incomplete/unsupported forms fail closed. Snapshot and approval state
is memory-only and cleared on connection closure. A target change invalidates the original review, even if a frontend forges edit
metadata. There are no address-specific runtime write blocks. Live testing requires
authorization for each target and each write action.


## Management adapters and capabilities

Both applications use `management.ManagementSession`. `StatusDevice` is the
DRAC 5 HTTP transport, `configuration.ConfigEditor` owns vendor settings, and
`ipmi.IpmiAdapter` independently authenticates to the BMC. HTTP login failure or
an unavailable status page can fall back to IPMI at the same configured address
with the saved credentials. This does not require a DRAC card. A BMC at a separate
address is a separate device profile. No address is probed without being selected.

The shared capabilities response contains supported page IDs, KVM availability,
settings availability and the active protocol. Both clients filter their navigation
from this response. IPMI inventory reads detect available pages; unsupported
sensor/log pages, vendor configuration and graphical KVM are hidden. The existing
DRAC 5 adapter advertises its known page catalog. Unsupported management actions
are hidden; supported power actions that are invalid for the current state are
gray. SOL is a future text-console adapter, not currently implemented. Redfish is
future work, not a dependency or part of the current implementation.

An IPMI-only backend needs `ipmitool`; Docker installs it from Debian. Native
installs use a system-provided executable on PATH. Passwords use only the child's
environment, never command arguments; child diagnostics and raw status output
are not returned to clients. Read-only probes select RMCP+ cipher 17, then cipher
3, then legacy authenticated IPMI LAN as available. Permission-limited accounts
may read through USER privilege; power is exposed only after an administrator
session succeeds. Legacy compatibility stays inside the device-facing adapter.

`power.PowerController` is the common power policy and review layer. It consumes
adapter power-state/permission reads and a fixed action allowlist. DRAC 5 form
values are on=1, off=0, reset=2 and cycle=3. Graceful shutdown uses IPMI
`chassis power soft`, requires OS/ACPI support, and never escalates to forced off.
See the [official ipmitool manual](https://github.com/ipmitool/ipmitool/blob/master/doc/ipmitool.1.in).

Review reads only. Confirmation is tied to owner, target, exact action, state,
permission and adapter, expires in 120 seconds and is single-use. A fresh read
must match before sending. If state sources disagree, all actions are disabled.
A submitted command is never rerouted to another adapter after an uncertain
response. `ipmitool -R 1` bounds its response loop to one initial command attempt;
`-R 0` would restore default retries. On/off may be verified from resulting power
state; ON alone cannot verify reset/cycle. Those requests remain submitted until
observed by the user. No forced-off fallback, write retry or rollback is automatic.


## Interactive console boundary

App consoles now launch the fingerprinted viewer with interactive capability;
keyboard/mouse forwarding starts disabled. The standalone launcher remains strict
view-only unless `--interactive` is supplied. The original vendor context/power
menus and their own confirmations are restored in interactive-capable viewers.
They use the viewer's existing six command types; the strict read-only transport
continues to reject every generic command. Vendor takeover/sharing remains blocked.
The connection-error watcher distinguishes normal confirmations from network error
dialogs instead of treating every dialog as a disconnect.

`ConsoleControl` gates vendor keyboard/mouse callbacks, tracks forwarded presses,
and releases them on disable/focus loss/disconnect. Desktop uses the Java keyboard
handler without native/global hooks. Its Input menu offers a local toggle. Viewer
power controls are independent of the keyboard/mouse switch.

Browser input is accepted only on the owning authenticated, same-origin console
WebSocket, for its current viewer generation. Messages use a fixed key/pointer
schema, bounded coordinates and rates, never arbitrary commands/addresses. A
worker-local subprocess uses XTest only on that worker's Xauthority-protected Xvfb
display. Pointer coordinates map to the displayed viewer crop, including its window
offset, allowing the original menus and dialogs to work. No host-desktop input path is exposed.
A loopback Java control broker publishes a random token/port inside the worker's
private directory; only the backend uses it to enable/release input. Browser events
never receive that token, port, display name, device credentials or JNLP ticket.

A three-second heartbeat lease drops the Java input gate if browser/backend input
stalls. Browser blur, visibility loss, Ctrl+Alt+Shift, explicit disable, socket
closure and worker teardown release tracked keys/buttons. Every reconnect uses a
new private broker endpoint and starts with input off. Old-generation messages
cannot control a replacement viewer. Session teardown closes the input subprocess
before terminating Java/Xvfb. There is no automatic remote wake key or power action.


Capture geometry is now window-scoped. The private display can accommodate a
larger viewer, but only the union of its mapped viewer windows/popups is encoded.
A shared private geometry file and opaque revision identify each crop. The framed
capture pipe pairs geometry with its JPEG; the API emits that revision before the
image, and the browser binds it only when that image is drawn. Pointer input must
match the current crop revision. A move/resize rejects stale coordinates and
releases held input. Browser-only resizing scales the canvas without changing the
native geometry, keeping pointer mapping stable. Startup uses a tiny hidden frame
rather than streaming an empty desktop. Themes affect web chrome only.
