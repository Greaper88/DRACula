# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Initialize local web authentication and an independent credential encryption key."""
import getpass,hashlib,json,os,secrets,sys
from pathlib import Path
from cryptography.fernet import Fernet

def paths():
    return Path(os.getenv('DRACULA_DATA','/data')),Path(os.getenv('DRACULA_KEYS','/keys'))

def main():
    os.umask(0o077);data,keys=paths();data.mkdir(parents=True,exist_ok=True);keys.mkdir(parents=True,exist_ok=True)
    auth=data/'auth.json'
    if '--check' in sys.argv:raise SystemExit(0 if auth.exists() else 1)
    if auth.exists():print('Web login already configured.');return
    password=getpass.getpass('Create dashboard password (at least 8 characters): ') if sys.stdin.isatty() else sys.stdin.readline(4097).rstrip('\n')
    if not 8<=len(password)<=4096:raise SystemExit('Use a web login password between 8 and 4096 characters.')
    salt=secrets.token_bytes(16)
    value={'salt':salt.hex(),'hash':hashlib.pbkdf2_hmac('sha256',password.encode(),salt,250_000).hex()}
    auth.write_text(json.dumps(value));auth.chmod(0o600)
    key=keys/'credentials.key'
    if not key.exists():key.write_bytes(Fernet.generate_key());key.chmod(0o600)
    print('Web login configured. Device passwords will be encrypted separately.')
if __name__=='__main__':main()
