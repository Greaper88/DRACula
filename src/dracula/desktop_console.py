# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Native-display desktop entry point using the same supervisor as the web app."""
import os,time
from .console_session import ConsoleSession

def run(host,user,password,report=lambda state:None,status_report=lambda info:None):
    if not os.getenv('DISPLAY'):raise RuntimeError('A desktop display is required for the KVM window')
    if os.getenv('DRACULA_AUTO_JAVA')=='1':
        from .launcher import setup_java
        setup_java()
    session=ConsoleSession(host,'desktop');session.attached=True;session.max_lifetime=None
    try:
        session.start({'address':host,'username':user},password,display_env=os.environ,stop_on_close=True)
        previous=None;previous_info=None
        while not session.shutdown.is_set():
            info=session.status();current=info['state']
            if current!=previous:report(current);previous=current
            if info!=previous_info:status_report(info);previous_info=info
            if current=='failed':raise RuntimeError('KVM reconnect attempts exhausted; check device availability')
            time.sleep(.5)
    finally:session.stop()
