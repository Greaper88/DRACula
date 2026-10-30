"""Offline inspection entry point; no device-changing commands are exposed."""
import argparse
import json
from pathlib import Path
from .drac5 import parse_status

def main():
    parser = argparse.ArgumentParser(description="DRACula read-only tooling")
    parser.add_argument("xml", type=Path, help="Saved DRAC sysinfo or vkvmconfig XML")
    args = parser.parse_args()
    try:
        print(json.dumps(parse_status(args.xml.read_text()), indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Cannot inspect status: {exc}\n")

if __name__ == "__main__":
    main()
