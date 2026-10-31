# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import tempfile,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from dracula.web_worker import ConsoleWorker,RETRY_DELAYS

class ConsoleReconnectTests(unittest.TestCase):
    def setUp(self):
        self.worker=ConsoleWorker('test','owner');self.work=tempfile.TemporaryDirectory()
        self.worker.directory=self.work;self.worker.env={};self.worker.log=Mock()
        self.worker._terminate=Mock()
    def tearDown(self):self.work.cleanup()
    def state(self,value):(Path(self.work.name)/'viewer-state').write_text(value)
    def process(self,code=None):
        proc=Mock();proc.poll.return_value=code;return proc
    def test_healthy_console_does_not_reauthenticate_after_web_timeout(self):
        w=self.worker;w.viewer=self.process();w.launched=0;self.state('connected')
        with patch.object(w,'_launch') as launch:
            w._tick(100);w._tick(2000)
            launch.assert_not_called();w._terminate.assert_not_called()
            self.assertEqual(w.state,'connected')
    def test_exited_process_backs_off_then_launches_again(self):
        w=self.worker;w.viewer=self.process(1)
        with patch.object(w,'_launch') as launch:
            w._tick(10);self.assertEqual(w.state,'reconnecting')
            self.assertFalse(w.expired())
            w._tick(11);launch.assert_not_called()
            w._tick(12);launch.assert_called_once()
    def test_modal_error_signal_restarts_even_if_java_is_still_alive(self):
        w=self.worker;w.viewer=self.process();self.state('disconnected')
        w._tick(10);w._terminate.assert_not_called();self.assertEqual(w.state,'reconnecting')
        w._tick(39);w._terminate.assert_not_called()
        w._tick(40);w._terminate.assert_called_once();self.assertIsNone(w.viewer)
    def test_each_launch_loads_current_saved_credentials_and_clears_stale_state(self):
        w=self.worker
        w.credentials=Mock(side_effect=[({'address':'192.0.2.252','username':'first'},'old'),({'address':'192.0.2.252','username':'second'},'new')])
        with patch('dracula.console_session.subprocess.Popen',side_effect=[self.process(),self.process()]) as spawn:
            self.state('connected');w._launch()
            self.assertFalse((Path(self.work.name)/'viewer-state').exists())
            self.state('disconnected');w._launch()
            self.assertEqual(w.generation,2);self.assertEqual(w.credentials.call_count,2)
            self.assertEqual(spawn.call_args_list[0].args[0][-1],'--console')
            self.assertEqual(spawn.call_count,2)
            self.assertFalse((Path(self.work.name)/'viewer-state').exists())
    def test_backoff_is_bounded_and_stop_prevents_relaunch(self):
        w=self.worker;w.failures=len(RETRY_DELAYS);w._retry(10)
        self.assertEqual(w.state,'failed')
        with patch.object(w,'_launch') as launch:w._tick(1000);launch.assert_not_called()
        w.stop();self.assertIsNone(w.credentials)
        with patch.object(w,'_launch') as launch:w._tick(2000);launch.assert_not_called()
    def test_startup_timeout_retries_but_static_connected_screen_does_not(self):
        w=self.worker;w.viewer=self.process();w.launched=1
        w._tick(77);self.assertEqual(w.state,'reconnecting')
    def test_credential_reload_failure_is_bounded_and_not_exposed(self):
        w=self.worker;w.credentials=Mock(side_effect=RuntimeError('synthetic-secret'))
        w._tick(10)
        self.assertEqual(w.state,'reconnecting')
        self.assertNotIn('synthetic-secret',str(w.status()))
        self.assertEqual(w.failures,1)
    def test_clean_launcher_exit_during_grace_retries_without_killing_it(self):
        w=self.worker;proc=self.process();w.viewer=proc;self.state('disconnected:exit')
        w._tick(10);self.assertEqual(w.state,'reconnecting')
        proc.poll.return_value=0
        w._tick(12);self.assertIsNone(w.viewer)
        self.assertEqual(w.failures,1)
    def test_stop_allows_wrapper_logout_before_force_killing_group(self):
        from dracula.console_session import ConsoleSession
        process=self.process()
        with patch('dracula.console_session.os.killpg') as kill:
            ConsoleSession._terminate(process)
            process.terminate.assert_called_once()
            process.wait.assert_called_once_with(timeout=30)
            kill.assert_not_called()
    def test_hung_logout_is_force_killed_only_after_cleanup_deadline(self):
        import signal,subprocess
        from dracula.console_session import ConsoleSession
        process=self.process();process.pid=1234
        process.wait.side_effect=[subprocess.TimeoutExpired('test',30),0]
        with patch('dracula.console_session.os.killpg') as kill:
            ConsoleSession._terminate(process)
            kill.assert_called_once_with(1234,signal.SIGKILL)
            self.assertEqual(process.wait.call_count,2)
