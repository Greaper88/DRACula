# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Capture only this private display's visible viewer windows and popups."""
import hashlib,io,os,struct,sys,time
from Xlib import X,display,error
from PIL import Image
from .console_geometry import viewport,window_bounds,encode_frame

def main():
    connection=display.Display();root=connection.screen().root
    previous=None;last=0;region=None
    while True:
        geometry=root.get_geometry()
        if not (0<geometry.width<=2048 and 0<geometry.height<=2048):raise ValueError('Display too large')
        windows=[]
        for window in root.query_tree().children:
            try:
                if window.get_attributes().map_state!=X.IsViewable:continue
                g=window.get_geometry();windows.append((g.x,g.y,g.width+2*g.border_width,g.height+2*g.border_width))
            except error.XError:continue  # A transient popup may close between queries.
        bounds=window_bounds(windows,geometry.width,geometry.height)
        current=viewport(bounds,(geometry.width,geometry.height),region)
        if current is not region:
            current.write(os.environ['DRACULA_FRAME_REGION']);region=current
        frame=root.get_image(*bounds,X.ZPixmap,0xffffffff)
        if frame is None:raise ValueError('Display is unavailable')
        digest=hashlib.sha256(region.id.encode()+frame.data).digest();now=time.monotonic()
        if digest!=previous or now-last>5:
            image=Image.frombytes('RGB',(region.width,region.height),frame.data,'raw','BGRX')
            target=io.BytesIO();image.save(target,format='JPEG',quality=85)
            data=encode_frame(region,target.getvalue());sys.stdout.buffer.write(struct.pack('>I',len(data))+data);sys.stdout.buffer.flush()
            previous=digest;last=now
        time.sleep(.2)
if __name__=='__main__':main()
