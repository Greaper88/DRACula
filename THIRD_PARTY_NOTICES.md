# Third-party notices

The Apache 2.0 license in this repository applies to DRACula's original code and
documentation. Dependencies and separately downloaded programs retain their own
licenses and attribution requirements.

## Web image and Python packages

Direct dependencies are pinned in [requirements.txt](apps/web/requirements.txt).
Their upstream license texts and metadata are retained with the installed
packages in the image. The Debian base image and system libraries retain their
package copyright files under `/usr/share/doc`.

| Direct runtime dependency | Version | Upstream license |
| --- | --- | --- |
| FastAPI | 0.118.0 | MIT |
| Uvicorn | 0.38.0 | BSD-3-Clause |
| websockets | 15.0.1 | BSD-3-Clause |
| cryptography | 46.0.5 | Apache-2.0 OR BSD-3-Clause |
| Pillow | 12.1.1 | MIT-CMU |
| python-xlib | 0.33 | LGPLv2+ (as declared by the package) |

This table identifies direct dependencies; their full upstream license files and
transitive dependency notices remain with the installed distributions. It does
not replace those texts or relicense the dependencies.

The frontend uses repository-owned JavaScript and CSS, system fonts and no
external JavaScript libraries or remote font service. The development-only HTTP
client dependency is listed separately in `apps/web/requirements-test.txt`.

## Legacy Java and vendor viewer

See [runtime and third-party packaging](apps/web/THIRD_PARTY.md) for the pinned
Azul Zulu package, source/redistribution considerations and Dell viewer policy.
The default image downloads Java on the deploying host's first launch instead of
redistributing it inside the image. The Dell viewer is downloaded only from the
user's authorized controller, fingerprinted and kept in the private cache.
Neither component is part of the source release.

The archived launcher under `docs/history` is project history, not a bundled
runtime or vendor binary. It is not the supported launcher entry point.

## Executable desktop JAR

The JAR embeds Apache Commons Compress 1.28.0, Commons IO 2.20.0, Commons Codec
1.19.0 and Commons Lang 3.18.0, all under Apache-2.0. Their upstream LICENSE and
NOTICE files are retained separately under `META-INF/licenses/` in the JAR.
Build dependency URLs and SHA-256 values are pinned in
`apps/desktop/bootstrap/dependencies.json`.

The JAR downloads CPython 3.12.16 from the official
[python-build-standalone 20261026 release](https://github.com/astral-sh/python-build-standalone/releases/tag/20261026).
It does not embed Python binaries. Each platform archive is pinned by SHA-256;
its included Python and component license files remain in the extracted private
runtime. CPython and its bundled components retain their upstream licenses.
See the upstream [distribution documentation](https://gregoryszorc.com/docs/python-build-standalone/main/distributions.html).

When Linux desktop KVM is missing 32-bit Xtst, the portable launcher downloads
Debian's `libxtst6` i386 package version `2:1.2.3-1.1` directly from
[Debian](https://packages.debian.org/bookworm/libxtst6). The package, library and
copyright-file SHA-256 values are pinned in `src/dracula/kvm_runtime.py`.
Only the library and upstream copyright/license text are copied into the private
`state/lib32` cache; no package scripts run. The library retains its X.Org/MIT
licenses, recorded in `state/lib32/usr/share/doc/libxtst6/copyright`.
It is downloaded on demand, not embedded in the JAR or source archive.
