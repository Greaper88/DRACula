# DRAC 5 hardware investigation

Observed October 29, 2026 (America/Chicago). Authorized read-only access.

| Address | Result | Hardware | DRAC firmware | BMC IPMI enabled field |
| --- | --- | --- | --- | --- |
| 192.168.1.252 | Offline per owner; HTTPS unreachable | Not queried | Unknown | Unknown |
| 192.168.1.253 | Authenticated status read | PowerEdge 1950 III, DRAC A00 | 1.65 (12.08.16) | 0 |
| 192.168.1.254 | Authenticated status read | PowerEdge 1950 III, DRAC A03 | 1.65 (12.08.16) | 1 |

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
Maximum sessions: .253 reports 2; .254 reports 4. No settings were changed.

Static `/cgi/vkvm.xsl` references `/cgi-bin/webcgi/vkvmjnlp?id=...` as its Java
launcher. `/cgi/vkvmload.xsl` chooses Java or historical platform plugins based
on browser/platform. Native Linux paths also appear; portable support must not
assume that a working Java version alone solves native-library compatibility.
The JavaScript plugin version constants are XPI 2.2.0.3 and CAB 3,1,1,117;
these are not verified Java viewer versions.

No console state-transition URLs were invoked, no viewer was launched, no JNLP
was requested, no input was sent and no virtual media was attached. Exact Java
runtime, JAR/native dependencies and view-only behavior remain unverified.

Dell reference (hardware-observed ports take precedence over general tables):
https://www.dell.com/support/manuals/en-us/dell-openmanage-server-administrator-8.5/om_8.5_port_information_guide/drac-5?guid=guid-4b160f32-0cce-471b-8879-e6222ff30bbd&lang=en-us
