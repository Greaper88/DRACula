// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import java.awt.*;
import java.awt.event.*;

/** Visible during connection recovery; the live viewer carries its own passive badge. */
final class ConsoleStatusDialog extends JDialog {
    final JLabel badge=new JLabel("Connecting"),detail=new JLabel("Opening remote console…");
    final JProgressBar progress=new JProgressBar();
    volatile boolean cancelled;
    volatile Runnable cancelAction=()->{};
    ConsoleStatusDialog(JFrame owner,String host){
        super(owner,"KVM · "+host,false);setDefaultCloseOperation(DO_NOTHING_ON_CLOSE);
        JPanel body=new JPanel(new BorderLayout(0,14));body.setBorder(new EmptyBorder(22,24,20,24));DesktopTheme.style(body,"surface");setContentPane(body);
        JLabel target=new JLabel("Remote console · "+host);target.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,13));DesktopTheme.style(target,"muted");body.add(target,BorderLayout.NORTH);
        JPanel middle=new JPanel(new GridLayout(0,1,0,12));middle.setOpaque(false);
        badge.setFont(new Font(Font.SANS_SERIF,Font.BOLD,22));badge.getAccessibleContext().setAccessibleName("Console connection status");middle.add(badge);middle.add(detail);
        progress.setIndeterminate(true);middle.add(progress);body.add(middle,BorderLayout.CENTER);
        JPanel bottom=new JPanel(new BorderLayout(15,0));bottom.setOpaque(false);JLabel mode=new JLabel("Keyboard and mouse can be enabled in the viewer");mode.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,11));bottom.add(mode,BorderLayout.WEST);
        JButton close=new JButton("Close console");close.addActionListener(e->cancel());bottom.add(close,BorderLayout.EAST);body.add(bottom,BorderLayout.SOUTH);
        addWindowListener(new WindowAdapter(){public void windowClosing(WindowEvent event){cancel();}});
        setMinimumSize(new Dimension(470,230));pack();setLocationRelativeTo(owner);
    }
    void cancel(){if(cancelled)return;cancelled=true;cancelAction.run();dispose();}
    void showState(String state,int attempt,int retryIn){
        if(cancelled)return;
        boolean connected=state.equals("connected"),closing=state.equals("closing"),failed=state.equals("failed");
        String label=connected?"Connected":closing?"Closing":failed?"Disconnected":state.equals("reconnecting")?"Reconnecting":"Connecting";
        badge.setText("●  "+label);DesktopTheme.style(badge,connected?"success":failed?"danger":"warning");
        String note=connected?"Your console is connected.":closing?"Finishing your console session…":failed?"Automatic reconnect stopped. Close and open the console again.":state.equals("reconnecting")?"Reconnecting automatically.":"Opening remote console…";
        if(state.equals("reconnecting")){if(attempt>0)note+=" Attempt "+attempt+".";if(retryIn>0)note+=" Next try in "+retryIn+"s.";}
        detail.setText(note);progress.setVisible(!connected&&!closing&&!failed);
        // Keep a recovery window available while replacement Java viewers are absent.
        setVisible(!connected&&!closing);
    }
}
