# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from dracula.ipmi import IpmiAdapter, IpmiError, TRANSPORTS
from dracula.sol import SolSession


def synthetic_adapter(received):
    # The real worker sees a line-buffered terminal, a serial stream and stdin EOF.
    script = """
import os, sys
with open(sys.argv[1], 'wb', buffering=0) as recorded:
    print('[SOL Session operational. Use ^]? for help]', flush=True)
    os.write(1, b'old text\\r\\x1b[2Kserial login:')
    while data := os.read(0, 512):
        recorded.write(data)
        os.write(1, b'\\r\\x1b[2Kinput received')
with open(sys.argv[1]+'.closed', 'w') as closed:
    closed.write('EOF')
"""
    adapter = Mock()
    adapter.command.return_value = ([sys.executable, '-u', '-c', script, str(received)], os.environ.copy())
    return adapter


class SolTests(unittest.TestCase):
    def test_sol_detection_uses_only_encrypted_rmcp_and_preserves_existing_transport(self):
        adapter = IpmiAdapter('192.0.2.1', 'operator', 'synthetic')
        adapter.transport, adapter.privilege = TRANSPORTS[-1], 'ADMINISTRATOR'
        with patch('dracula.ipmi.shutil.which', return_value='/synthetic/ipmitool'), \
             patch.object(adapter, '_run', side_effect=[IpmiError(), 'Enabled : true']) as command:
            self.assertEqual(adapter.sol_access(), (TRANSPORTS[1], 'ADMINISTRATOR'))
            self.assertEqual([call.args[1] for call in command.call_args_list], list(TRANSPORTS[:2]))
            self.assertTrue(all(call.args[0] == ('sol', 'info') for call in command.call_args_list))
            self.assertEqual(adapter.transport, TRANSPORTS[-1])
        with patch('dracula.ipmi.shutil.which', return_value='/synthetic/ipmitool'), \
             patch.object(adapter, '_run', return_value='Enabled : false') as command:
            self.assertIsNone(adapter.sol_access())
            command.assert_called_once()

    def wait_for(self, worker, expected):
        until = time.monotonic() + 5
        while time.monotonic() < until:
            status = worker.snapshot()
            if expected in status['text']:
                return status
            if status['state'] in ('failed', 'closed'):
                self.fail(status['error'] or 'SOL closed unexpectedly')
            time.sleep(.02)
        self.fail('Serial text did not arrive')

    def test_serial_rendering_input_gate_and_owned_session_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            received = Path(directory)/'received'
            adapter = synthetic_adapter(received)
            worker = SolSession('synthetic', 'test')
            try:
                worker.start(adapter, (TRANSPORTS[1], 'ADMINISTRATOR'))
                status = self.wait_for(worker, 'serial login:')
                self.assertEqual(status['state'], 'connected')
                self.assertNotIn('old text', status['text'])
                self.assertFalse(status['input_enabled'])
                worker.message({'type':'input', 'data':'blocked\r'})
                self.assertEqual(received.read_bytes(), b'')
                worker.message({'type':'enable', 'enabled':True})
                with self.assertRaises(ValueError):
                    worker.message({'type':'input', 'data':'\x1dB'})
                worker.message({'type':'input', 'data':'allowed\r'})
                self.wait_for(worker, 'input received')
                worker.message({'type':'enable', 'enabled':False})
                worker.message({'type':'input', 'data':'also blocked'})
            finally:
                worker.stop()
            self.assertEqual(received.read_bytes(), b'allowed\r')
            self.assertEqual(received.with_suffix('.closed').read_text(), 'EOF')
            self.assertTrue(worker.expired())
            self.assertEqual(worker.process.returncode, 0)
            adapter.command.assert_called_once_with(('-e', '\x1d', 'sol', 'activate'), TRANSPORTS[1], 'ADMINISTRATOR')

    def test_failed_activation_never_becomes_connected(self):
        adapter = Mock()
        script = "import sys; print('SOL payload already active on another session', file=sys.stderr); sys.exit(1)"
        adapter.command.return_value = ([sys.executable, '-c', script], os.environ.copy())
        worker = SolSession('synthetic', 'test')
        worker.start(adapter, (TRANSPORTS[1], 'ADMINISTRATOR'))
        try:
            self.assertTrue(worker.done.wait(5))
            self.assertEqual(worker.snapshot()['state'], 'failed')
            self.assertIn('Another SOL session', worker.snapshot()['error'])
            self.assertFalse(worker.snapshot()['input_enabled'])
        finally:
            worker.stop()
