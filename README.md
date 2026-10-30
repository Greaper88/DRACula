# DRACula

Modern management for legacy Dell DRAC controllers, starting with DRAC 5.

## Layout

- `src/dracula`: shared device models, status parsing and future adapters.
- `apps/desktop`: future portable Windows, Linux and macOS application.
- `apps/web`: future browser interface and management backend.
- `docs`: architecture, hardware evidence and KVM investigation.

Both products use one shared core on the same development branch. This is an
initial scaffold and working offline status parser, not a finished manager.
A Linux view-only console launcher now downloads a private Java runtime and
opens the fingerprinted Dell viewer; see [launcher instructions](launcher/README.md).
No hardware-changing commands or browser console bridge are implemented.

## Run the current tooling

Python 3.12 or newer; no runtime dependencies for the initial parser.

```sh
PYTHONPATH=src python3 -m dracula.cli /path/to/saved-status.xml
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The parser exports an explicit selection of status fields and rejects login
responses rather than reporting a successful status. Do not commit raw captures.

See [architecture](docs/architecture.md), [hardware findings](docs/drac5-findings.md)
and [next steps](docs/roadmap.md).
