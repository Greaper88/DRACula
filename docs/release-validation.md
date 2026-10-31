# Release validation — 0.1.1 preview

Prepared October 31, 2026 (America/Chicago). This release pass used offline
fixtures and isolated local containers/displays. No management-controller request
or remote input was sent. Existing local desktop and web server lists were cleared;
dashboard login configuration was preserved.

## Reproduce the automated checks

Requirements: Python 3.12+, JDK 17+ and Node.js 22.8+. Build dependencies download
from pinned Maven Central artifacts on first build; no hardware is used.

```sh
python3 -m venv .venv
.venv/bin/pip install -r apps/web/requirements-test.txt
PYTHON_BIN=.venv/bin/python ./scripts/check.sh
```

The current pass completed **117 Python tests**, **29 browser logic tests** and
**six Java test programs** without skips. Coverage includes parsers, profile/vault
handling, empty first-run lists, last-profile removal/restart, confirmation binding,
power state/permissions, reconnect/cleanup, input gates, geometry, themes, portable
HTTP isolation and bootstrap archive/path/link safety.

```sh
./apps/desktop/build.sh
java -Djava.awt.headless=true -Ddracula.home=/tmp/dracula-clean-check \
  -jar dist/DRACula-0.1.1.jar --prepare-only
python3 scripts/build-release.py
```

The executable JAR downloaded and SHA-256-verified private Python from a fresh
isolated directory, then launched the actual desktop manager from outside the
checkout. Its private Python imported the embedded shared core, profiles were
empty, and no device connection occurred. Six platform runtime manifests are
validated offline; only Linux x86-64 execution is verified here. The desktop JAR
contains Apache/dependency notices and no Java, Python or vendor runtime binaries.

## Docker

```sh
docker build --platform linux/amd64 -f apps/web/Dockerfile \
  --build-arg BUNDLE_JAVA=false -t ghcr.io/greaper88/dracula:0.1.1 .
docker compose -f compose.release.yaml config --quiet
```

The runtime-free image was inspected with networking disabled: no saved profiles,
Java runtime, Dell JAR, JNLP tickets or device responses were present. Apache and
third-party notice files were included. An isolated first install used fresh
volumes, downloaded and verified private Java, and passed its health check. A
subsequent restart with container networking disabled reused that cache, ran Java
8u512, and served HTTP health successfully. The default deployment retains a
non-root user, read-only root filesystem, dropped capabilities and loopback port.

The browser displayed an empty fresh-install fleet and saved a synthetic profile
without connecting. API regression tests cover removing the final profile. The
isolated test profile was cleared locally; disposable release-test volumes were
removed after validation.

## Publication hygiene

Pattern scans covered publishable working files and all existing Git history
blobs. Saved device passwords were also compared privately against source/history;
no matches were found and no credential values were printed. No runtime, vendor
binary or private state is included in the source archive. Downloaded caches and
credentials are excluded from Git and the Docker build context. Source examples
and test fixtures use documentation addresses rather than live server entries.
This is a release hygiene check, not a completed independent security audit.

The tagged release workflow runs the checks, builds the JAR/source archive and
checksums, publishes `ghcr.io/greaper88/dracula`, and attaches assets to the GitHub
preview release. Action versions and downloaded build/runtime artifacts are pinned.

## Earlier hardware evidence and remaining limits

Earlier authorized DRAC 5 tests covered status, reviewed settings readback,
confirmed power, KVM recovery after HTTP expiry, repeated session cleanup and
optional input. Browser sizes included 1920×1080, 1280×720, 800×600, 390×844 and
844×390, plus height-only changes. A clipping bug on static-picture height changes
was fixed. An approved chassis reset kept KVM connected through POST.

POST retained the same captured dimensions. Actual hardware video-mode transitions
remain unverified. Generated JPEG frames from 640×504 through 1600×1224, including
viewer chrome, passed through the production authenticated stream and refitted
in both directions without reconnecting or stretching. Windows/macOS/ARM hardware,
additional viewer fingerprints and standalone IPMI helpers need further work.
