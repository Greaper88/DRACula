# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Parse DRAC 5 XML without executing its stylesheet or embedded code."""
from xml.etree import ElementTree as ET

# Explicit projection avoids exporting sessions, service tags, MACs or credentials.
FIELDS = {
    "system": ("Description", "BiosVersion", "SystemRevision"),
    "rac": ("Name", "HardwareVersion", "FirmwareVersion"),
    "bmc": ("IpmiVersion", "BmcFirmwareVersion", "Enabled"),
    "vkvm": ("Enabled", "MaxSessions", "ActiveSessions", "KMPortNumber",
             "VideoPortNumber", "EncryptionEnabled", "PluginType"),
}

def parse_status(xml: str) -> dict[str, dict[str, str]]:
    if len(xml) > 1_000_000:
        raise ValueError("Response too large")
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise ValueError("DTD and entity declarations are not supported")
    root = ET.fromstring(xml)
    if root.tag != "drac":
        raise ValueError("Expected DRAC XML; authentication may have expired")
    result = {}
    for obj in root.findall(".//object"):
        name = obj.get("name")
        if name not in FIELDS:
            continue
        values = {p.get("name"): p.findtext("value", default="")
                  for p in obj.findall("property") if p.get("name") in FIELDS[name]}
        if values:
            result[name] = values
    if not result:
        raise ValueError("No recognized status objects; authentication may be required")
    return result
