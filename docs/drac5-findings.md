# DRAC 5 hardware investigation

Historical observations from October 29, 2026 (America/Chicago). Lab addresses
have been removed; controller labels identify test hardware, not shipped profiles.

| Address | Result | Hardware | DRAC firmware | BMC IPMI enabled field |
| --- | --- | --- | --- | --- |
| Test controller | Offline per owner; HTTPS unreachable | Not queried | Unknown | Unknown |
| Controller A | Authenticated status read | PowerEdge 1950 III, DRAC A00 | 1.65 (12.08.16) | 0 |
| Controller B | Authenticated status read | PowerEdge 1950 III, DRAC A03 | 1.65 (12.08.16) | 1 |

Both report BIOS 2.7.0, BMC 2.50 and IPMI 2.0. The Enabled field is an
interface report, not proof of IPMI reachability; no IPMI commands were sent.

Modern default curl TLS negotiation failed. A connection limited to TLS 1.0,
with a connection-specific OpenSSL security-level exception and certificate
verification disabled, successfully retrieved each interface. This is discovery
evidence, not a production trust policy. Certificate enrollment/pinning remains
work. No machine-wide TLS settings were changed.

## Interface observed

The root redirects through `/cgi-bin/webcgi/index` and XSL-based navigation.
Login is a form POST to `/cgi-bin/webcgi/login` with `user` and `password`.
The authenticated `/cgi-bin/webcgi/sysinfo` response is structured XML.
`/cgi-bin/webcgi/vkvmconfig` reports current settings without a form submission.
Sessions were established using owner-authorized defaults; secrets are not stored
in this repository. Login necessarily creates authentication/session audit state.

Both devices report KVM enabled, keyboard/mouse port 5900, video port 5901,
EncryptionEnabled=0, PluginType=1, and zero active console sessions at inspection.
Maximum sessions: Controller A reports 2; Controller B reports 4. No settings were changed.

Static `/cgi/vkvm.xsl` references `/cgi-bin/webcgi/vkvmjnlp?id=...` as its Java
launcher. `/cgi/vkvmload.xsl` chooses Java or historical platform plugins based
on browser/platform. Native Linux paths also appear; portable support must not
assume that a working Java version alone solves native-library compatibility.
The JavaScript plugin version constants are XPI 2.2.0.3 and CAB 3,1,1,117;
these are not verified Java viewer versions.

During the initial inspection, no console state-transition URLs were invoked, no viewer was launched, no JNLP
was requested, no input was sent and no virtual media was attached. Exact Java
runtime, JAR/native dependencies and view-only behavior remain unverified.

Dell reference (hardware-observed ports take precedence over general tables):
https://www.dell.com/support/manuals/en-us/dell-openmanage-server-administrator-8.5/om_8.5_port_information_guide/drac-5?guid=guid-4b160f32-0cce-471b-8879-e6222ff30bbd&lang=en-us

## Historical implementation recovered

See [recovered launcher](recovered-launcher.md) for the earlier Java main class,
archive names and proposed token flow from the archived DRACula discussion.
These narrow the investigation but do not establish current runtime compatibility
or view-only access.


## Launcher bring-up (later on October 29)

Owner confirmed Controller B is powered off; Controller A is expected to show a Linux login.
Downloaded the viewer and inspected its Java input interfaces. The Linux native
keyboard library is 32-bit ELF. A private Azul Java 8u512 x86 runtime runs here.

The JNLP launch flow requires the console page initialization and a request to
`/cgi-bin/webcgi/vkvmjnlp?id=...`. Its `user` argument is a 32-character hex ticket,
not the numeric web session ID. The descriptor's main class and protocol arguments
match the recovered script. Session tickets are transient and not saved in Git.

The console handshake uses SSLv3 even with EncryptionEnabled=0. A process-local
Java security-properties override fixed the earlier SSL failure. Confirmed a
successful User Login Response (0), Video Connect Status true, and 800x600 video
resolution metadata on Controller A. The original vendor window then displayed **No
Signal**. This is not verification of the expected Linux prompt; the video source
or blanking state needs checking. No remote wake key or mouse input was sent.

The wrapper replaces keyboard and mouse transport interfaces with no-ops,
omits native keyboard capture, rejects generic control operations and removes
menus. An offline tripwire test exercises every input-interface entry point.
A shutdown hook closes its own console session. No settings, firmware, power
operations, virtual media, or remote keyboard/mouse actions were performed.

See [launcher instructions](../launcher/README.md) for limitations and commands.


## Video verification after authorized wake

The owner confirmed CentOS blanks its display and explicitly directed a NumLock
cycle. A temporary diagnostic bypassed the normal input no-op only for exactly
two NumLock press/release pairs, restoring the prior toggle parity. No other key
or mouse events were sent. After waiting for video to resume, the Controller A Linux
login prompt was visually verified in the private display. Authentication and
video rendering are therefore confirmed on this device. The normal committed
launcher remains view-only; the one-time wake helper is not part of its source.
