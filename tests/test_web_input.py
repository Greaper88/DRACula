# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from dracula.web_input import Injector,validate,StaleFrame
from dracula.console_geometry import Viewport
from dracula.console_session import ConsoleSession

class InputTests(unittest.TestCase):
    def test_schema_rejects_arbitrary_commands_keys_coordinates_and_types(self):
        for message in ({'type':'power','action':'off'},{'type':'key','code':'Enter','down':1},{'type':'key','code':'unknown','down':True},{'type':'pointer','action':'move','x':-1,'y':0},{'type':'pointer','action':'button','x':0,'y':0,'button':3,'down':True},{'type':'input-control','enabled':'true'},{'type':'release','host':'192.0.2.99'}):
            with self.assertRaises(ValueError):validate({'generation':1,**({'frame':'a'*32} if message.get('type')=='pointer' else {}),**message})
        for generation in (True,0,-1,'1'):
            with self.assertRaises(ValueError):validate({'type':'release','generation':generation})
        self.assertEqual(validate({'type':'key','code':'NumLock','down':True,'generation':1})['code'],'NumLock')
    def test_stale_generation_disconnected_and_nonprivate_display_cannot_inject(self):
        s=ConsoleSession('test','owner');s.state='connected';s.generation=2
        with patch('dracula.console_session.subprocess.Popen') as spawn:
            self.assertFalse(s.input_message({'type':'input-control','enabled':True,'generation':1})['enabled']);spawn.assert_not_called()
            s.state='reconnecting';self.assertFalse(s.input_message({'type':'key','code':'Enter','down':True,'generation':2})['enabled']);spawn.assert_not_called()
            s.state='connected'
            with self.assertRaises(ValueError):s.input_message({'type':'input-control','enabled':True,'generation':2})
            spawn.assert_not_called()
    def injector(self):
        i=Injector('/private/endpoint');i.connection=Mock();i.X=Mock(KeyPress=2,KeyRelease=3,MotionNotify=6,ButtonPress=4,ButtonRelease=5);i.XK=Mock();i.XK.string_to_keysym.return_value=123;i.connection.keysym_to_keycode.return_value=38;i.connection.screen().root.get_geometry.return_value=Mock(width=1280,height=1024)
        def control(op):i.enabled=op not in ('disable','release');return i.enabled
        i.control=Mock(side_effect=control);i.viewport=Mock(return_value=Viewport('a'*32,0,0,1280,1024,2048,1536));return i
    def test_disable_releases_all_held_modifiers_and_buttons(self):
        i=self.injector();i.handle({'type':'key','code':'ControlLeft','down':True,'generation':1});i.handle({'type':'pointer','frame':'a'*32,'action':'button','x':65535,'y':0,'button':0,'down':True,'generation':1});i.handle({'type':'release','generation':1})
        calls=i.connection.xtest_fake_input.call_args_list
        self.assertTrue(any(c.args==(3,38) for c in calls));self.assertTrue(any(c.args==(5,1) for c in calls));self.assertFalse(i.enabled);self.assertFalse(i.keys);self.assertFalse(i.buttons)
        self.assertTrue(any(c.kwargs=={'x':1279,'y':0} for c in calls));i.control.assert_called_with('disable')
    def test_gate_disabled_never_generates_x_events_and_duplicates_do_not_stick(self):
        i=self.injector();i.control.side_effect=lambda op:False;i.handle({'type':'key','code':'Enter','down':True,'generation':1});i.connection.xtest_fake_input.assert_not_called()
        i=self.injector()
        for _ in range(2):i.handle({'type':'key','code':'KeyA','down':True,'generation':1})
        self.assertEqual(i.connection.xtest_fake_input.call_count,1)
        connection=i.connection;i.close();self.assertFalse(i.keys);connection.close.assert_called_once()
    def test_server_status_reflects_gate_and_resets_on_reconnect(self):
        s=ConsoleSession('test','owner')
        with tempfile.TemporaryDirectory() as directory:
            s.input_state=Path(directory)/'state';s.input_state.write_text('enabled');s.state='connected';self.assertTrue(s.status()['input_enabled']);s.state='reconnecting';self.assertFalse(s.status()['input_enabled'])

    def test_cropped_pointer_maps_to_private_window_offset_and_rejects_old_images(self):
        i=self.injector();i.viewport.return_value=Viewport('b'*32,100,80,720,424,2048,1536)
        i.handle({'type':'pointer','frame':'b'*32,'action':'move','x':65535,'y':65535,'generation':1})
        self.assertEqual(i.connection.xtest_fake_input.call_args.kwargs,{'x':819,'y':503})
        i.connection.xtest_fake_input.reset_mock()
        with self.assertRaises(StaleFrame):i.handle({'type':'pointer','frame':'a'*32,'action':'button','button':0,'down':True,'x':0,'y':0,'generation':1})
        i.connection.xtest_fake_input.assert_not_called();i.close();self.assertFalse(i.enabled)
