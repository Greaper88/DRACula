# DRAC 5 console launcher

Linux x86 launcher for the reviewed Dell DRAC 5 Java viewer. It uses a private
32-bit Azul Java 8 runtime and leaves system Java unchanged.

## Setup and launch

Requirements: Python 3.12+, curl, a graphical display and the compatible 32-bit
Linux libraries listed in the [desktop guide](../apps/desktop/README.md).
Run from the repository root:

```sh
./launcher/drac5 --setup
./launcher/drac5 192.0.2.10 --legacy-tls
```

Replace the documentation address with your authorized controller. Enter its
password at the prompt; use `--user` if the username differs from `root`.
`--inspect` reads console metadata without requesting a KVM ticket.
`--seconds 30` closes the viewer automatically. `--verbose` prints redacted
connection diagnostics on exit.

The default standalone launcher is strictly view-only. Before allocating a ticket,
it verifies the viewer's SHA-256 and runs offline input-suppression checks. It
replaces remote input interfaces with no-ops, disables native keyboard capture,
blocks generic control commands and removes menus.

Use `--interactive` to offer the original viewer menus and an explicit input
switch, as the desktop and web managers do. Input still starts disabled.
**Ctrl+Alt+Shift** releases capture. Native menus retain their own behavior and
confirmations; interactive mode can control the remote machine.

## Runtime and transport

`--setup` downloads the pinned Azul Zulu CA 32-bit JDK 8u512 and verifies its
SHA-256 before extraction. A JDK is currently needed because the small adapter is
compiled locally against the fingerprinted viewer. The source distribution
contains neither that runtime nor Dell binaries. See
[third-party notices](../apps/web/THIRD_PARTY.md).

DRAC 5's console requires a worker-local Java security override, equivalent to
changing `jdk.tls.disabledAlgorithms` in the runtime's security file. The launcher
uses `-Djava.security.properties=.../legacy-java.security`; it does not edit the
runtime or global Java configuration. This legacy profile permits SSLv3.
`--legacy-tls` also opts into device HTTPS with TLS 1.0 and without certificate
verification. Use only on a trusted management network.

The launcher validates the JNLP target, application class, argument schema and
viewer fingerprint. Tickets reach Java through stdin, not command-line arguments.
Private authentication files and vendor logs are removed on exit; only the
runtime and reviewed viewer cache are retained under `.local`.

Windows/macOS, ARM, encrypted viewer transport, other viewer fingerprints and a
universal portable desktop bundle remain unvalidated. See
[release validation](../docs/release-validation.md) for current evidence.
