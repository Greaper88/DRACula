# DRAC 5 view-only launcher

Current Linux x86 development launcher, using an isolated 32-bit Java 8 build.
Windows/macOS packaging and the modern Java manager are future work.

From the repository root:

```sh
./launcher/drac5 --setup
./launcher/drac5 192.168.1.253 --legacy-tls
```

Enter the DRAC password at the prompt. `--inspect` reads configuration without
requesting a console ticket. `--seconds 30` closes the console automatically.
`--verbose` prints redacted diagnostics when the console closes.

The app opens a dedicated view-only console window. It uses a Java subclass of
the exact fingerprinted Dell viewer, replacing keyboard/mouse interfaces with
no-ops, disabling native keyboard capture and generic control commands, and
removing menus. The packet-tripwire self-test runs before a ticket is requested.
No firmware, power, virtual-media or configuration commands are implemented.

The launcher retrieves the JNLP itself and sends its temporary ticket to the
worker over stdin, not the process command line. Only the known DRAC 5 viewer
hash is accepted; a different firmware/viewer build requires adapter review.
Viewer archives, Java runtimes, device responses and tickets are never committed.
Private session folders and their vendor logs are deleted on exit.

## Legacy Java configuration

The file normally remembered as `jre/lib/security/java.security` contains
`jdk.tls.disabledAlgorithms`. This launcher supplies an equivalent process-local
override with `-Djava.security.properties=.../legacy-java.security`, leaving
system Java untouched. DRAC 5's console authentication required SSLv3 during
live testing, even with its video encryption setting disabled. The compatibility
file deliberately allows legacy algorithms in this worker only. Do not use it
for the modern manager or web server. Device HTTPS also needs TLS 1.0 and an
explicit `--legacy-tls` opt-in; certificate enrollment/pinning is future work.

## Development dependencies and limits

Python 3.12+, curl, Linux x86 userspace with 32-bit glibc/X11 libraries, and a
local graphical display. The current pinned package is Azul's 32-bit Java 8
JDK 8u512, used to compile the small adapter during development. A release can
precompile the adapter and ship a smaller portable JRE. SHA-256 is checked on
runtime download. This is not yet a universal dependency-free portable bundle.

This workstation was missing 32-bit `libXtst.so.6`; its Ubuntu package was
extracted privately into `.local/lib32`, without system installation. The launcher
adds that private library folder to the worker's search path. Other machines may
need additional compatible 32-bit libraries; automatic bundling is unfinished.

## Verified October 29, 2026

- Private 32-bit runtime starts successfully.
- Input-blocking self-test passes before any live console connection.
- .253 web authentication, JNLP retrieval, console authentication and video
  resolution negotiation succeed with the private SSLv3 profile.
- The vendor video window displays **No Signal**. The expected Linux login prompt
  has not yet been verified. This may reflect a blanked local video output;
  the cause is not established. No input was sent to wake it.
- .254 is powered off per the owner; .252 remains offline.
- Logout responses were not consistently confirmed. The console shutdown hook
  closes its own socket/session, and temporary credentials are deleted locally.
