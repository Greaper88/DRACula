# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""First-launch runtime bootstrap for the optional runtime-free image variant."""
import os,sys
from .launcher import CACHE,setup_java

def main():
    os.umask(0o077);CACHE.mkdir(mode=0o700,parents=True,exist_ok=True)
    setup_java()
    os.execv(sys.executable,[sys.executable,'-m','uvicorn','dracula.web_api:app','--host','0.0.0.0','--port','8080','--no-access-log'])
if __name__=='__main__':main()
