// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import java.util.concurrent.ArrayBlockingQueue;
import javax.swing.*;
import javax.swing.border.EmptyBorder;

/** Display a serial session without sending input until the operator enables it. */
final class SolDialog extends JDialog {
    private final JTextArea screen = new JTextArea(25, 80);
    private final JLabel status = new JLabel("Connecting…");
    private final JCheckBox keyboard = new JCheckBox("Enable keyboard input");
    private final ArrayBlockingQueue<String> commands = new ArrayBlockingQueue<>(64);
    private volatile Process process;
    private volatile boolean disposed;
    private boolean inputEnabled;

    SolDialog(JFrame owner, String host) {
        super(owner, "Serial over LAN · " + host, false);
        setDefaultCloseOperation(DISPOSE_ON_CLOSE);
        JPanel body = new JPanel(new BorderLayout(0, 12));
        body.setBorder(new EmptyBorder(16, 16, 16, 16));
        DesktopTheme.style(body, "surface");
        setContentPane(body);
        body.add(status, BorderLayout.NORTH);
        screen.setEditable(false);
        screen.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 14));
        screen.getAccessibleContext().setAccessibleName("Serial terminal");
        body.add(new JScrollPane(screen), BorderLayout.CENTER);
        JPanel controls = new JPanel(new BorderLayout());
        controls.setOpaque(false);
        keyboard.setEnabled(false);
        controls.add(keyboard, BorderLayout.WEST);
        JButton close = new JButton("Close SOL");
        close.addActionListener(event -> dispose());
        controls.add(close, BorderLayout.EAST);
        body.add(controls, BorderLayout.SOUTH);
        keyboard.addActionListener(event -> requestInput(keyboard.isSelected()));
        addWindowFocusListener(new WindowAdapter() {
            @Override public void windowLostFocus(WindowEvent event) { requestInput(false); }
        });
        screen.setFocusTraversalKeysEnabled(false);
        screen.addKeyListener(new KeyAdapter() {
            @Override public void keyPressed(KeyEvent event) {
                if (event.getKeyCode() == KeyEvent.VK_TAB && (!inputEnabled || event.isShiftDown())) {
                    if (event.isShiftDown()) screen.transferFocusBackward();
                    else screen.transferFocus();
                    event.consume();
                    return;
                }
                if (!inputEnabled) return;
                String sequence = switch (event.getKeyCode()) {
                    case KeyEvent.VK_UP -> "\033[A";
                    case KeyEvent.VK_DOWN -> "\033[B";
                    case KeyEvent.VK_RIGHT -> "\033[C";
                    case KeyEvent.VK_LEFT -> "\033[D";
                    case KeyEvent.VK_HOME -> "\033[H";
                    case KeyEvent.VK_END -> "\033[F";
                    case KeyEvent.VK_INSERT -> "\033[2~";
                    case KeyEvent.VK_DELETE -> "\033[3~";
                    case KeyEvent.VK_PAGE_UP -> "\033[5~";
                    case KeyEvent.VK_PAGE_DOWN -> "\033[6~";
                    case KeyEvent.VK_F1 -> "\033OP";
                    case KeyEvent.VK_F2 -> "\033OQ";
                    case KeyEvent.VK_F3 -> "\033OR";
                    case KeyEvent.VK_F4 -> "\033OS";
                    case KeyEvent.VK_F5 -> "\033[15~";
                    case KeyEvent.VK_F6 -> "\033[17~";
                    case KeyEvent.VK_F7 -> "\033[18~";
                    case KeyEvent.VK_F8 -> "\033[19~";
                    case KeyEvent.VK_F9 -> "\033[20~";
                    case KeyEvent.VK_F10 -> "\033[21~";
                    case KeyEvent.VK_F11 -> "\033[23~";
                    case KeyEvent.VK_F12 -> "\033[24~";
                    default -> "";
                };
                if (!sequence.isEmpty()) {
                    sendInput(sequence);
                    event.consume();
                }
            }

            @Override public void keyTyped(KeyEvent event) {
                if (!inputEnabled || event.isAltDown() || event.isMetaDown()) return;
                char key = event.getKeyChar();
                if (key == KeyEvent.CHAR_UNDEFINED || key == '\u001d' || key == '\u007f') return;
                if (key == '\u0003' && screen.getSelectedText() != null) return;
                if (key == '\t' && event.isShiftDown()) return;
                sendInput(String.valueOf(key == '\n' ? '\r' : key == '\b' ? '\u007f' : key));
                event.consume();
            }
        });
        pack();
        setLocationRelativeTo(owner);
        DesktopTheme.applyTree(this);
    }

    private void requestInput(boolean enable) {
        if (!enable) {
            if (!keyboard.isSelected() && !inputEnabled && !keyboard.isEnabled()) return;
            keyboard.setSelected(false);
            inputEnabled = false;
        }
        send(enable ? "ENABLE" : "DISABLE");
    }

    private void sendInput(String data) { send("INPUT\t" + Manager.enc(data)); }

    private void send(String command) {
        if (!disposed && !commands.offer(command)) {
            Process current = process;
            if (current != null) current.destroy();
            update("failed", false, null, "The serial input channel is busy. Open SOL again.");
        }
    }

    void start(ProcessBuilder builder, String host, String user, char[] password) {
        Thread reader = new Thread(() -> {
            Thread writer = null;
            try {
                if (disposed) return;
                Process child = builder.start();
                process = child;
                if (disposed) return;
                BufferedWriter output = child.outputWriter(StandardCharsets.UTF_8);
                for (String value : new String[]{host, user, new String(password)}) {
                    output.write(Manager.enc(value));
                    output.newLine();
                }
                output.flush();
                Arrays.fill(password, '\0');
                writer = new Thread(() -> writeCommands(output), "dracula-sol-input");
                writer.setDaemon(true);
                writer.start();
                boolean terminal = false;
                try (BufferedReader input = child.inputReader(StandardCharsets.UTF_8)) {
                    String line;
                    while ((line = input.readLine()) != null && !disposed) {
                        String[] fields = line.split("\t", -1);
                        if (fields.length == 5 && fields[0].equals("SOL")) {
                            String state = decode(fields[1]);
                            boolean enabled = Boolean.parseBoolean(decode(fields[2]));
                            String display = decode(fields[3]);
                            String error = decode(fields[4]);
                            terminal = state.equals("closed") || state.equals("failed");
                            SwingUtilities.invokeLater(() -> update(state, enabled, display, error));
                        } else if (fields.length == 2 && fields[0].equals("ERROR")) {
                            String error = decode(fields[1]);
                            terminal = true;
                            SwingUtilities.invokeLater(() -> update("failed", false, null, error));
                        }
                    }
                }
                if (!terminal) SwingUtilities.invokeLater(() -> update("closed", false, null, ""));
            } catch (IOException | IllegalArgumentException error) {
                SwingUtilities.invokeLater(() -> update("failed", false, null, "The serial console could not start."));
            } finally {
                Arrays.fill(password, '\0');
                if (writer != null) writer.interrupt();
                Process child = process;
                if (child != null && child.isAlive()) child.destroy();
            }
        }, "dracula-sol");
        reader.setDaemon(true);
        reader.start();
    }

    private void writeCommands(BufferedWriter output) {
        try (output) {
            while (!disposed) {
                output.write(commands.take());
                output.newLine();
                output.flush();
            }
        } catch (IOException | InterruptedException ignored) {
            Process child = process;
            if (child != null && child.isAlive()) child.destroy();
        }
    }

    private static String decode(String field) {
        return new String(Base64.getDecoder().decode(field), StandardCharsets.UTF_8);
    }

    private void update(String state, boolean enabled, String display, String error) {
        if (disposed) return;
        boolean connected = state.equals("connected");
        boolean wasEnabled = inputEnabled;
        inputEnabled = connected && keyboard.isSelected() && enabled;
        keyboard.setEnabled(connected);
        if (!connected) keyboard.setSelected(false);
        if (inputEnabled && !wasEnabled) screen.requestFocusInWindow();
        if (display != null && !screen.getText().equals(display)) screen.setText(display);
        String message = switch (state) {
            case "starting" -> "Connecting…";
            case "connected" -> inputEnabled ? "Connected · Keyboard enabled" : "Connected · View only";
            default -> "Serial console disconnected.";
        };
        status.setText(error.isBlank() ? message : error);
    }

    @Override public void dispose() {
        disposed = true;
        Process child = process;
        if (child != null && child.isAlive()) child.destroy();
        super.dispose();
    }
}
