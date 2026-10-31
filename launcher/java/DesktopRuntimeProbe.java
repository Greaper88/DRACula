// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

/** Load native graphics and fonts without showing a viewer or generating input. */
public final class DesktopRuntimeProbe {
    public static void main(String[] args) throws Exception {
        javax.swing.SwingUtilities.invokeAndWait(() -> {
            javax.swing.JFrame window = new javax.swing.JFrame();
            try {
                window.add(new javax.swing.JLabel("KVM graphics check"));
                window.pack();
            } finally {
                window.dispose();
            }
        });
        System.exit(0);
    }
}
