# Changelog

## 0.1.0 — initial public preview

- Shared Python core for a Linux desktop manager and Docker-hosted web dashboard.
- User-configured devices with encrypted credentials; fresh installs start empty.
- One executable Java 17+ desktop JAR with embedded shared core and pinned private
  Python downloads for Windows, macOS and Linux x64/ARM64.
- Published GHCR image, copyable Compose deployment, release assets and checksums.
- Apache 2.0 licensing, retained dependency notices and required AI disclosure.
- DRAC 5 status/configuration tabs and capability-based IPMI fallback.
- Staged settings with confirmation and readback; confirmed power operations.
- Isolated legacy Java KVM, automatic fresh-JNLP recovery, connection status and
  optional keyboard/mouse input that starts disabled.
- Browser capture cropped to the viewer, responsive scaling and stale-frame input
  protection. Fixed clipping after height-only browser resizing.
- Dark/light themes in both apps.

Preview limits: Linux AMD64 Docker; desktop execution verified on Linux x86-64,
with Windows/macOS/ARM runtime selection prepared but hardware unverified. Legacy
KVM currently remains Linux x86-64 only; desktop IPMI needs ipmitool. No Redfish,
SOL, firmware updates or virtual media mounting. Hardware video-mode transitions during POST remain unverified;
resolution changes through the web stream were tested with generated frames.
