First public preview of DRACula: shared desktop and web management for DRAC 5 and IPMI controllers.

- Docker image: `ghcr.io/greaper88/dracula:0.1.2` (Linux AMD64, Java downloaded on first launch).
- `DRACula-0.1.2.jar`: single executable desktop JAR for Java 17+. Double-click where your OS associates JARs with Java, or run `java -jar DRACula-0.1.2.jar`. It extracts its support code and downloads a checksum-pinned private Python backend. No checkout or separate Python install is required.
- Source archive and SHA-256 checksums are attached.
- Apache 2.0 licensing, notices, contributing instructions and required AI disclosure.

Fresh installs start with no controllers or device credentials. Settings and power require review and confirmation; KVM input starts off.

The portable launcher selects Windows, macOS or Linux runtimes on x64/ARM64. Linux x86-64 is verified here; Windows/macOS/ARM device access remains unverified. Legacy DRAC 5 KVM is currently enabled only on verified Linux x86-64 and still needs compatible 32-bit system libraries. IPMI requires `ipmitool` on the desktop; Docker includes it. Firmware flashing, virtual media, Redfish and SOL are future work.

See README for the copyable Compose configuration and first-run password setup. No default dashboard password is included. Consult SECURITY.md before LAN deployment.
