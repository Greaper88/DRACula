// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

import java.awt.*;
import java.util.*;
import java.util.prefs.Preferences;
import javax.swing.*;
import javax.swing.plaf.ColorUIResource;
import javax.swing.plaf.FontUIResource;
import javax.swing.text.JTextComponent;

/** Local appearance only. Switching a palette never reloads a device or its fields. */
final class DesktopTheme {
    private static boolean dark=true;
    private static final String ROLE="dracula.theme.role";
    static boolean dark(){return dark;}
    static Color color(int rgb){return new Color(rgb);}
    static Color background(){return color(dark?0x080f24:0xf4f6fa);}
    static Color surface(){return color(dark?0x101c36:0xffffff);}
    static Color raised(){return color(dark?0x152340:0xf8f9fc);}
    static Color input(){return color(dark?0x0c1730:0xffffff);}
    static Color ink(){return color(dark?0xe8edfa:0x20232d);}
    static Color muted(){return color(dark?0xa9b5cf:0x667187);}
    static Color line(){return color(dark?0x2a3a5b:0xe1e5ed);}
    static Color accent(){return color(dark?0xc8a9ff:0x6d28d9);}
    static Color accentFill(){return color(0x7c3aed);}
    static Color selected(){return color(dark?0x382b60:0xeadfff);}
    static Color hover(){return color(dark?0x1c2d50:0xeef0f8);}
    static Color success(){return color(dark?0x7be0b6:0x176c53);}
    static Color warning(){return color(dark?0xf0ca83:0x805c15);}
    static Color danger(){return color(dark?0xff9fb2:0xa92c49);}
    static Color pending(){return color(dark?0x30283b:0xfff6df);}
    static Color row(int index,boolean dirty){return dirty?pending():index%2==0?surface():raised();}
    static String action(){return dark?"Light mode":"Dark mode";}
    static void load(){
        String value=System.getProperty("dracula.theme");
        if(value==null)try{value=Preferences.userNodeForPackage(DesktopTheme.class).get("theme","dark");}catch(SecurityException ignored){}
        install(!"light".equals(value));
    }
    static void remember(){try{Preferences p=Preferences.userNodeForPackage(DesktopTheme.class);p.put("theme",dark?"dark":"light");p.flush();}catch(Exception ignored){}}
    private static void put(String key,Color value){ColorUIResource resource=new ColorUIResource(value);UIManager.put(key,resource);UIManager.getLookAndFeelDefaults().put(key,resource);}
    private static void putPainter(String key,Painter<JComponent> painter){UIManager.put(key,painter);UIManager.getLookAndFeelDefaults().put(key,painter);}
    static void install(boolean value){
        dark=value;
        // Nimbus derives painter colors from these values when its defaults load.
        for(String key:new String[]{"control","nimbusLightBackground"})put(key,surface());
        put("nimbusBase",accentFill());put("nimbusBlueGrey",raised());put("text",ink());put("textForeground",ink());
        put("nimbusFocus",accent());put("nimbusSelectionBackground",selected());put("nimbusSelectedText",ink());put("nimbusDisabledText",muted());
        try{UIManager.setLookAndFeel(new javax.swing.plaf.nimbus.NimbusLookAndFeel());}catch(UnsupportedLookAndFeelException e){throw new IllegalStateException("Nimbus appearance unavailable",e);}
        put("control",surface());put("info",raised());put("nimbusBase",accentFill());put("nimbusBlueGrey",raised());put("nimbusLightBackground",surface());put("nimbusSelectionBackground",selected());put("nimbusSelectedText",ink());put("nimbusFocus",accent());put("text",ink());put("textForeground",ink());
        for(Object key:new ArrayList<>(UIManager.getDefaults().keySet())){
            Object existing=UIManager.get(key);String name=key.toString();
            if(existing instanceof Font)UIManager.put(key,new FontUIResource(Font.SANS_SERIF,Font.PLAIN,13));
            if(existing instanceof Color){
                String lower=name.toLowerCase(Locale.ROOT);
                if(lower.endsWith("foreground")||lower.endsWith("textforeground"))put(name,lower.contains("disabled")?muted():ink());
                else if(lower.endsWith("background"))put(name,lower.contains("selection")?selected():surface());
            }
        }
        put("controlText",ink());put("infoText",ink());put("textText",ink());put("menuText",ink());put("windowText",ink());put("textHighlight",selected());put("textHighlightText",ink());put("textInactiveText",muted());
        put("nimbusBorder",line());put("nimbusLightBackground",surface());put("nimbusDisabledText",muted());
        put("Panel.background",surface());put("Viewport.background",surface());put("ScrollPane.background",surface());
        put("List.background",surface());put("List.foreground",ink());put("List.selectionBackground",selected());put("List.selectionForeground",ink());
        put("Table.background",surface());put("Table.foreground",ink());put("Table.alternateRowColor",raised());put("Table.gridColor",line());put("Table.selectionBackground",selected());put("Table.selectionForeground",ink());
        put("TableHeader.foreground",muted());put("TableHeader.background",raised());
        for(String name:new String[]{"TextField","PasswordField","FormattedTextField","TextArea","TextPane","EditorPane","ComboBox"}){put(name+".background",input());put(name+".foreground",ink());put(name+".caretForeground",ink());put(name+".disabledText",muted());put(name+".selectionBackground",selected());put(name+".selectionForeground",ink());}
        put("TabbedPane.background",background());put("TabbedPane.foreground",ink());put("TabbedPane.contentAreaColor",surface());
        put("OptionPane.messageForeground",ink());put("OptionPane.background",surface());put("ToolTip.background",raised());put("ToolTip.foreground",ink());
        // Replace bright default gradients with flat surfaces in both palettes.
        for(Object item:new ArrayList<>(UIManager.getDefaults().keySet())){
            String key=item.toString();if(!key.endsWith("backgroundPainter"))continue;
            if(key.startsWith("Button")||key.startsWith("ToggleButton"))putPainter(key,painter(key,"button"));
            else if(key.startsWith("TextField")||key.startsWith("PasswordField")||key.startsWith("FormattedTextField")||key.startsWith("TextArea")||key.startsWith("ComboBox"))putPainter(key,painter(key,"input"));
            else if(key.startsWith("TabbedPane:TabbedPaneTab["))putPainter(key,painter(key,"tab"));
            else if(key.startsWith("TabbedPane:TabbedPaneTabArea"))putPainter(key,painter(key,"area"));
            else if(key.startsWith("TableHeader:"))putPainter(key,painter(key,"header"));
            else if(key.startsWith("ScrollBar:ScrollBarThumb"))putPainter(key,painter(key,"thumb"));
            else if(key.startsWith("ScrollBar:ScrollBarTrack"))putPainter(key,painter(key,"area"));
        }
    }
    static Painter<JComponent> painter(String key,String kind){return (graphics,component,width,height)->{
        Graphics2D g=(Graphics2D)graphics.create();g.setRenderingHint(RenderingHints.KEY_ANTIALIASING,RenderingHints.VALUE_ANTIALIAS_ON);
        boolean selected=key.contains("Selected"),over=key.contains("MouseOver"),disabled=key.contains("Disabled");
        boolean cell=Boolean.TRUE.equals(component.getClientProperty("dracula.field-cell"));
        Color fill=kind.equals("area")?background():kind.equals("input")?input():raised();
        if(kind.equals("thumb"))fill=color(dark?0x526584:0xaab4ca);
        if(selected||key.contains("Pressed"))fill=DesktopTheme.selected();if(over&&!disabled)fill=hover();
        if("primary".equals(component.getClientProperty(ROLE))&&!disabled)fill=accentFill();
        if(cell)fill=component.getBackground();
        g.setColor(fill);
        if(cell||kind.equals("area")||kind.equals("header"))g.fillRect(0,0,width,height);else g.fillRoundRect(0,0,width,height,9,9);
        if(kind.equals("header")){g.setColor(line());g.drawLine(0,height-1,width,height-1);g.drawLine(width-1,0,width-1,height);}
        else if(!cell&&!kind.equals("area")&&!kind.equals("thumb")){g.setColor(component.hasFocus()?accent():line());g.drawRoundRect(0,0,width-1,height-1,9,9);}
        g.dispose();
    };}
    static void style(JComponent component,String role){component.putClientProperty(ROLE,role);applyRole(component);}
    static void applyRole(JComponent component){
        Object role=component.getClientProperty(ROLE);if(role==null)return;
        switch(role.toString()){
            case "background"->component.setBackground(background());
            case "surface"->component.setBackground(surface());
            case "accent"->component.setForeground(accent());
            case "muted"->component.setForeground(muted());
            case "success"->component.setForeground(success());
            case "warning"->component.setForeground(warning());
            case "danger"->component.setForeground(danger());
            case "primary"->{
                component.setBackground(accentFill());component.setForeground(Color.WHITE);
                UIDefaults overrides=new UIDefaults();for(Object key:UIManager.getLookAndFeelDefaults().keySet())if(key.toString().startsWith("Button")&&key.toString().endsWith("textForeground"))overrides.put(key,key.toString().contains("Disabled")?muted():Color.WHITE);
                component.putClientProperty("Nimbus.Overrides",overrides);component.putClientProperty("Nimbus.Overrides.InheritDefaults",true);
            }
            default->component.setForeground(ink());
        }
    }
    static boolean finishEditors(Component component){
        if(component instanceof JTable table&&table.isEditing()&&!table.getCellEditor().stopCellEditing())return false;
        if(component instanceof Container container)for(Component child:container.getComponents())if(!finishEditors(child))return false;
        return true;
    }
    static void refreshWindows(){
        for(Window window:Window.getWindows()){
            SwingUtilities.updateComponentTreeUI(window);applyTree(window);window.repaint();
        }
    }
    static void applyTree(Component component){
        if(component instanceof Manager.PagePanel panel){panel.table.setDefaultRenderer(Object.class,new FieldCells.Renderer());panel.table.getColumnModel().getColumn(2).setCellEditor(new FieldCells.Editor());}
        if(component instanceof JScrollPane scroll)scroll.setBorder(BorderFactory.createLineBorder(line()));
        if(component instanceof JTable table){table.setBackground(surface());table.setForeground(ink());table.setSelectionBackground(selected());table.setSelectionForeground(ink());table.setGridColor(line());table.getTableHeader().setForeground(muted());table.getTableHeader().setBackground(raised());}
        else if(component instanceof JList<?> list){list.setBackground(surface());list.setForeground(ink());list.setSelectionBackground(selected());list.setSelectionForeground(ink());}
        else if(component instanceof JTextComponent text){text.setBackground(input());text.setForeground(ink());text.setCaretColor(ink());}
        else if(component instanceof JViewport)component.setBackground(surface());
        if(component instanceof JComponent swing)applyRole(swing);
        if(component instanceof Container container)for(Component child:container.getComponents())applyTree(child);
    }
}
