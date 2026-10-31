// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

import java.awt.*;
import java.util.*;
import javax.swing.*;
import javax.swing.table.*;

/** Cell edits are drafts. Only the Manager review/confirmation flow can submit them. */
final class FieldCells {
    record Choice(String value,String text){public String toString(){return text;}}
    static final class Edit {
        final String key,type,initial,revision,on,off;final java.util.List<Choice> choices=new ArrayList<>();
        Edit(String[] f){key=f[0];type=f[1];initial=f[2];revision=f[3];on=f[8];off=f[9];}
        boolean binary(){return type.equals("boolean")||type.equals("choice")&&choices.size()==2&&choices.stream().anyMatch(c->c.value.equals("0"))&&choices.stream().anyMatch(c->c.value.equals("1"));}
        String display(String raw){if(type.equals("boolean"))return raw.equals("1")?on:off;return choices.stream().filter(c->c.value.equals(raw)).map(Choice::text).findFirst().orElse(raw);}
    }
    record Value(String text, Boolean checked, Edit edit,String raw) {
        Value(String text,Boolean checked){this(text,checked,null,null);}
        public String toString(){return text;}
        Value changed(String value){return new Value(edit.display(value),edit.binary()?value.equals("1"):null,edit,value);}
        boolean dirty(){return edit!=null&&!Objects.equals(raw,edit.initial);}
    }
    record Access(String mode,String evidence,boolean editable) {
        Access(String mode,String evidence){this(mode,evidence,false);}
        public String toString(){return switch(mode){case "configurable"->editable?"Configurable":"Configurable · locked";case "read-only"->"Read only";default->"Unverified";};}
    }
    static Object[] row(String[] fields){return row(fields,null);}
    static Object[] row(String[] fields,Edit edit){
        Boolean checked=fields[3].equals("true")?Boolean.TRUE:fields[3].equals("false")?Boolean.FALSE:null;
        return new Object[]{fields[0],fields[1],new Value(fields[2],checked,edit,edit==null?null:edit.initial),new Access(fields[4],fields[5],edit!=null)};
    }
    static final class ToggleIcon implements Icon {
        final boolean on;ToggleIcon(boolean on){this.on=on;}
        public int getIconWidth(){return 34;}public int getIconHeight(){return 20;}
        public void paintIcon(Component c,Graphics g,int x,int y){Graphics2D paint=(Graphics2D)g.create();paint.setRenderingHint(RenderingHints.KEY_ANTIALIASING,RenderingHints.VALUE_ANTIALIAS_ON);paint.setColor(on?DesktopTheme.color(DesktopTheme.dark()?0x2d9878:0x207963):DesktopTheme.color(DesktopTheme.dark()?0x536584:0x76808f));paint.fillRoundRect(x,y,34,20,20,20);paint.setColor(Color.WHITE);paint.fillOval(x+(on?17:3),y+3,14,14);paint.dispose();}
    }
    static final class Renderer extends DefaultTableCellRenderer {
        public Component getTableCellRendererComponent(JTable table,Object value,boolean selected,boolean focus,int row,int col){
            putClientProperty("html.disable",Boolean.TRUE);super.getTableCellRendererComponent(table,value,selected,focus,row,col);
            if(!selected){setBackground(DesktopTheme.row(row,value instanceof Value field&&field.dirty()));setForeground(value instanceof Access?DesktopTheme.muted():DesktopTheme.ink());}
            setBorder(BorderFactory.createEmptyBorder(0,7,0,7));setToolTipText(value instanceof Access access?access.evidence():String.valueOf(value));
            if(value instanceof Value field&&field.checked()!=null){
                JToggleButton toggle=new JToggleButton(field.text(),new ToggleIcon(field.checked()),field.checked());
                toggle.setDisabledIcon(new ToggleIcon(field.checked()));toggle.setDisabledSelectedIcon(new ToggleIcon(field.checked()));
                toggle.putClientProperty("dracula.field-cell",Boolean.TRUE);toggle.setForeground(getForeground());toggle.setEnabled(field.edit()!=null&&table.isCellEditable(row,col));toggle.setHorizontalAlignment(SwingConstants.LEFT);toggle.setBorder(BorderFactory.createEmptyBorder(0,7,0,7));toggle.setBackground(getBackground());toggle.setBorderPainted(false);
                toggle.setToolTipText(field.edit()==null?"Reported device state · Editing locked":"Staged locally · Apply requires confirmation");toggle.getAccessibleContext().setAccessibleName(table.getValueAt(row,1)+": "+field.text());return toggle;
            }
            return this;
        }
    }
    static final class Editor extends AbstractCellEditor implements TableCellEditor {
        Value original;JComponent component;JTable editingTable;int modelRow;
        public Component getTableCellEditorComponent(JTable table,Object value,boolean selected,int row,int column){
            original=(Value)value;editingTable=table;modelRow=table.convertRowIndexToModel(row);
            if(original.edit.binary()){
                JToggleButton toggle=new JToggleButton(original.edit.display(original.raw),original.raw.equals("1"));toggle.setIcon(new ToggleIcon(toggle.isSelected()));
                toggle.addActionListener(e->{toggle.setText(original.edit.display(toggle.isSelected()?"1":"0"));stopCellEditing();});component=toggle;
            }else if(original.edit.type.equals("choice")){
                JComboBox<Choice> choices=new JComboBox<>(original.edit.choices.toArray(new Choice[0]));for(Choice choice:original.edit.choices)if(choice.value.equals(original.raw))choices.setSelectedItem(choice);choices.addActionListener(e->stage());component=choices;
            }else {
                JTextField input=new JTextField(original.raw);component=input;
                input.getDocument().addDocumentListener(new javax.swing.event.DocumentListener(){public void insertUpdate(javax.swing.event.DocumentEvent e){stage();}public void removeUpdate(javax.swing.event.DocumentEvent e){stage();}public void changedUpdate(javax.swing.event.DocumentEvent e){stage();}});
            }
            component.getAccessibleContext().setAccessibleName(table.getValueAt(row,1).toString());return component;
        }
        void stage(){if(component!=null&&editingTable!=null)editingTable.getModel().setValueAt(getCellEditorValue(),modelRow,2);}
        public void cancelCellEditing(){if(editingTable!=null)editingTable.getModel().setValueAt(original,modelRow,2);super.cancelCellEditing();}
        public Object getCellEditorValue(){
            String raw=component instanceof JToggleButton toggle?(toggle.isSelected()?"1":"0"):component instanceof JComboBox<?> combo?((Choice)combo.getSelectedItem()).value:((JTextField)component).getText();
            return original.changed(raw);
        }
    }
    static String quote(String value){
        StringBuilder out=new StringBuilder("\"");for(char c:value.toCharArray()){switch(c){case '"'->out.append("\\\"");case '\\'->out.append("\\\\");case '\n'->out.append("\\n");case '\r'->out.append("\\r");case '\t'->out.append("\\t");default->{if(c<32)out.append(String.format("\\u%04x",(int)c));else out.append(c);}}}return out.append('"').toString();
    }
}
