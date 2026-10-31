# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import io,base64,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from dracula.console_session import ConsoleSession
from dracula.web_worker import ConsoleWorker

class DesktopConsoleTests(unittest.TestCase):
    def test_web_and_desktop_use_identical_retry_loop(self):
        self.assertIs(ConsoleWorker._tick,ConsoleSession._tick)
        self.assertIs(ConsoleWorker._launch,ConsoleSession._launch)
    def test_desktop_normal_window_close_stops_instead_of_reopening(self):
        session=ConsoleSession('test','desktop');session.stop_on_close=True
        session.viewer=Mock();session.viewer.poll.return_value=0;session.viewer.returncode=0
        with tempfile.TemporaryDirectory() as directory:
            session.directory=Mock(name=directory);session.directory.name=directory
            with patch.object(session,'_launch') as launch:
                session._tick(time.monotonic());session._tick(time.monotonic()+100)
                self.assertEqual(session.state,'closed');self.assertTrue(session.shutdown.is_set())
                launch.assert_not_called()
    def test_desktop_error_exit_uses_same_fresh_launcher_retry(self):
        session=ConsoleSession('test','desktop');session.stop_on_close=True
        session.viewer=Mock();session.viewer.poll.return_value=1;session.viewer.returncode=1
        with tempfile.TemporaryDirectory() as directory:
            session.directory=Mock();session.directory.name=directory
            session._tick(10);self.assertEqual(session.state,'reconnecting')
            with patch.object(session,'_launch') as launch:session._tick(12);launch.assert_called_once()
    def test_native_display_is_preserved_without_spawning_xvfb(self):
        from dracula.launcher import JAVA_NAME
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory);java=cache/'runtime32'/JAVA_NAME/'bin/java';java.parent.mkdir(parents=True);java.touch()
            session=ConsoleSession('test','desktop');session.attached=True;session.max_lifetime=None
            with patch('dracula.console_session.CACHE',cache),patch('dracula.console_session.threading.Thread') as thread,patch('dracula.console_session.subprocess.Popen') as process:
                session.start({'address':'192.0.2.252','username':'root'},'synthetic',display_env={'DISPLAY':':77','XAUTHORITY':'/private/auth'},stop_on_close=True)
                self.assertEqual(session.env['DISPLAY'],':77');self.assertEqual(session.env['XAUTHORITY'],'/private/auth')
                process.assert_not_called();self.assertTrue(session.stop_on_close)
                session.stop();self.assertIsNone(session.credentials)
    def test_managed_bridge_dispatches_saved_credentials_to_shared_session(self):
        from dracula import manager_bridge
        data=''.join(base64.b64encode(s.encode()).decode()+'\n' for s in ('192.0.2.252','root','synthetic'))
        with patch('sys.argv',['bridge','--console-managed']),patch('sys.stdin',io.StringIO(data)),patch('dracula.manager_bridge.signal.signal'),patch('dracula.desktop_console.run') as run:
            manager_bridge.main();self.assertEqual(run.call_args.args[:3],('192.0.2.252','root','synthetic'))
    def test_user_close_shows_closing_and_never_queues_reconnect(self):
        session=ConsoleSession('test','desktop');session.stop_on_close=True
        session.viewer=Mock();session.viewer.poll.return_value=None
        with tempfile.TemporaryDirectory() as directory:
            session.directory=Mock();session.directory.name=directory
            (Path(directory)/'viewer-state').write_text('closed')
            with patch.object(session,'_launch') as launch,patch.object(session,'_terminate') as terminate:
                session._tick(10);self.assertEqual(session.state,'closing')
                self.assertFalse(session.shutdown.is_set());terminate.assert_not_called()
                session.viewer.poll.return_value=0;session._tick(11)
                self.assertEqual(session.state,'closed');self.assertTrue(session.shutdown.is_set());launch.assert_not_called()
    def test_retry_status_has_safe_countdown(self):
        session=ConsoleSession('test','owner');session.state='reconnecting';session.next_retry=110;session.failures=2
        with patch('dracula.console_session.time.monotonic',return_value=100):
            self.assertEqual(session.status()['retry_in'],10);self.assertEqual(session.status()['attempt'],2)
