# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Private capture geometry shared by the pixel reader and input worker."""
from dataclasses import asdict,dataclass
import json,re,secrets
from pathlib import Path

@dataclass(frozen=True)
class Viewport:
    id:str
    x:int
    y:int
    width:int
    height:int
    screen_width:int
    screen_height:int
    @classmethod
    def parse(cls,value):
        if not isinstance(value,dict) or set(value)!=set(cls.__dataclass_fields__):raise ValueError('Invalid capture geometry')
        result=cls(**value)
        if type(result.id) is not str or not re.fullmatch('[0-9a-f]{32}',result.id):raise ValueError('Invalid capture revision')
        for key in set(value)-{'id'}:
            if type(value[key]) is not int:raise ValueError('Invalid capture bounds')
        if not (1<=result.screen_width<=2048 and 1<=result.screen_height<=2048 and result.x>=0 and result.y>=0 and result.width>0 and result.height>0 and result.x+result.width<=result.screen_width and result.y+result.height<=result.screen_height):raise ValueError('Capture outside private display')
        return result
    def write(self,path):
        path=Path(path);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(asdict(self)));temp.chmod(0o600);temp.replace(path)
    @classmethod
    def read(cls,path):
        raw=Path(path).read_bytes()
        if len(raw)>1024:raise ValueError('Oversized capture geometry')
        return cls.parse(json.loads(raw))
    def point(self,x,y):return self.x+round(x*(self.width-1)/65535),self.y+round(y*(self.height-1)/65535)

def viewport(bounds,screen,previous=None):
    values=(*bounds,*screen)
    if previous and values==(previous.x,previous.y,previous.width,previous.height,previous.screen_width,previous.screen_height):return previous
    return Viewport.parse(dict(zip(Viewport.__dataclass_fields__,(secrets.token_hex(16),*values))))

def window_bounds(windows,width,height):
    """Union the viewer and visible dialogs/popups, clipped to the private screen."""
    clipped=[]
    for x,y,w,h in windows:
        left,top=max(0,x),max(0,y);right,bottom=min(width,x+w),min(height,y+h)
        if right>left and bottom>top and w>1 and h>1:clipped.append((left,top,right,bottom))
    if not clipped:return (0,0,1,1)  # Tiny hidden startup heartbeat, never the empty desktop.
    x=min(v[0] for v in clipped);y=min(v[1] for v in clipped)
    return x,y,max(v[2] for v in clipped)-x,max(v[3] for v in clipped)-y

def encode_frame(region,jpeg):
    metadata=json.dumps(asdict(region),separators=(',',':')).encode()
    return len(metadata).to_bytes(2,'big')+metadata+jpeg

def decode_frame(payload):
    if len(payload)<4:raise ValueError('Invalid capture frame')
    size=int.from_bytes(payload[:2],'big')
    if not 0<size<=1024 or size+2>=len(payload):raise ValueError('Invalid capture metadata')
    region=Viewport.parse(json.loads(payload[2:size+2]));jpeg=payload[size+2:]
    if not jpeg.startswith(b'\xff\xd8'):raise ValueError('Expected JPEG capture')
    return region,jpeg
