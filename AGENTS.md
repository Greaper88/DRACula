# DRACula working rules

One repository and shared core, with desktop and web applications.
Hardware access is currently authorized only for reading status and inspecting
legacy console metadata. Never change settings, update firmware, reset a DRAC,
clear logs, mount virtual media, send remote keyboard/mouse input, or perform
power operations without explicit approval for the particular action.
192.168.1.252 is offline and reserved for later testing; its future use does not
constitute current write authorization. .253 and .254 are read-only targets.
Do not commit passwords, cookies, session identifiers, JNLP tickets, device
binaries, downloaded runtimes, or raw hardware responses. Store transient
material outside tracked files with restrictive permissions.
Legacy TLS/Java compatibility must be confined to device-facing workers, never
applied globally or to the browser-facing connection. The browser never receives
DRAC credentials or direct device URLs. Do not launch an interactive viewer until
its input suppression is verified or the user authorizes interactive access.
