# Release validation — 0.1.2 preview

Prepared October 31, 2026 (America/Chicago). This release pass used offline
fixtures and isolated local containers/displays. No management-controller request
or remote input was sent. Existing local desktop and web server lists were cleared;
dashboard login configuration was preserved.

## Reproduce the automated checks

Requirements: Python 3.12+, JDK 17+ and Node.js 24+. Build dependencies download
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
  -jar dist/DRACula-0.1.2.jar --prepare-only
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
  --build-arg BUNDLE_JAVA=false -t ghcr.io/greaper88/dracula:0.1.2 .
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

The separate portable-smoke workflow can prepare the published JAR without a
checkout on Linux, Windows and macOS hosted runners. This checks runtime startup,
not remote hardware or vendor KVM compatibility.

Public v0.1.2 verification completed: anonymous GHCR pull, matching JAR/source
checksums, and successful private-backend setup using the published JAR on
Windows, macOS and Linux hosted runners. The release workflow and separate
portable-smoke workflow both passed.

## Published-artifact fresh-install hardware check

The published 0.1.2 image was pulled by immutable digest and the release JAR was
redownloaded and checked against the published SHA-256. Separate empty web and
desktop data stores were used with one authorized diskless DRAC 5 target. No
other controller was accessed; input stayed disabled throughout. No power,
configuration, firmware or virtual-media changes were sent.

The web image downloaded its own pinned Java runtime and viewer, read overview,
fan, temperature and KVM settings, and displayed the POST screen in the browser.
Closing it removed the worker and returned the KVM count to zero.

The JAR downloaded its private Python backend and read status through the portable
stdlib HTTPS transport. Its initial KVM launch exposed a missing host prerequisite:
32-bit `libXtst.so.6`. With that documented library supplied privately in a new
isolated installation, the unchanged published JAR downloaded its own private Java
and viewer and displayed the same POST screen. Input remained disabled, closing
removed its worker, and final controller readback showed zero KVM sessions. No
host packages were installed or changed.

Fresh application state does not provide the desktop's documented native system
libraries automatically. In 0.1.2, a missing library can appear as a reconnecting
console rather than a direct dependency message. A clearer preflight error remains
an improvement to make. Docker already includes these libraries.

## 0.1.3 desktop prerequisite repair

A user's independently downloaded 0.1.2 JAR reproduced the same missing 32-bit
Xtst prerequisite. The source fix adds a local AWT/font preflight before creating
a console supervisor. Portable mode downloads the pinned Debian i386 Xtst package
when needed, verifies package and selected-file SHA-256 values, and retains its
copyright file privately. No system package or global Java setting is changed.
Other prerequisites and display failures stop with an actionable console-dialog
error before logging into a controller.

The real private Java runtime reproduced the missing-library failure on an
isolated local display. The fix downloaded the library and passed AWT/font
startup; another check reused it without downloading. All **128 Python tests**,
**29 browser tests** and **six Java test programs** passed. New coverage includes
pre-login failure, missing loader/display/library, download failure, checksum
rejection, restricted package copying and retained notices. No controller was
accessed while testing this fix.

The rebuilt JAR also passed a separate empty-data bootstrap using its embedded
core and private Python, followed by the real Java graphics check and private
Xtst download. Docker rebuilt successfully and passed network-disabled import
and empty-install inspection. The workstation's existing app cache received the
same private library and passed local graphics startup; profiles, credentials
and host packages were not changed. The local build is
`dist/DRACula-kvm-fix.jar`; no release assets were replaced.

## 0.1.3 publication

The author confirmed that the transferred fixed JAR opened KVM successfully on
another desktop. Version 0.1.3 packages the same repair, with updated release
metadata, download links and retained third-party notices. Existing 0.1.2 assets
are preserved. The release workflow reruns the offline checks, builds the JAR
and source archive, generates checksums, verifies standalone backend bootstrap,
and publishes the matching runtime-free Docker image and preview release.
No live controller access is needed for publication.
