// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

/** Exercise every input method with a tripwire in the real outgoing packet path. */
public final class ReadOnlySelfTest {
    static final class Tripwire extends ReadOnlyViewer.Transport {
        @Override public com.avocent.kvm.d.b.g y() {
            throw new AssertionError("An input method reached the packet queue");
        }
    }
    public static void main(String[] args) throws Exception {
        Tripwire t = new Tripwire();
        // Initial transport cleanup is not a dropped established connection.
        t.m();
        javax.swing.JPanel progress=new javax.swing.JPanel();
        progress.add(new javax.swing.JLabel("Connecting to KVM Server"));
        if (ReadOnlyViewer.hasOptionPane(progress)) throw new AssertionError("Progress mistaken for an error dialog");
        progress.add(new javax.swing.JOptionPane("Socket error"));
        if (!ReadOnlyViewer.hasOptionPane(progress)) throw new AssertionError("Error dialog not detected");
        if (args.length==1 && args[0].equals("--disconnect-check")) {
            t.l();
            t.m();
            throw new AssertionError("Established disconnect did not exit for reconnection");
        }
        t.d().a(65); t.d().b(65); t.d().a((com.avocent.kvm.d.d.d)null);
        t.e().a(10,20); t.e().b(10,20); t.e().c(10,20);
        t.e().a(1,2,3,true,true,true,4); t.e().b(1,2,3,true,true,true,4);
        for (int op=0; op<10; op++) {
            try { t.a(op,null,null); throw new AssertionError("Command allowed"); }
            catch (SecurityException expected) { }
        }
        System.out.println("PASS: all keyboard/mouse entry points and generic commands blocked");
        if (args.length==1 && args[0].equals("--window-close-check")) {
            javax.swing.JFrame frame=new javax.swing.JFrame();
            ReadOnlyViewer.ownWindowClose(frame);
            frame.dispatchEvent(new java.awt.event.WindowEvent(frame,java.awt.event.WindowEvent.WINDOW_CLOSING));
            throw new AssertionError("Local window close did not terminate normally");
        }
        System.exit(0);
    }
}
