#!/usr/bin/env python3
# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Package only nonignored source files; runtime caches and credentials stay out."""
import gzip,hashlib,io,subprocess,tarfile,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    version=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['version'];out=ROOT/'dist';out.mkdir(exist_ok=True)
    files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).split(b'\0')
    archive=out/f'DRACula-{version}-source.tar.gz'
    with archive.open('wb') as file,gzip.GzipFile(fileobj=file,mode='wb',mtime=0) as compressed,tarfile.open(fileobj=compressed,mode='w') as tar:
        for raw in sorted(set(files)):
            if not raw:continue
            name=raw.decode();path=ROOT/name
            if not path.is_file():continue
            if path.is_symlink() or any(part in ('.git','.local','.venv','dist','__pycache__') for part in Path(name).parts) or path.suffix in ('.jar','.class','.jnlp','.vault','.key','.pem'):raise ValueError('Private/binary file in source candidates: '+name)
            data=path.read_bytes();entry=tarfile.TarInfo(f'DRACula-{version}/'+name);entry.size=len(data);entry.mode=0o755 if path.stat().st_mode&0o111 else 0o644;entry.mtime=0;tar.addfile(entry,io.BytesIO(data))
    artifacts=[out/f'DRACula-{version}.jar',archive]
    (out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in artifacts))
    print('Prepared source archive, standalone JAR and SHA256SUMS; nothing published.')
if __name__=='__main__':main()
