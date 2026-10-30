package dracula;

import java.awt.*;
import java.awt.event.*;
import javax.swing.*;
import com.avocent.kvm.d.*;

/** Version-specific adapter: no remote input, native keyboard hooks or menus. */
public final class ReadOnlyViewer {
    public static class Transport extends com.avocent.kvm.e.m {
        public Transport() { super(null); }
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
        @Override public bi d() { return keyboard; }
        @Override public bj e() { return mouse; }
        // Disable the generic viewer command channel (power/control operations).
        @Override public int a(int op, Object first, Object second) {
            throw new SecurityException("Remote control commands disabled in read-only mode");
        }
    }
    static final class Viewer extends com.avocent.drac5.viewer.f {
        Viewer() { super(); this.r = new Transport(); }
        // Refuse session-sharing prompts that could displace another viewer.
        @Override public void r() { System.err.println("Console login failed; sharing and takeover disabled"); System.exit(2); }
    }
    static final class Factory extends com.avocent.drac5.kvm.e {
        @Override public q a(Object ignored) {
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
            frame.setJMenuBar(null);
            frame.setTitle("DRACula — View only (input blocked)");
            return frame;
        }
        @Override public JFrame c(com.avocent.a.b.i viewer) {
            JFrame frame=super.c(viewer);
            frame.setJMenuBar(null);
            return frame;
        }

    }
    public static void main(String[] ignored) throws Exception {
        // Ticket is sent over stdin, never in the OS command line.
        java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(System.in, "UTF-8"));
        String line = reader.readLine();
        if (line == null) throw new IllegalArgumentException("Missing launch parameters");
        String[] args = line.split("\\t", -1);
        com.avocent.kvm.d.e.e log = com.avocent.kvm.d.e.b.a();
        log.b(false);
        com.avocent.a.c resources = new com.avocent.a.c();
        resources.a("com.avocent.drac5.kvm.Res");
        Viewer viewer = new Viewer();
        viewer.a(log);
        viewer.a(new Factory(), resources, args);
        Runtime.getRuntime().addShutdownHook(new Thread(new Runnable() {
            public void run() { try { viewer.a().g(); } catch (Exception ignored) { } }
        }));
        viewer.f();
    }
}
