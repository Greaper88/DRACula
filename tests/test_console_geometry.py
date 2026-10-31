# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import tempfile,unittest
from pathlib import Path
from dataclasses import replace
from dracula.console_geometry import Viewport,viewport,window_bounds,encode_frame,decode_frame

class GeometryTests(unittest.TestCase):
    def test_only_visible_window_area_is_captured_with_popup_union_and_clipping(self):
        self.assertEqual(window_bounds([(100,80,720,424)],2048,1536),(100,80,720,424))
        self.assertEqual(window_bounds([(100,80,720,424),(750,460,190,300)],2048,1536),(100,80,840,680))
        self.assertEqual(window_bounds([(-10,-20,200,100),(1,1,1,1)],1280,1024),(0,0,190,80))
        self.assertEqual(window_bounds([],1280,1024),(0,0,1,1))
    def test_geometry_revision_is_stable_for_pixels_but_changes_when_window_moves(self):
        original=viewport((100,80,720,424),(2048,1536))
        self.assertIs(viewport((100,80,720,424),(2048,1536),original),original)
        moved=viewport((101,80,720,424),(2048,1536),original)
        self.assertNotEqual(moved.id,original.id)
        self.assertEqual(original.point(0,0),(100,80));self.assertEqual(original.point(65535,65535),(819,503))
    def test_private_geometry_file_and_framing_roundtrip(self):
        region=viewport((100,80,720,424),(2048,1536));jpeg=b'\xff\xd8synthetic-image\xff\xd9'
        self.assertEqual(decode_frame(encode_frame(region,jpeg)),(region,jpeg))
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'region.json';region.write(file);self.assertEqual(file.stat().st_mode&0o777,0o600);self.assertEqual(Viewport.read(file),region)
    def test_untrusted_or_broken_frame_bounds_fail_closed(self):
        from dataclasses import asdict
        base=asdict(viewport((0,0,720,424),(2048,1536)))
        for change in ({'x':-1},{'width':3000},{'screen_height':4096},{'height':True},{'id':'bad'},{'x':1900}):
            with self.assertRaises(ValueError):Viewport.parse(base|change)
        for payload in (b'',b'\x00\x00xx',b'\xff\xffx',encode_frame(Viewport.parse(base),b'not-jpeg')):
            with self.assertRaises(ValueError):decode_frame(payload)
    def test_display_resolution_changes_replace_capture_bounds_and_pointer_mapping(self):
        region=None;ids=[]
        for width,height in ((720,424),(1024,792),(1280,1048),(720,424)):
            bounds=window_bounds([(0,0,width,height)],2048,1536)
            region=viewport(bounds,(2048,1536),region);ids.append(region.id)
            self.assertEqual((region.width,region.height),(width,height))
            self.assertEqual(region.point(65535,65535),(width-1,height-1))
        self.assertEqual(len(set(ids)),len(ids))
