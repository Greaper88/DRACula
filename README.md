# DRACula — Dell DRAC 5 KVM and IPMI management

Manage Dell DRAC 5 and IPMI controllers from your browser or desktop. DRACula
opens the legacy KVM console and IPMI Serial over LAN (SOL), reads hardware
status, and provides reviewed settings and power controls.

**0.1.4 is an early public preview.** Docker supports Linux AMD64. The desktop
ships as one executable JAR with automatic backend setup; hardware validation
currently covers Linux x86-64.

## What works

- Multiple saved devices, encrypted credential storage, and capability-based tabs.
- DRAC 5 status, sensors, logs and supported configuration fields.
- Local settings drafts with an exact-change review, confirmation and readback.
- Confirmed power controls, including IPMI fallback and graceful shutdown.
- Legacy Java KVM in a desktop window or a browser stream, with automatic recovery
  using saved credentials and a fresh JNLP after a disconnect.
- Optional keyboard/mouse control, initially off; reconnecting turns input off.
- IPMI Serial over LAN in both apps with an explicit keyboard input switch.
- Dark and light themes in both apps. The browser console fits the available space.

IPMI-only devices show the supported status and power pages. DRAC KVM and vendor
configuration are hidden when unavailable. Redfish, firmware flashing,
virtual-media mounting, log clearing and controller resets are not implemented.

## Web app: published Docker image

Image: **`ghcr.io/greaper88/dracula:0.1.4`** ([package](https://github.com/Greaper88/DRACula/pkgs/container/dracula)).
Linux AMD64 is supported. Copy this into `compose.yaml`:

```yaml
services:
  dracula:
    image: ghcr.io/greaper88/dracula:0.1.4
    platform: linux/amd64
    init: true
    ports:
      - "127.0.0.1:8788:8080"
    volumes:
      - dracula-data:/data
      - dracula-keys:/keys
      - dracula-cache:/app/.local
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=256m
    read_only: true
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    pids_limit: 256
    mem_limit: 1g
    cpus: 2
    restart: unless-stopped
volumes:
  dracula-data:
  dracula-keys:
  dracula-cache:
```

Create your own dashboard password, then start:

```sh
docker compose run --rm dracula python3 -m dracula.web_setup
docker compose up -d
```

Open [http://localhost:8788](http://localhost:8788). There is **no default password**.
The first start downloads and verifies a private Java runtime from Azul. Later
starts reuse the cache. The image contains neither Java nor Dell's viewer.
See [web setup](apps/web/README.md) for LAN access, persistence and source builds.

Both apps start with an empty device list. Use **Manage devices → Add device**,
enter the controller's address and credentials, select it, then choose **Connect**.
A saved profile never connects automatically.

## Desktop app: one executable JAR

Download **[DRACula-0.1.4.jar](https://github.com/Greaper88/DRACula/releases/download/v0.1.4/DRACula-0.1.4.jar)**
from [Releases](https://github.com/Greaper88/DRACula/releases/tag/v0.1.4).
Install Java 17 or newer, then double-click the JAR where your OS associates JAR
files with Java. The equivalent command is:

```sh
java -jar DRACula-0.1.4.jar
```

No source checkout or separate Python installation is needed. First launch
extracts the shared core and downloads a checksum-pinned private Python backend.
The launcher selects Windows, macOS or Linux on x64/ARM64. Published-JAR backend
setup passed on Windows, macOS and Linux hosted runners. Hardware access outside
Linux x86-64 remains unverified. Profiles live in the
OS's per-user app data directory, rather than inside the JAR.

Legacy DRAC 5 KVM currently runs only on verified Linux x86-64 and needs compatible
32-bit system libraries. Its private Java runtime is downloaded on first console
use. Desktop IPMI needs `ipmitool` on PATH; Docker includes it. See
[desktop setup](apps/desktop/README.md) for compatibility and source-build details.

## Management and console behavior

Reading status does not apply settings or send power commands. Supported settings
are staged locally; **Apply changes…** shows the exact device and proposed changes
before a separate confirmation. Power actions have their own review. The legacy
KVM viewer retains its original menus and confirmations.

Console input starts disabled. Enable it explicitly to control a machine;
**Ctrl+Alt+Shift** releases capture. Closing the console stops its worker and
reconnect attempts. A healthy KVM connection survives DRAC web-login expiry.

**Open SOL** appears next to KVM when the selected controller reports enabled
Serial over LAN over encrypted IPMI 2.0. It opens the server's serial terminal
with keyboard input off. Set up BIOS serial redirection to the controller for
firmware output. For an operating system login, the OS must also use that serial
port. Closing the terminal releases the session opened by DRACula.

Use a trusted management network. Device-side DRAC 5 compatibility uses obsolete
TLS and does not verify the controller certificate. It is confined to private
workers and never applied to browser-facing TLS. See [security notes](SECURITY.md).

## Development and release checks

```sh
python3 -m venv .venv
.venv/bin/pip install -r apps/web/requirements-test.txt
PYTHON_BIN=.venv/bin/python ./scripts/check.sh
```

The checks use synthetic devices, require JDK 17+ and Node.js 24+, and do not
contact hardware. Node is a development dependency only; neither app requires a
Node server. See [release validation](docs/release-validation.md) for build checks
and [runtime notices](apps/web/THIRD_PARTY.md) for third-party distribution details.

- [Architecture](docs/architecture.md)
- [Dell DRAC 5 KVM and Serial over LAN setup on a PowerEdge 1950](docs/drac5-kvm-sol.md)
- [DRAC 5 field mapping](docs/drac5-fields.md)
- [Changelog](CHANGELOG.md)
- [Roadmap](docs/roadmap.md)

## License and contributions

DRACula's original code and documentation use the [Apache License 2.0](LICENSE).
See [NOTICE](NOTICE), [third-party notices](THIRD_PARTY_NOTICES.md) and
[contributing guidance](CONTRIBUTING.md). AI-assisted contributions require the
disclosure format in [AGENTS.md](AGENTS.md).

## Trademarks and affiliation

DRACula is an independent, open-source project. “DRAC” refers to Dell Remote
Access Controller and is used in the project name to identify hardware the
software is designed to work with. DRACula is not affiliated with, endorsed by,
or sponsored by Dell Technologies.

Dell Technologies, Dell, and other Dell trademarks are trademarks of Dell Inc.
or its subsidiaries.
