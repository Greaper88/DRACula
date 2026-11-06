// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
'use strict';

let solSocket = null;
let solInputRequested = false;
let solInputEnabled = false;

function setSolInput(enabled) {
 const toggle = $('sol-input');
 solInputRequested = enabled;
 if (!enabled) solInputEnabled = false;
 toggle.checked = enabled;
 if (solSocket?.readyState === WebSocket.OPEN)
  solSocket.send(JSON.stringify({type:'enable', enabled}));
}

function closeSol() {
 const socket = solSocket;
 solSocket = null;
 solInputEnabled = solInputRequested = false;
 socket?.close();
 if ($('sol-dialog').open) $('sol-dialog').close();
}

function openSol() {
 if (!current()?.connected || !state.capabilities?.sol || state.settingsBusy || solSocket) return;
 const dialog = $('sol-dialog');
 const toggle = $('sol-input');
 const screen = $('sol-screen');
 toggle.checked = false;
 toggle.disabled = true;
 text('sol-status', 'Connecting…');
 screen.textContent = '';
 dialog.showModal();
 const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
 const socket = new WebSocket(`${protocol}//${location.host}/api/devices/${encodeURIComponent(state.device)}/sol`);
 solSocket = socket;
 socket.onmessage = event => {
  if (socket !== solSocket) return;
  const status = JSON.parse(event.data);
  const connected = status.state === 'connected';
  if (!connected) solInputRequested = false;
  const wasEnabled = solInputEnabled;
  solInputEnabled = connected && solInputRequested && status.input_enabled === true;
  toggle.disabled = !connected;
  toggle.checked = solInputRequested;
  if (solInputEnabled && !wasEnabled) screen.focus();
  text('sol-status', status.error || (connected ? (solInputEnabled ? 'Connected · Keyboard enabled' : 'Connected · View only') :
   status.state === 'starting' ? 'Connecting…' : 'Serial console disconnected.'));
  if (typeof status.text === 'string' && screen.textContent !== status.text) screen.textContent = status.text;
 };
 socket.onclose = event => {
  if (socket !== solSocket) return;
  solSocket = null;
  solInputEnabled = solInputRequested = false;
  toggle.checked = false;
  toggle.disabled = true;
  if (event.code !== 1000 && event.code !== 1005) text('sol-status', 'SOL connection ended. Close and open it again to retry.');
 };
}

function sendSolInput(data) {
 if (!solInputEnabled || solSocket?.readyState !== WebSocket.OPEN || !data) return;
 if (new TextEncoder().encode(data).length > 512) {
  text('sol-status', 'Paste up to 512 bytes at a time.');
  return;
 }
 if (data.includes('\x1d')) return;
 solSocket.send(JSON.stringify({type:'input', data}));
}

function initSol() {
 const screen = $('sol-screen');
 const keys = {Enter:'\r', Backspace:'\x7f', Tab:'\t', Escape:'\x1b',
  ArrowUp:'\x1b[A', ArrowDown:'\x1b[B', ArrowRight:'\x1b[C', ArrowLeft:'\x1b[D',
  Home:'\x1b[H', End:'\x1b[F', Delete:'\x1b[3~', Insert:'\x1b[2~',
  PageUp:'\x1b[5~', PageDown:'\x1b[6~',
  F1:'\x1bOP', F2:'\x1bOQ', F3:'\x1bOR', F4:'\x1bOS', F5:'\x1b[15~',
  F6:'\x1b[17~', F7:'\x1b[18~', F8:'\x1b[19~', F9:'\x1b[20~',
  F10:'\x1b[21~', F11:'\x1b[23~', F12:'\x1b[24~'};
 $('sol').onclick = openSol;
 $('close-sol').onclick = closeSol;
 $('sol-dialog').addEventListener('cancel', event => {event.preventDefault();closeSol();});
 $('sol-input').onchange = event => setSolInput(event.target.checked);
 window.addEventListener('blur', () => setSolInput(false));
 document.addEventListener('visibilitychange', () => {if (document.hidden) setSolInput(false);});
 screen.addEventListener('keydown', event => {
  if (!solInputEnabled || event.metaKey || event.altKey || event.isComposing) return;
  // Keep a keyboard route back to the dialog controls.
  if (event.shiftKey && event.key === 'Tab') return;
  let data;
  if (event.ctrlKey) {
   if (/^[a-z]$/i.test(event.key) && !/^[v]$/i.test(event.key) &&
       !(event.key.toLowerCase() === 'c' && window.getSelection()?.toString()))
    data = String.fromCharCode(event.key.toUpperCase().charCodeAt(0) - 64);
  } else {
   data = keys[event.key] || (Array.from(event.key).length === 1 ? event.key : '');
  }
  if (data) {event.preventDefault();sendSolInput(data);}
 });
 screen.addEventListener('paste', event => {
  if (!solInputEnabled) return;
  event.preventDefault();
  sendSolInput(event.clipboardData.getData('text').replace(/\r?\n/g, '\r'));
 });
}
