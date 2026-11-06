# Roadmap

## Initial public preview

Implemented: shared desktop/web management, empty first-run device lists,
encrypted saved credentials, DRAC 5 status/configuration tabs, IPMI-only fallback,
reviewed settings and power actions, automatic KVM recovery, optional console
input, responsive browser framing, and matching dark/light themes.

Docker targets Linux AMD64 without Java bundled by default. The desktop ships
as an executable Java 17+ JAR with automatic private-backend setup. Windows/macOS/ARM
launcher manifests are included; hardware validation and legacy KVM portability
remain incomplete. See [release validation](release-validation.md) for test evidence.

## Next work

- Portable desktop packaging, updater and Windows/macOS/ARM validation.
- Device certificate enrollment/pinning and a fuller deployment security review.
- Additional reviewed controller/viewer versions and modular vendor adapters.
- Redfish support.
- Higher-frame-rate browser video if needed.
- Separately reviewed firmware, virtual media and maintenance workflows.

New hardware behavior and write actions need their own explicit authorization and
validation. Capability detection should keep unsupported features hidden.
