# Web setup

The browser dashboard uses the shared Python core and runs legacy KVM workers on
the backend. Browsers need no Java plugin or direct connection to a controller.
This preview targets **Linux AMD64**. ARM64 is not validated.

## Published image

Use `ghcr.io/greaper88/dracula:0.1.0` with the copyable configuration in the
[root README](../../README.md#web-app-published-docker-image), or
[compose.release.yaml](../../compose.release.yaml). Run the password-setup command
there before starting. No checkout or local image build is needed.

## Build and start from source

Install Docker Engine with Docker Compose, then run from the repository root:

```sh
./apps/web/start.sh
```

On first setup, enter a dashboard password of at least eight characters. There is
**no default dashboard password** and no built-in device password. The normal
image contains no Java runtime: first startup downloads the pinned private Azul
Java 8 package, verifies its SHA-256 and caches it. Internet access to the vendor
is required once. Later starts reuse the cache.

Open [http://localhost:8788](http://localhost:8788). The server list starts empty.
Choose **Manage devices → Add device**, enter your controller's name, IPv4 address,
username and password, then select it and choose **Connect device**. Nothing
connects automatically. Removing every device keeps the list empty after restart.

For a different host port:

```sh
DRACULA_PORT=8790 ./apps/web/start.sh
```

The app needs connectivity from its container to each selected management
controller. Native IPMI access uses `ipmitool`, which is included in the image.

## Access from your LAN

The default host binding is loopback. For remote browser access, use a TLS reverse
proxy on a trusted management network. Forward WebSocket upgrades and preserve
the original Host header. Set the public origin and secure-cookie option before
starting:

```sh
DRACULA_PUBLIC_ORIGIN=https://management.example.com \
DRACULA_SECURE_COOKIES=1 ./apps/web/start.sh
```

`DRACULA_BIND` selects the Docker host bind address. A proxy in another container
must have a route to DRACula; loopback publishing alone does not connect two
containers. The dashboard is single-admin and intended for a trusted LAN, not
direct exposure to the public Internet. Device certificate pinning is not yet
implemented; [security notes](../../SECURITY.md) explain the legacy TLS boundary.

## Persistent data

| Compose volume | Contents |
| --- | --- |
| `dracula-data` | Dashboard password hash and profiles with encrypted device passwords |
| `dracula-keys` | Independent device-credential encryption key |
| `dracula-cache` | Downloaded Java, viewer cache and temporary console workers |

Compose prefixes volume names with the project name. Keep the data and key
volumes together when backing up or migrating. Losing the key makes saved device
passwords unrecoverable. The browser never receives those credentials, DRAC
cookies, JNLP tickets or direct device URLs. Desktop profiles are separate.

```sh
docker compose logs -f
docker compose down
```

`down` preserves named volumes. `down --volumes` erases profiles, login setup,
encryption keys and runtime caches. Browser login sessions end when the server
restarts. Status connections expire after 15 idle minutes.

To exclude addresses from this instance, set `DRACULA_BLOCKED_HOSTS` to a
comma-separated list of IPv4 addresses before starting. There are no lab-specific
addresses or runtime write-target restrictions built into the app.

## Runtime options and image builds

Build the normal runtime-free image:

```sh
docker build --platform linux/amd64 -f apps/web/Dockerfile \
  --build-arg BUNDLE_JAVA=false -t dracula-web:0.1.0 .
```

For a private deployment that needs Java included in its image:

```sh
BUNDLE_JAVA=true ./apps/web/start.sh
```

Downloading Java during an image build is still bundling. The public release
uses the runtime-free variant. Read [third-party notices](THIRD_PARTY.md) before
redistributing a runtime-included image. Dell's proprietary viewer is always
retrieved from the user's controller and is never included in the build context.

The project image is published to GitHub Container Registry. To publish a
separate image under your own registry, replace the placeholder and tag:

```sh
docker tag dracula-web:0.1.0 YOUR_REGISTRY/dracula-web:0.1.0
docker push YOUR_REGISTRY/dracula-web:0.1.0
```

To run a published image, replace the Compose service's `image` and remove its
`build` block. Dashboard setup and persistent volumes are still required.

## Settings and power

The interface shows only capabilities reported by the current connection. DRAC
HTTP provides vendor settings and KVM. IPMI independently supplies supported BMC
status and power when HTTP is unavailable, including IPMI-only controllers.
Redfish and SOL are future work.

Supported fields stage local drafts. **Apply changes…** validates them against a
fresh controller read, then shows an exact target and old/proposed values. Only
**Confirm and apply** submits that batch. Cancel sends no configuration.
Reviews are single-use, session-bound and expire after 120 seconds. Stale values,
changed targets and replayed approvals are rejected. A partial or uncertain
result disables further editing until refreshed; writes are never automatically
retried through a second protocol or rolled back.

Power has a separate confirmation workflow. Power-on is unavailable while on;
off, cycle, reset and graceful shutdown are unavailable while off. Graceful
shutdown uses IPMI `power soft` and requires OS/ACPI support. Firmware flashing,
virtual-media mounting, log clearing and controller resets are not available.

## KVM and appearance

**Open KVM** starts a private Java/Xvfb worker and streams JPEG frames over an
authenticated same-origin WebSocket. The stream captures the viewer and its
visible menus/dialogs, fits the available browser area and preserves aspect ratio.
Source resolution changes and browser resizes refit it, including height-only
changes while the picture is static. Dark/light mode affects app chrome, not the
remote screen or vendor menus.

Input starts off. Enable **Keyboard and mouse** to control the selected machine;
**Ctrl+Alt+Shift** releases capture. Focus loss, disconnect, close and viewer
replacement turn input off and release held keys/buttons. Pointer events are
bound to the displayed capture revision; stale coordinates are rejected. The
vendor viewer retains its original menus and confirmations.

A healthy KVM connection survives the DRAC web-login timeout. On a viewer drop,
the backend rereads saved credentials and retrieves a new JNLP. The browser shows
**Reconnecting**, attempt count and retry delay. Closing the console cancels
retries and closes its own authenticated device session. DRACula does not evict
other viewers or automatically send wake keys.

Limits: up to five changed frames per second, a five-second static heartbeat,
two workers per backend, one per device, a 30-minute console lifetime and a
60-second limit for an unattached worker. Retries are bounded; refresh credentials
or close/reopen the console after a terminal failure. Physical input currently
uses the private display's US keyboard layout. A blanked remote screen can show
**No Signal** without indicating a network failure.

## Development

See [release validation](../../docs/release-validation.md) for offline checks,
fresh-container smoke tests and the limits of live resolution testing.
