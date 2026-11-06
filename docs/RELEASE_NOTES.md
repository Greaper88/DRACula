DRACula v0.1.4 adds Serial over LAN to the desktop and web apps.

**Open SOL** appears beside **Open KVM** when the selected controller reports
enabled SOL over encrypted IPMI 2.0. The terminal starts in view-only mode and
offers an explicit keyboard input switch. Close the terminal to release the
session it opened.

On a Dell DRAC 5, the local web and desktop builds received live serial text.
The web console received BIOS POST output and reopened after closing. A separate
live test verified Down and Up in BIOS Setup, with the original row restored and
settings left alone. Offline tests cover capability detection, terminal rendering,
input gating, authentication boundaries and worker cleanup.

Both apps now have an About dialog with the same independence and trademark
notice as the README and third-party notices.

- **Desktop** — Download `DRACula-0.1.4.jar` and launch it with Java 17 or later.
- **Docker** — Use `ghcr.io/greaper88/dracula:0.1.4` on Linux AMD64.
- The release includes a source archive and SHA-256 checksums.

Desktop SOL requires a POSIX backend with `ipmitool` on PATH. Docker includes
the helper. BIOS or operating system serial redirection must be configured
on the managed server for the terminal to display output. See the desktop and
web setup guides for details.

[Set up Dell DRAC 5 KVM and Serial over LAN on a PowerEdge 1950](https://github.com/Greaper88/DRACula/blob/v0.1.4/docs/drac5-kvm-sol.md)
