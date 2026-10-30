# Recovered historical DRACula launcher

Source: archived chat **Flatpak Browser DRAC5 Compatibility**,
chat ID `69c5f474-30dc-832a-85b2-57282dd3e863`.
Recovered October 29, 2026. The visible source turns are from March 2026.
The available history contains the later Java launcher and client proposals;
it initially did not include the original shell script or successful test output.
The owner subsequently located a historical script preview. A preserved copy is
[launch-drac-direct.sh.txt](history/launch-drac-direct.sh.txt). The owner said their
working version differed slightly to match earlier iterations. This reference
was read, not executed: it does not enforce the current read-only restriction.
Its shell-sourced generated values and unrestricted archive extraction should
not be carried into the new launcher.

## Useful leads

The historical assistant described the Linux launch path as previously validated.
That is a historical claim, not independent verification in this repository.

- Main class: `com.avocent.drac5.kvm.Main`.
- Viewer archive: `avctDRAC5Viewer.jar`.
- Linux native archive: `avctKVMIOLinux.jar`, expected `libavctKVMIO.so`.
- Proposed Windows archive: `avctKVMIOWin32.jar`, expected `avctKVMIO.dll`;
  Windows support was explicitly untested.
- Proposed device assets: `/plugins/vkvm/avctDRAC5Viewer.jar` and
  `/plugins/vkvm/avctKVMIOLinux.jar`; confirm against the device before fetching.
- Earlier launcher searched `~/.cache/icedtea-web/cache` for these archives.
- Java 8 was the proposed application target. Exact Java vendor, update level and
  runtime/native CPU architecture were not established in the recovered turns.
- Proposed token flow visited `/cgi-bin/webcgi/vkvmload?cat=C00&tab=T05&id=P07`
  then `/cgi-bin/webcgi/vkvm?state=0`, extracting `vKvmSessionId`.
  These are investigation leads, not an approved read-only request sequence.

The proposed viewer arguments were `title=DRAC5 vKVM`, `ip=<device>`,
`user=<fresh KVM token>`, `passwd=`, `kmport=5900`, `vport=5901`,
`apcp=0`, `version=1`, and `sslv3=1`. Argument meanings and view-only behavior
still need verification. In particular, do not interpret `apcp=0` as an input
safety switch. The historical code hardcoded ports; use actual device settings.
Never record a real token in logs or launch-plan artifacts.

The user stated that an expired web session redirects to
`/cgi-bin/webcgi/login`. Preserve redirect visibility and isolate cookies per
machine, with bounded reauthentication rather than an unlimited retry loop.

## Do not copy the old prototype wholesale

The historical manager was explicitly reported as incomplete: power status and
power actions were unfinished, Java bootstrapping was external, cached JARs were
assumed present, and cross-platform operation had not been demonstrated.
The proposed client installed process-global trust-all TLS and cookie settings.
The archive extraction example lacked path containment checks. Those approaches
need replacement before integration into a shared multi-machine backend.

No recovered code was executed and no live KVM connection was opened during
this historical review. Next: inspect viewer assets and runtime architecture,
then determine how to enforce view-only console access in the backend worker.
