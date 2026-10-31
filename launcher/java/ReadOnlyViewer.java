// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

import java.awt.*;
import java.awt.event.*;
import javax.swing.*;
import com.avocent.kvm.d.*;

/** Version-specific adapter: no remote input, native keyboard hooks or menus. */
public final class ReadOnlyViewer {
    static final boolean inputCapable="1".equals(System.getenv("DRACULA_INPUT_CAPABLE"));
    private static volatile boolean closing;
    private static volatile boolean failed;
    private static volatile boolean userClosed;
    private static volatile String connectionState="starting";
    private static synchronized void state(String value) {
        if (failed && value.equals("connected")) return;
        connectionState=value;ConsoleChrome.refresh(value);
        String path=System.getenv("DRACULA_VIEWER_STATE");
        if (path != null) try {
            java.nio.file.Path target=java.nio.file.Paths.get(path);
            java.nio.file.Path temp=java.nio.file.Paths.get(path+".tmp");
            java.nio.file.Files.write(temp, value.getBytes("UTF-8"));
            java.nio.file.Files.move(temp,target,java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        } catch (Exception ignored) { }
    }
    static boolean hasOptionPane(Component component) {
        if (component instanceof JOptionPane) return true;
        if (component instanceof Container)
            for (Component child:((Container)component).getComponents())
                if (hasOptionPane(child)) return true;
        return false;
    }
    static boolean hasConnectionError(Component component) {
        if(component instanceof JOptionPane){JOptionPane pane=(JOptionPane)component;String message=String.valueOf(pane.getMessage()).toLowerCase(java.util.Locale.ROOT);return pane.getMessageType()==JOptionPane.ERROR_MESSAGE&&message.matches("(?s).*(socket|connection|network|session|authentication|login|timed out|i/o).*");}
        if(component instanceof Container)for(Component child:((Container)component).getComponents())if(hasConnectionError(child))return true;
        return false;
    }
    private static void dropped(String reason) {
        if (!closing) { failed=true; state("disconnected:"+reason); System.exit(3); }
    }
    public static class Transport extends com.avocent.kvm.e.m {
        private volatile boolean connected;
        final ConsoleControl controls;
        public Transport() { this(false); }
        Transport(boolean capable) { super(null);controls=new ConsoleControl(super.d(),super.e(),capable); }
        @Override public void l() { super.l(); connected=true; controls.connected(true); state("connected"); }
        @Override public void m() { controls.connected(false);super.m(); if (connected) dropped("closed"); }
        @Override public void a(Throwable error) {
            if (error instanceof java.io.IOException) dropped("transport-"+error.getClass().getSimpleName());
            else super.a(error);
        }
        private final bi keyboard = new bi() {
            public void a(int key) { }
            public void b(int key) { }
            public void a(com.avocent.kvm.d.d.d listener) { }
        };
        private final bj mouse = new bj() {
            public void a(int x, int y) { }
            public void b(int x, int y) { }
            public void c(int x, int y) { }
            public void a(int x, int y, int z, boolean b, boolean c, boolean d, int e) { }
            public void b(int x, int y, int z, boolean b, boolean c, boolean d, int e) { }
        };
        @Override public bi d() { return controls!=null&&controls.capable?controls.keyboard:keyboard; }
        @Override public bj e() { return controls!=null&&controls.capable?controls.mouse:mouse; }
        @Override public void a(boolean focused) { if(controls!=null&&controls.enabled())super.a(focused); }
        // Disable the generic viewer command channel (power/control operations).
        @Override public int a(int op, Object first, Object second) throws java.io.IOException {
            if(controls!=null&&controls.capable&&op>=1&&op<=6)return super.a(op,first,second);
            throw new SecurityException("Remote control commands disabled in read-only mode");
        }
    }
    static final class Viewer extends com.avocent.drac5.viewer.f {
        Viewer() { super(); this.r = new Transport(inputCapable); }
        // Refuse session-sharing prompts that could displace another viewer.
        @Override public void r() { System.err.println("Console login failed; sharing and takeover disabled"); System.exit(2); }
    }
    static void ownWindowClose(JFrame frame) {
        // A user's local window close is completion, never a transport failure.
        for (WindowListener listener:frame.getWindowListeners()) frame.removeWindowListener(listener);
        frame.setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE);
        frame.addWindowListener(new WindowAdapter() {
            @Override public void windowClosing(WindowEvent event) {
                if(ConsoleControl.current()!=null)ConsoleControl.current().enable(false);
                userClosed=true; closing=true; failed=true; state("closed"); System.exit(0);
            }
        });
    }
    static final class Factory extends com.avocent.drac5.kvm.e {
        @Override public q a(Object ignored) {
            // Interactive sessions use the vendor Java-only keyboard handler.
            if(inputCapable)return new com.avocent.kvm.d.w();
            // No native keyboard hook, Java key listeners, or focus-generated input.
            return new q() {
                public void a(t session, bh canvas) { }
                public void a(t session) { }
                public void a(bh canvas, com.avocent.kvm.d.e.e log) { }
                public void a() { }
                public void a(bh canvas, boolean enabled) { }
                public void a(boolean enabled) { }
            };
        }
        @Override public JFrame b(final com.avocent.a.b.i viewer) {
            JFrame frame=super.b(viewer);
            if(!inputCapable)frame.setJMenuBar(null);
            ownWindowClose(frame);
            if(ConsoleControl.current()!=null)ConsoleControl.current().watch(frame);
            frame.setTitle("DRACula — View only (input blocked)");
            ConsoleChrome.register(frame,connectionState);
            return frame;
        }
        @Override public JFrame c(com.avocent.a.b.i viewer) {
            JFrame frame=super.c(viewer);
            if(!inputCapable)frame.setJMenuBar(null);
            ownWindowClose(frame);
            if(ConsoleControl.current()!=null)ConsoleControl.current().watch(frame);
            ConsoleChrome.register(frame,connectionState);
            return frame;
        }

    }
    public static void main(String[] ignored) throws Exception {
        // Ticket is sent over stdin, never in the OS command line.
        java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(System.in, "UTF-8"));
        String line = reader.readLine();
        if (line == null) throw new IllegalArgumentException("Missing launch parameters");
        String[] args = line.split("\\t", -1);
        for(String arg:args)if(arg.startsWith("ip="))ConsoleChrome.target(arg.substring(3));
        com.avocent.kvm.d.e.e log = com.avocent.kvm.d.e.b.a();
        log.b(false);
        com.avocent.a.c resources = new com.avocent.a.c();
        resources.a("com.avocent.drac5.kvm.Res");
        Viewer viewer = new Viewer();
        viewer.a(log);
        viewer.a(new Factory(), resources, args);
        Runtime.getRuntime().addShutdownHook(new Thread(new Runnable() {
            public void run() {
                if(ConsoleControl.current()!=null)ConsoleControl.current().enable(false);
                closing=true; failed=true; state(userClosed?"closed":"disconnected:exit");
                Thread cleanup=new Thread(new Runnable() {
                    public void run() { try { viewer.a().g(); } catch (Exception ignored) { } }
                },"dracula-close-sockets");
                cleanup.setDaemon(true); cleanup.start();
                try { cleanup.join(2000); } catch (InterruptedException ignored) { }
            }
        }));
        // Vendor socket failures can block inside a dialog before notifying listeners.
        // Observe our own windows only; never dismiss dialogs or synthesize input.
        Thread watcher=new Thread(new Runnable() {
            public void run() {
                while (!closing) {
                    for (Window window:Window.getWindows())
                        if (window instanceof JDialog && window.isVisible() && (inputCapable?hasConnectionError(window):hasOptionPane(window)))
                            dropped("dialog");
                    ConsoleChrome.refresh(connectionState);
                    try { Thread.sleep(500); } catch (InterruptedException ex) { return; }
                }
            }
        },"dracula-connection-watch");
        watcher.setDaemon(true); watcher.start();
        if(ConsoleControl.current()!=null)ConsoleControl.current().startBroker();
        viewer.f();
    }
}
