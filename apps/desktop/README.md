# Desktop setup

The release is one executable JAR requiring Java 17+. Its shared Python core is
embedded as support code, and a checksum-pinned private Python runtime is
downloaded on first launch. Neither Python nor the source checkout needs to be
installed separately.

## Download and launch

Download [DRACula-0.1.2.jar](https://github.com/Greaper88/DRACula/releases/download/v0.1.2/DRACula-0.1.2.jar)
from the [release page](https://github.com/Greaper88/DRACula/releases/tag/v0.1.2).
Double-click it if JAR files are associated with Java, or run:

```sh
java -jar DRACula-0.1.2.jar
```

First setup requires HTTPS access to GitHub's official standalone-Python release.
Downloads are platform-specific and pinned to SHA-256 in
`apps/desktop/bootstrap/python-runtimes.properties`. Later starts reuse the
private backend. Java is not bundled. Some OS installations require you to set a
JAR file association before double-clicking will launch Java.

| Platform | Desktop launcher | DRAC 5 KVM |
| --- | --- | --- |
| Linux x86-64 (glibc) | Verified | Verified; compatible 32-bit libraries required |
| Linux ARM64 (glibc) | Runtime selected; hardware unverified | Hidden in this preview |
| Windows x64 / ARM64 | Runtime selected; hardware unverified | Hidden in this preview |
| macOS Intel / Apple Silicon | Runtime selected; hardware unverified | Hidden in this preview |

DRAC HTTP uses a private stdlib transport without requiring curl. Desktop IPMI
still needs `ipmitool` on PATH. The Docker app includes its IPMI and KVM libraries.
Support for a Java runtime on an OS does not by itself validate the legacy vendor
viewer or native IPMI helper on that OS.

App data is stored under `%LOCALAPPDATA%/DRACula` on Windows,
`~/Library/Application Support/DRACula` on macOS, or
`${XDG_DATA_HOME:-~/.local/share}/dracula` on Linux. `-Ddracula.home=/path` overrides
that location. The `state/manager` directory contains profiles and the optional
vault; `runtimes` contains private Python and `state/runtime32` the legacy Java.
Support code is extracted into a versioned `core-*` folder. Moving the JAR does
not move or delete saved profiles.

## KVM dependencies on Linux x86-64

The portable JAR prepares private Java on first KVM use. The viewer also requires
32-bit glibc, libstdc++, X11, Xext, Xrender, Xtst, Xi, freetype, fontconfig and ALSA.
For Debian/Ubuntu, install the compatible packages with administrator access:

```sh
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install libc6:i386 libstdc++6:i386 libx11-6:i386 libxext6:i386 \
  libxrender1:i386 libxtst6:i386 libxi6:i386 libfreetype6:i386 \
  libfontconfig1:i386 libasound2:i386
```

Names can differ on other distributions. No system Java security files are edited.
The viewer is retrieved only from your selected DRAC and must match the reviewed
fingerprint.

## Build or run from source

Builders need Python 3.12+, JDK 17+ and internet access once to fetch pinned Apache
Commons dependencies from Maven Central. Build with:

```sh
./apps/desktop/build.sh
```

The output is `dist/DRACula-0.1.2.jar`. It embeds Java dependencies with their
upstream notices, shared Python source and launcher support files, with no device
credentials, runtime binaries or Dell viewer.

For the existing source launcher:

```sh
./apps/desktop/dracula
./launcher/drac5 --setup
```

Source mode uses the checkout's Python/curl tools and `.local` state. It remains
useful for development. The portable JAR uses its independent per-user data store.

## Devices and passwords

A fresh install has **no devices or saved credentials**. Choose **Manage devices →
Add device**, enter a name, IPv4 address, username and password, then select it and
choose **Connect**. Use the top dropdown or machine list to switch devices.
Selection closes the previous status connection and console. Nothing connects at
startup. Removing the last device leaves an empty list across restarts.

Passwords can remain in memory for the current app session or be saved in the
local encrypted vault. Saving first asks you to create a vault unlock password;
future launches need it to use saved credentials. There is no password recovery.
Desktop and web have separate profile stores; neither automatically imports the
other's credentials. Portable JAR and source mode also use separate state locations.

| Source-mode path | Contents |
| --- | --- |
| `.local/manager/devices.properties` | Device names, addresses and usernames |
| `.local/manager/passwords.vault` | Optional AES-256-GCM encrypted credentials |
| `.local/preferences` | Remembered desktop theme |
| `.local/runtime32` | Downloaded legacy Java runtime |
| `.local/viewer.jar` | Fingerprinted viewer downloaded from your controller |

Profiles and vault files are written atomically with owner-only permissions on
POSIX systems. The vault uses PBKDF2-HMAC-SHA256 with a fresh salt and nonce on
save. Keep local state out of source archives and issue reports.

## Using the manager

Supported DRAC 5 devices expose 28 tabs across System, Logs, Hardware, Controller,
Access, Alerts, Console and Maintenance. Tabs read when first selected; **Refresh
tab** reads again. Filtering and sorting operate on the displayed fields.
Unsupported pages disappear on IPMI-only connections.

Binary fields use labeled toggles. Editable settings stage local drafts;
**Apply changes…** shows the device, old values, proposed values and warnings.
Only the final confirmation submits them. Cancel preserves the draft; **Discard
edits** restores the loaded values. An unverified Apply requires a refresh before
further editing. Secrets and unsupported forms stay locked.

Power controls reflect current state and permissions and require their own
confirmation. Graceful shutdown uses IPMI `power soft` and needs OS/ACPI support.
Firmware flashing, virtual-media mounting, controller reset and log clearing are
unavailable.

**Open KVM window** opens a separate viewer. Its status shows **Connected** or
**Reconnecting**; a drop triggers a fresh login and JNLP. Closing the viewer stops
retries. Healthy video remains independent of HTTP status-login expiry.
Keyboard/mouse input starts off. Enable it through **Input → Keyboard and mouse**;
**Ctrl+Alt+Shift** releases capture. Native viewer menus retain their own behavior
and confirmations. A blanked remote screen is not automatically woken.

**Light mode / Dark mode** beside the app title switches the manager and its
dialogs immediately and remembers the choice. Pending edits survive a theme
change. The remote video and vendor viewer keep their own colors.

For automated checks, see [release validation](../../docs/release-validation.md).
