// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

import java.awt.*;
import java.awt.event.KeyEvent;
import javax.swing.*;
import javax.swing.border.EmptyBorder;

/** Project identity and attribution, available without a device connection. */
final class AboutDialog extends JDialog {
    static final String NOTICE_TEXT="""
        DRACula is an independent, open-source project. “DRAC” refers to Dell Remote Access Controller and is used in the project name to identify hardware the software is designed to work with. DRACula is not affiliated with, endorsed by, or sponsored by Dell Technologies.

        Dell Technologies, Dell, and other Dell trademarks are trademarks of Dell Inc. or its subsidiaries.
        """;

    AboutDialog(JFrame owner){
        super(owner,"About DRACula",true);
        setDefaultCloseOperation(DISPOSE_ON_CLOSE);
        JPanel body=new JPanel(new BorderLayout(0,20));
        body.setBorder(new EmptyBorder(24,26,20,26));DesktopTheme.style(body,"surface");setContentPane(body);
        JPanel heading=new JPanel(new BorderLayout(0,6));heading.setOpaque(false);
        JLabel title=new JLabel("DRACula");title.setFont(new Font(Font.SANS_SERIF,Font.BOLD,28));DesktopTheme.style(title,"accent");heading.add(title,BorderLayout.NORTH);
        JLabel subtitle=new JLabel("Independent remote access management · Apache License 2.0");DesktopTheme.style(subtitle,"muted");heading.add(subtitle,BorderLayout.SOUTH);body.add(heading,BorderLayout.NORTH);
        JTextArea notice=new JTextArea(NOTICE_TEXT,9,48);notice.setEditable(false);notice.setLineWrap(true);notice.setWrapStyleWord(true);notice.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,14));notice.setOpaque(false);notice.setCaretPosition(0);
        JScrollPane scroll=new JScrollPane(notice);scroll.setBorder(null);scroll.setOpaque(false);scroll.getViewport().setOpaque(false);body.add(scroll,BorderLayout.CENTER);
        JPanel footer=new JPanel(new FlowLayout(FlowLayout.RIGHT,0,0));footer.setOpaque(false);
        JButton close=new JButton("Close");close.addActionListener(e->dispose());footer.add(close);body.add(footer,BorderLayout.SOUTH);getRootPane().setDefaultButton(close);
        getRootPane().registerKeyboardAction(e->dispose(),KeyStroke.getKeyStroke(KeyEvent.VK_ESCAPE,0),JComponent.WHEN_IN_FOCUSED_WINDOW);
        setMinimumSize(new Dimension(460,340));pack();setLocationRelativeTo(owner);DesktopTheme.applyTree(this);
    }
}
