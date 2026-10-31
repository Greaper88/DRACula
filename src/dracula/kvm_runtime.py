# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Check native Java graphics locally, before allocating any controller session."""
import hashlib
import io
import os
import re
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

XTST_URL = 'https://deb.debian.org/debian/pool/main/libx/libxtst/libxtst6_1.2.3-1.1_i386.deb'
XTST_SHA256 = 'd70b41ff8ccac0ab02eb53817189af9ac0397c9bbcc2e4afd04896000e771f5b'
XTST_FILES = {
    'usr/lib/i386-linux-gnu/libXtst.so.6.1.0': 'e8196d8cb708b7b450cbb18a8c915921370420a59d41404ff1c5a9a84d394885',
    'usr/share/doc/libxtst6/copyright': '304f78731e1e0e78132fbba4e1909c8642878a3b8c4837b36cb2d38891bf2204',
}

def viewer_environment(base, cache):
    env = dict(base)
    # This path is private to the device-facing child, never the host Java.
    env['LD_LIBRARY_PATH'] = str(cache/'lib32/usr/lib/i386-linux-gnu')
    for name in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS'):
        env.pop(name, None)
    return env

def _package_files(package):
    """Read only pinned regular files; never extract package paths or run scripts."""
    if len(package) > 100_000 or hashlib.sha256(package).hexdigest() != XTST_SHA256:
        raise ValueError('KVM library download failed checksum verification')
    if package[:8] != b'!<arch>\n':
        raise ValueError('Invalid KVM library package')
    offset = 8
    while offset < len(package):
        header = package[offset:offset+60]
        if len(header) != 60 or header[58:] != b'`\n':
            raise ValueError('Invalid KVM library package header')
        size = int(header[48:58])
        if size < 0 or offset+60+size > len(package):
            raise ValueError('Truncated KVM library package')
        payload = package[offset+60:offset+60+size]
        offset += 60+size+(size % 2)
        if header[:16].strip().rstrip(b'/') != b'data.tar.xz':
            continue
        files = {}
        with tarfile.open(fileobj=io.BytesIO(payload), mode='r:xz') as archive:
            for member in archive:
                name = member.name.removeprefix('./')
                if name not in XTST_FILES:
                    continue
                if not member.isfile() or member.size > 100_000 or name in files:
                    raise ValueError('Invalid KVM library member')
                data = archive.extractfile(member).read(100_001)
                if hashlib.sha256(data).hexdigest() != XTST_FILES[name]:
                    raise ValueError('Invalid KVM library member checksum')
                files[name] = data
        if files.keys() != XTST_FILES.keys():
            raise ValueError('Incomplete KVM library package')
        return files
    raise ValueError('Missing KVM library package data')

def prepare_xtst(cache):
    root = cache/'lib32'
    with urllib.request.urlopen(XTST_URL, timeout=45) as response:
        files = _package_files(response.read(100_001))
    library = files['usr/lib/i386-linux-gnu/libXtst.so.6.1.0']
    files['usr/lib/i386-linux-gnu/libXtst.so.6'] = library
    # Retain the upstream license before making the library available.
    for name in sorted(files, key=lambda n: 'copyright' not in n):
        target = root/name
        target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(files[name])
        try:
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

def check_display(java, root, cache, auto_download=False):
    """Load real AWT/fonts on this display; no device login or remote input."""
    env = viewer_environment(os.environ, cache)
    try:
        with tempfile.TemporaryDirectory(prefix='graphics-check-', dir=cache) as work:
            compiled = subprocess.run([str(java.parent/'javac'), '-d', work,
                str(root/'launcher/java/DesktopRuntimeProbe.java')], env=env,
                capture_output=True, timeout=30)
            if compiled.returncode:
                raise RuntimeError('The private KVM Java compiler could not start. Check the 32-bit Linux prerequisites in the desktop setup guide.')
            command = [str(java), '-Djava.awt.headless=false', '-cp', work, 'dracula.DesktopRuntimeProbe']
            result = subprocess.run(command, env=env, capture_output=True, timeout=25)
            output = (result.stdout+result.stderr).decode(errors='replace')
            if result.returncode and auto_download and 'libXtst.so.6' in output:
                try:
                    prepare_xtst(cache)
                except (OSError, ValueError) as error:
                    raise RuntimeError('KVM needs 32-bit libXtst.so.6. Its private download failed; check internet access or install libxtst6:i386 using the desktop setup guide.') from error
                result = subprocess.run(command, env=env, capture_output=True, timeout=25)
                output = (result.stdout+result.stderr).decode(errors='replace')
            if result.returncode:
                missing = re.search(r'(lib[A-Za-z0-9_+.-]+\.so(?:\.[0-9]+)*): cannot open shared object', output)
                if missing:
                    raise RuntimeError('KVM needs the 32-bit library '+missing[1]+'. Install the Linux prerequisites in the desktop setup guide, then open KVM again.')
                raise RuntimeError('KVM Java could not open local graphics. Check your desktop display and the 32-bit Linux prerequisites in the desktop setup guide.')
    except FileNotFoundError as error:
        raise RuntimeError('KVM Java needs the 32-bit Linux loader and libraries. Install the prerequisites in the desktop setup guide, then open KVM again.') from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('The local KVM graphics check timed out. Check your desktop display, then open KVM again.') from error
