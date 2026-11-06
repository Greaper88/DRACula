# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
"""Own one encrypted IPMI SOL session and render its terminal in memory."""
import errno
import importlib.util
import os
import select
import subprocess
import threading
import time


def available():
    return os.name == 'posix' and importlib.util.find_spec('pyte') is not None


class SolSession:
    kind = 'sol'
    escape = '\x1d'

    def __init__(self, device_id, owner):
        self.device_id = device_id
        self.owner = owner
        self.state = 'starting'
        self.error = ''
        self.input_enabled = False
        self.lock = threading.Lock()
        self.shutdown = threading.Event()
        self.done = threading.Event()
        self.thread = None
        self.created = time.monotonic()
        self.screen = None

    def start(self, adapter, access):
        import pty
        import tty
        import pyte

        self.screen = pyte.Screen(80, 25)
        stream = pyte.ByteStream(self.screen)
        transport, privilege = access
        command, env = adapter.command(('-e', self.escape, 'sol', 'activate'), transport, privilege)
        master, slave = pty.openpty()
        try:
            # A terminal on stdout flushes ipmitool's activation banner immediately.
            # A pipe on stdin lets EOF release our payload without sending serial data.
            tty.setraw(slave)
            with self.lock:
                if self.shutdown.is_set():
                    raise RuntimeError('SOL was closed before activation.')
                self.process = subprocess.Popen(command, env=env, stdin=subprocess.PIPE, stdout=slave,
                                                stderr=subprocess.PIPE, start_new_session=True)
                self.thread = threading.Thread(target=self._read, args=(master, stream), daemon=True)
                self.thread.start()
        except BaseException:
            os.close(master)
            raise
        finally:
            os.close(slave)

    def _read(self, fd, stream):
        banner = bytearray()
        diagnostics = bytearray()
        errors = self.process.stderr.fileno()
        readers = [fd, errors]
        try:
            os.set_blocking(self.process.stdin.fileno(), False)
            while not self.shutdown.is_set():
                elapsed = time.monotonic() - self.created
                if elapsed >= 1800:
                    self._end('closed', 'Session ended. Open SOL again to reconnect.')
                    break
                if self.state == 'starting' and elapsed >= 25:
                    self._end('failed', 'SOL activation timed out.')
                    break
                ready, _, _ = select.select(readers, [], [], .2)
                if errors in ready:
                    detail = os.read(errors, 4096)
                    if detail:
                        diagnostics.extend(detail[:4096-len(diagnostics)])
                    else:
                        readers.remove(errors)
                if fd not in ready:
                    continue
                try:
                    data = os.read(fd, 4096)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    data = b''
                if not data:
                    if self.state == 'starting':
                        if b'payload already active' in diagnostics or b'payload activation limit reached' in diagnostics:
                            self._end('failed', 'Another SOL session is open. Close it in the client that opened it, then retry.')
                        else:
                            self._end('failed', 'SOL could not activate. Check account access and controller settings.')
                    break
                with self.lock:
                    if self.state == 'starting':
                        banner.extend(data)
                        if b'\n' not in banner:
                            if len(banner) > 4096:
                                raise ValueError('Missing SOL activation banner')
                            continue
                        header, _, data = banner.partition(b'\n')
                        if not header.startswith(b'[SOL Session operational.'):
                            raise ValueError('Invalid SOL activation banner')
                        self.state = 'connected'
                    stream.feed(bytes(data))
        except (OSError, ValueError, IndexError):
            self._end('failed', 'The serial console stopped.')
        finally:
            with self.lock:
                self.input_enabled = False
                if self.state in ('starting', 'connected'):
                    self.state = 'closed'
                self.process.stdin.close()
            try:
                self.process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            finally:
                os.close(fd)
                self.process.stderr.close()
                self.done.set()

    def _end(self, state, error):
        with self.lock:
            self.state = state
            self.error = error
            self.input_enabled = False

    def snapshot(self):
        with self.lock:
            display = '\n'.join(line[:264] for line in self.screen.display) if self.screen else ''
            return {'state': self.state, 'text': display, 'error': self.error,
                    'input_enabled': self.input_enabled}

    def message(self, message):
        if not isinstance(message, dict):
            raise ValueError('Invalid SOL message')
        with self.lock:
            connected = self.state == 'connected' and not self.shutdown.is_set()
            if message.keys() == {'type', 'enabled'} and message['type'] == 'enable' and type(message['enabled']) is bool:
                self.input_enabled = connected and message['enabled']
                return
            if message.keys() != {'type', 'data'} or message['type'] != 'input' or not isinstance(message['data'], str):
                raise ValueError('Invalid SOL input')
            data = message['data'].encode('utf-8')
            if not 0 < len(data) <= 512 or self.escape.encode() in data:
                raise ValueError('Invalid SOL input')
            if connected and self.input_enabled:
                os.write(self.process.stdin.fileno(), data)

    def expired(self):
        return self.done.is_set()

    def stop(self):
        self.shutdown.set()
        with self.lock:
            thread = self.thread
        if thread:
            thread.join()
