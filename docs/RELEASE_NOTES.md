Desktop KVM startup fix for the DRACula public preview.

On Linux x86-64, a missing 32-bit `libXtst.so.6` could leave the desktop KVM
reconnecting without opening a viewer. Version 0.1.3 checks local Java graphics
and fonts before creating a KVM session. The portable launcher downloads and
verifies the missing Xtst library into its private cache, retaining its license
and leaving host packages unchanged. Other missing prerequisites appear as a
readable error in the console dialog.

The author confirmed that the fixed JAR worked after transfer to another desktop.
Local validation passed 128 Python tests, 29 browser tests, six Java test programs,
fresh-JAR backend setup, real Java graphics startup, private-library download/cache
reuse, and the Docker build. No live hardware was accessed for this patch's checks.

- **Desktop:** download `DRACula-0.1.3.jar`, then double-click with Java 17+ or run `java -jar DRACula-0.1.3.jar`.
- **Docker:** `ghcr.io/greaper88/dracula:0.1.3` (Linux AMD64).
- Source archive and SHA-256 checksums are attached. Version 0.1.2 assets remain unchanged.

Profiles stay in the existing per-user app-data directory when replacing the JAR.
Legacy DRAC 5 KVM remains Linux x86-64 only and needs the other documented 32-bit
system libraries. Desktop IPMI needs `ipmitool`. Backend startup on other operating
systems does not establish legacy KVM compatibility. Console input starts off;
settings and power operations retain their confirmation workflows.

See the README and desktop setup guide for installation and prerequisites.
