# DRACula desktop manager

The first desktop manager runs on modern Java (17+) and uses the shared Python
read-only device layer. The legacy KVM stays in a separate private 32-bit Java 8
process. This is a Linux development build; Windows/macOS distribution packaging
and a standalone app updater are not implemented yet.

## Start

From the repository root, on a graphical desktop:

```sh
./apps/desktop/dracula
```

The first run builds `.local/desktop/dracula-manager.jar` with JDK 17+.
Later runs reuse it unless the desktop sources changed. Python 3.12+ and curl
are required by the current shared device bridge. For KVM, prepare the private
runtime using `./launcher/drac5 --setup`; see [KVM requirements](../../launcher/README.md).

## Devices and passwords

Use the top **Device** dropdown or the machine list to select a DRAC. Selection
ends the old status connection and clears its displayed data. Click **Connect**
to authenticate. Nothing connects automatically to the offline .252 machine.

**Manage devices** adds, edits or removes display names, IPv4 addresses, usernames
and passwords. Profiles initially include .252, .253 and .254 with username root;
no default passwords are saved or embedded in the app.

Passwords can be kept for this app session only, or saved in an encrypted local
vault. On first saving a password, create an unlock password. Subsequent app
launches require it before saved credentials can be used. The unlock password
is kept in memory until the app closes; it is not written to disk. There is no
password recovery if it is lost.

Profile names, IPs and usernames are in `.local/manager/devices.properties`.
Saved passwords are separate in `.local/manager/passwords.vault`, protected by
AES-256-GCM with a new random salt and nonce on each save and PBKDF2-HMAC-SHA256
(210,000 iterations). Files are replaced atomically and restricted to the owner
on POSIX systems. Passwords, cookies and tickets are never committed to Git.

## Read-only tabs

28 tabs are organized into eight sections:

- **System:** overview and power state.
- **Logs:** system event log, POST history, DRAC event log.
- **Hardware:** batteries, fans, intrusion, performance, power monitoring,
  power supplies, temperatures and voltages.
- **Controller:** DRAC information, network, services, serial and serial over LAN.
- **Access:** users, directory services, certificate and sessions.
- **Alerts:** event filters, trap destinations and email configuration.
- **Console:** KVM settings and virtual media settings.
- **Maintenance:** current firmware versions and disabled update controls.

Tabs read on first selection; **Refresh tab** reads again. Tables are searchable,
sortable and read-only. Current readings retain units. Repeated sensor and log
records stay separate. Known health-code meanings come from the device's own XSL
renderer; unrecognized codes remain unknown. Failed reads are displayed as errors,
not normal status. Secret fields and session tokens are omitted.

Settings, firmware, power, media, log-clear, session-termination and test-alert
buttons are visible but disabled. The backend only exposes a fixed catalog of
read endpoints; arbitrary paths and non-login POST requests are rejected.
There is no approval button that silently enables writes in this version.

**Open KVM window** starts the existing view-only viewer using the selected
device's credentials. It does not send wake keys automatically. Normal status
selection does not launch a console or allocate a KVM ticket.

## Validation

Live .253 desktop/bridge checks passed for overview, power, temperatures, fans,
system events, network and certificate display. All original status/configuration
pages were inventoried read-only; a layout check covers all 28 tabs and verifies
that management actions stay disabled. Credential storage tests use synthetic
passwords and cover round-trip persistence, wrong-password rejection, tampering,
IP changes and removal.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
./apps/desktop/build.sh
mkdir -p .local/desktop/test-classes
javac --release 17 -cp .local/desktop/classes -d .local/desktop/test-classes apps/desktop/tests/dracula/DeviceStoreTest.java
java -cp .local/desktop/classes:.local/desktop/test-classes dracula.DeviceStoreTest
```
