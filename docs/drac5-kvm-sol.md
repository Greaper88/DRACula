# Dell DRAC 5 KVM and Serial over LAN on a PowerEdge 1950

DRACula opens the Dell DRAC 5 graphical console and the IPMI Serial over LAN
(SOL) text console from the same device profile. KVM shows the server's video
output. SOL shows BIOS and operating system text sent to its serial port.

Install the [web dashboard or desktop JAR](../README.md), then add your
controller in **Manage devices** and choose **Connect**. Use an authorized
controller account and a trusted management network.

## Open the DRAC 5 KVM console

Choose **Open KVM** to see the server's display. DRACula uses a private Java
runtime for the legacy viewer. The Docker app keeps Java on the server and
streams the console to the browser. On the desktop, see the
[Linux KVM prerequisites](../apps/desktop/README.md#kvm-dependencies-on-linux-x86-64).
Keyboard and mouse input start off. Close the console when finished to release
its session.

## Enable BIOS serial redirection

In the PowerEdge 1950 BIOS Setup, open **Serial Communication**. Use the
following settings for the DRAC 5 serial console.

| BIOS field | Setting |
| --- | --- |
| Serial Communication | On with Console Redirection via COM2 |
| External Serial Connector, when present | Remote Access Device |
| Remote Terminal Type | VT100/VT220 |

Save the BIOS settings before testing. For POST output, open SOL before a
planned boot so the terminal can receive the text as it arrives. See the
[PowerEdge 1950 Owner's Manual, page 34](https://dl.dell.com/manuals/all-products/esuprt_ser_stor_net/esuprt_poweredge/poweredge-1950_owner%27s%20manual_en-us.pdf#page=34)
and [DRAC 5 User's Guide, page 66](https://usermanual.wiki/Dell/DellDrac5Version130WithOpenmanage53UsersManual118279.557915366.pdf#page=66).

## Open IPMI Serial over LAN

The controller needs IPMI over LAN with SOL enabled and permission for the
account to open it. In DRACula, **Open SOL** appears beside **Open KVM** when
the connected controller reports enabled SOL over encrypted IPMI 2.0. Docker
includes `ipmitool`. Desktop SOL requires a POSIX backend with `ipmitool` on PATH.

1. Choose **Open SOL**. The terminal starts in view-only mode.
2. Watch for text from POST or the operating system. The operating system needs
   its own serial console setup to provide a login prompt.
3. To navigate, explicitly enable keyboard input and focus the terminal. We
   verified that Down and Up move the highlight in BIOS Setup on a PowerEdge
   1950 with DRAC 5.
4. Close the terminal to release the session.

If the terminal connects but stays blank, check the BIOS redirection and wait
for fresh serial output. If DRACula reports another SOL session, close that
session in the client that opened it before retrying.
