#!/usr/bin/env python3
# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Build one executable JAR, embedding original support code and licensed Java dependencies."""
import hashlib,json,os,shutil,subprocess,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'.local/desktop';CLASSES=BUILD/'classes';DEPS=BUILD/'deps'

def download(dependency):
    file=DEPS/dependency['name']
    if not file.exists() or hashlib.sha256(file.read_bytes()).hexdigest()!=dependency['sha256']:
        with urllib.request.urlopen(dependency['url'],timeout=60) as response:
            data=response.read(12_000_001)
        if len(data)>12_000_000 or hashlib.sha256(data).hexdigest()!=dependency['sha256']:
            raise ValueError('Desktop build dependency checksum mismatch')
        file.write_bytes(data)
    return file

def main():
    DEPS.mkdir(parents=True,exist_ok=True)
    dependencies=json.loads((ROOT/'apps/desktop/bootstrap/dependencies.json').read_text())
    for dep in dependencies:download(dep)
    shutil.rmtree(CLASSES,ignore_errors=True);CLASSES.mkdir(parents=True)
    classpath=os.pathsep.join(str(DEPS/d['name']) for d in dependencies)
    subprocess.run(['javac','--release','17','-cp',classpath,'-d',str(CLASSES),*map(str,sorted((ROOT/'apps/desktop/java/dracula').glob('*.java')))],check=True)
    payload={str(p.relative_to(ROOT)):p.read_bytes() for p in sorted((ROOT/'src/dracula').glob('*.py'))}
    python_dependencies=json.loads((ROOT/'apps/desktop/bootstrap/python-dependencies.json').read_text())
    for dependency in python_dependencies:
        package=dependency['name'].split('-')[0]
        with zipfile.ZipFile(download(dependency)) as wheel:
            for name in wheel.namelist():
                if name.endswith('/'):
                    continue
                path=Path(name)
                if path.is_absolute() or '..' in path.parts or '\\' in name:
                    raise ValueError('Unsafe Python wheel entry')
                metadata=path.parts[0].startswith(package+'-') and path.parts[0].endswith('.dist-info')
                if path.parts[0]==package or metadata:
                    data=wheel.read(name)
                    payload['src/'+name]=data
                    local=BUILD/'python-deps'/path
                    local.parent.mkdir(parents=True,exist_ok=True)
                    local.write_bytes(data)
    payload.update({str(p.relative_to(ROOT)):p.read_bytes() for p in sorted((ROOT/'launcher/java').glob('*.java'))})
    for name in ('launcher/legacy-java.security','LICENSE','NOTICE','THIRD_PARTY_NOTICES.md','apps/web/THIRD_PARTY.md','licenses/GPL-3.0.txt'):payload[name]=(ROOT/name).read_bytes()
    manifest=''.join(hashlib.sha256(data).hexdigest()+' '+name+'\n' for name,data in sorted(payload.items()))
    output=BUILD/'dracula-manager.jar';temporary=output.with_suffix('.tmp');seen=set()
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as jar:
        def add(name,data):
            if name in seen:raise ValueError('Duplicate packaged resource: '+name)
            seen.add(name);info=zipfile.ZipInfo(name,(2026,10,31,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;jar.writestr(info,data)
        add('META-INF/MANIFEST.MF',b'Manifest-Version: 1.0\nMain-Class: dracula.PortableDesktop\nImplementation-Version: 0.1.4\n\n')
        for file in sorted(CLASSES.rglob('*.class')):add(str(file.relative_to(CLASSES)).replace(os.sep,'/'),file.read_bytes())
        for dep in dependencies:
            with zipfile.ZipFile(DEPS/dep['name']) as upstream:
                for name in upstream.namelist():
                    if name.endswith('/') or name=='module-info.class' or name.startswith('META-INF/versions/') or name=='META-INF/MANIFEST.MF' or name.endswith(('.SF','.RSA','.DSA')):continue
                    if name.startswith('META-INF/'):
                        if any(word in name.upper() for word in ('LICENSE','NOTICE')):add('META-INF/licenses/'+dep['name']+'/'+Path(name).name,upstream.read(name))
                        continue
                    if name in seen:raise ValueError('Duplicate dependency class: '+name)
                    add(name,upstream.read(name))
        for name in ('LICENSE','NOTICE','THIRD_PARTY_NOTICES.md'):add(name,(ROOT/name).read_bytes())
        add('META-INF/licenses/pyte/GPL-3.0.txt',payload['licenses/GPL-3.0.txt'])
        add('bootstrap/python-runtimes.properties',(ROOT/'apps/desktop/bootstrap/python-runtimes.properties').read_bytes())
        add('bootstrap/payload.manifest',manifest.encode())
        for name,data in sorted(payload.items()):add('payload/'+name,data)
    temporary.replace(output);release=ROOT/'dist/DRACula-0.1.4.jar';release.parent.mkdir(exist_ok=True);shutil.copyfile(output,release)
    print('Built self-contained executable JAR:',release.name)
if __name__=='__main__':main()
