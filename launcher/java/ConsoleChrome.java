// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

import java.awt.*;
import java.util.*;
import javax.swing.*;
import javax.swing.border.EmptyBorder;

/** Passive status chrome: no menus, actions, key listeners or remote commands. */
final class ConsoleChrome {
    private static final Set<JFrame> frames=Collections.newSetFromMap(new WeakHashMap<JFrame,Boolean>());
    private static String target="Remote console";
    private static boolean enabled(){return !"0".equals(System.getenv("DRACULA_VIEWER_CHROME"));}
    static void target(String value){if(value.matches("[0-9.]+"))target=value;}
    static String label(String state){
        if(state.equals("connected"))return "Connected";
        if(state.equals("closed"))return "Closed";
        if(state.startsWith("disconnected"))return "Reconnecting";
        return "Connecting";
    }
    private static String lastState="starting";
    static void refreshMode(){refresh(lastState);}
    static void register(JFrame frame,String state){
        synchronized(frames){frames.add(frame);}update(frame,state);
    }
    static void refresh(final String state){
        lastState=state;
        if(!enabled())return;
        SwingUtilities.invokeLater(new Runnable(){public void run(){
            synchronized(frames){for(JFrame frame:frames)update(frame,state);}
        }});
    }
    static void update(JFrame frame,String state){
        if(!enabled())return;
        JMenuBar bar=frame.getJMenuBar();
        if(bar==null){bar=new JMenuBar();frame.setJMenuBar(bar);}
        JLabel status=null;
        for(Component child:bar.getComponents())if("dracula-connection-status".equals(child.getName()))status=(JLabel)child;
        if(status==null){
            bar.add(Box.createHorizontalGlue());status=new JLabel();status.setName("dracula-connection-status");status.setBorder(new EmptyBorder(8,12,8,12));bar.add(status);
            ConsoleControl control=ConsoleControl.current();
            if(control!=null&&control.capable){
                final JCheckBoxMenuItem toggle=new JCheckBoxMenuItem("Keyboard and mouse");toggle.setName("dracula-input-toggle");
                toggle.addActionListener(e->control.enable(toggle.isSelected()));
                JMenu menu=new JMenu("Input");menu.add(toggle);JMenuItem release=new JMenuItem("Release input (Ctrl+Alt+Shift)");release.addActionListener(e->control.enable(false));menu.add(release);bar.add(menu);
            }
        }
        ConsoleControl control=ConsoleControl.current();
        for(Component child:bar.getComponents())if(child instanceof JMenu){JMenu menu=(JMenu)child;for(int i=0;i<menu.getItemCount();i++){JMenuItem item=menu.getItem(i);if(item!=null&&"dracula-input-toggle".equals(item.getName())){item.setSelected(control!=null&&control.enabled());item.setEnabled(state.equals("connected"));}}}
        boolean connected=state.equals("connected");
        Color ink=connected?new Color(24,101,64):state.equals("closed")?new Color(75,85,99):new Color(128,79,0);
        bar.setBackground(connected?new Color(231,246,237):state.equals("closed")?new Color(238,241,245):new Color(255,244,214));
        status.setForeground(ink);status.setText("●  "+label(state));
        status.getAccessibleContext().setAccessibleDescription("Console connection: "+label(state));
        String title="DRACula · "+target+" · "+label(state)+" · "+(control!=null&&control.enabled()?"Keyboard and mouse enabled":"View only");
        if(!frame.getTitle().equals(title))frame.setTitle(title);
    }
}
