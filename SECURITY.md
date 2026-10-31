# Security notes

This preview is a single-admin management tool for a trusted management network.
Use a TLS reverse proxy for remote browser access. The default Docker port binds
to loopback; do not expose it directly to the Internet.

DRAC 5 requires obsolete TLS/SSL algorithms. Device-facing workers use their own
compatibility settings and do not verify the controller certificate. Certificate
pinning/enrollment is future work. These settings never apply to browser-facing
TLS, global Java, or the modern desktop manager.

The web backend stores encrypted device credentials and keeps the encryption key
in a separate volume. The desktop has a separate optional encrypted vault. Neither
store is a substitute for protecting the host and its backups. The runtime-free
image and source archive contain no saved devices, credentials, Java runtimes or
proprietary Dell binaries.

Settings and power operations require explicit review and confirmation. Console
input starts disabled; enabling input permits control of the selected machine.
Vendor KVM menus retain their native behavior and confirmations. Operate only
controllers you are authorized to manage.

Do not put passwords, session cookies, JNLP files, vaults, raw device responses or
private management addresses in public issues. Use the repository host's private
vulnerability-reporting channel if enabled. This project does not yet claim a
completed independent security audit or multi-user access control.
