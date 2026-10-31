# Copyright 2026 DRACula contributors
# SPDX-License-Identifier: Apache-2.0
import hashlib
import io
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from dracula import kvm_runtime as runtime


class RuntimeCheckTests(unittest.TestCase):
    def probe(self, results, auto=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(runtime.subprocess, 'run', side_effect=results) as run:
                runtime.check_display(root/'bin/java', root, root, auto_download=auto)
                return run.call_args_list

    def result(self, output=b'', code=0):
        return subprocess.CompletedProcess([], code, b'', output)

    def test_working_graphics_needs_no_download_and_does_not_show_viewer(self):
        with patch.object(runtime, 'prepare_xtst') as download:
            calls = self.probe([self.result(), self.result()])
            download.assert_not_called()
            self.assertIn('dracula.DesktopRuntimeProbe', calls[-1].args[0])
            self.assertNotIn('ReadOnlyViewer', ' '.join(calls[-1].args[0]))

    def test_missing_xtst_downloads_privately_then_rechecks(self):
        with patch.object(runtime, 'prepare_xtst') as download:
            calls = self.probe([self.result(), self.result(b'libXtst.so.6: cannot open shared object file', 1), self.result()])
            download.assert_called_once()
            self.assertEqual(len(calls), 3)

    def test_source_mode_reports_dependency_without_downloading_or_retrying(self):
        with patch.object(runtime, 'prepare_xtst') as download:
            with self.assertRaisesRegex(RuntimeError, '32-bit library libXtst.so.6'):
                self.probe([self.result(), self.result(b'libXtst.so.6: cannot open shared object file', 1)], auto=False)
            download.assert_not_called()

    def test_remaining_missing_library_is_named_without_raw_diagnostics(self):
        with self.assertRaisesRegex(RuntimeError, '32-bit library libXrender.so.1') as error:
            self.probe([self.result(), self.result(b'/private/location libXrender.so.1: cannot open shared object file', 1)])
        self.assertNotIn('/private/location', str(error.exception))

    def test_failed_download_has_actionable_message(self):
        with patch.object(runtime, 'prepare_xtst', side_effect=OSError('network')):
            with self.assertRaisesRegex(RuntimeError, 'private download failed'):
                self.probe([self.result(), self.result(b'libXtst.so.6: cannot open shared object file', 1)])

    def test_missing_loader_and_display_and_timeout_are_not_retried(self):
        with self.assertRaisesRegex(RuntimeError, '32-bit Linux loader'):
            self.probe([FileNotFoundError()])
        with self.assertRaisesRegex(RuntimeError, 'local graphics'):
            self.probe([self.result(), self.result(b"Can't connect to X11 window server", 1)])
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            self.probe([subprocess.TimeoutExpired('java', 25)])

    def test_preflight_failure_precedes_creation_of_any_controller_session(self):
        from dracula import desktop_console
        with patch.dict(os.environ, {'DISPLAY': ':99', 'DRACULA_AUTO_JAVA': '0'}), \
             patch.object(runtime, 'check_display', side_effect=RuntimeError('missing native library')), \
             patch.object(desktop_console, 'ConsoleSession') as session:
            with self.assertRaisesRegex(RuntimeError, 'missing native library'):
                desktop_console.run('192.0.2.1', 'synthetic', 'synthetic')
            session.assert_not_called()

    def test_environment_is_private_and_does_not_mutate_parent(self):
        parent = {'DISPLAY': ':88', 'LD_LIBRARY_PATH': '/host', '_JAVA_OPTIONS': '-bad'}
        env = runtime.viewer_environment(parent, Path('/private'))
        self.assertEqual(env['LD_LIBRARY_PATH'], '/private/lib32/usr/lib/i386-linux-gnu')
        self.assertNotIn('_JAVA_OPTIONS', env)
        self.assertEqual(parent['LD_LIBRARY_PATH'], '/host')


class PrivateLibraryTests(unittest.TestCase):
    def package(self, members):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:xz') as tar:
            for name, value in members.items():
                item = tarfile.TarInfo('./'+name)
                item.size = len(value)
                tar.addfile(item, io.BytesIO(value))
        content = data.getvalue()
        header = '{:<16}{:<12}{:<6}{:<6}{:<8}{:<10}`\n'.format('data.tar.xz/', 0, 0, 0, '100644', len(content)).encode()
        return b'!<arch>\n'+header+content+(b'\n' if len(content) % 2 else b'')

    def test_checksum_rejection_writes_no_library(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(runtime.urllib.request, 'urlopen') as request:
                request.return_value.__enter__.return_value.read.return_value = b'corrupt download'
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    runtime.prepare_xtst(Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_only_verified_library_and_license_are_copied_never_package_paths(self):
        files = {name: name.encode() for name in runtime.XTST_FILES}
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
        package = self.package({**files, '../../escape': b'malicious', 'etc/profile': b'not installed'})
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(runtime, 'XTST_SHA256', hashlib.sha256(package).hexdigest()), \
             patch.object(runtime, 'XTST_FILES', hashes), \
             patch.object(runtime.urllib.request, 'urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value = package
            root = Path(directory)
            runtime.prepare_xtst(root)
            self.assertEqual((root/'lib32/usr/lib/i386-linux-gnu/libXtst.so.6').read_bytes(), files['usr/lib/i386-linux-gnu/libXtst.so.6.1.0'])
            self.assertTrue((root/'lib32/usr/share/doc/libxtst6/copyright').is_file())
            self.assertEqual(len([p for p in root.rglob('*') if p.is_file()]), 3)
            self.assertFalse((root/'lib32/etc').exists())

    def test_missing_license_prevents_installation(self):
        package = self.package({'usr/lib/i386-linux-gnu/libXtst.so.6.1.0': b'library'})
        with patch.object(runtime, 'XTST_SHA256', hashlib.sha256(package).hexdigest()), \
             patch.object(runtime, 'XTST_FILES', {'usr/lib/i386-linux-gnu/libXtst.so.6.1.0': hashlib.sha256(b'library').hexdigest(), 'usr/share/doc/libxtst6/copyright': '0'*64}):
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                runtime._package_files(package)
