// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;
import javax.swing.*;
import java.awt.*;
public class FieldCellsTest {
 public static void main(String[] args)throws Exception{
  SwingUtilities.invokeAndWait(()->{
   Manager.PagePanel panel=new Manager.PagePanel("services","Services","Apply service settings");
   panel.model.addRow(FieldCells.row(new String[]{"Services","SSH enabled","Enabled","true","configurable","Mapped form control"}));
   panel.model.addRow(FieldCells.row(new String[]{"Services","Active sessions","1","","read-only","Reported count"}));
   if(panel.model.isCellEditable(0,2))throw new AssertionError("Device field editable");
   Component c=panel.table.prepareRenderer(panel.table.getCellRenderer(0,2),0,2);
   if(!(c instanceof JToggleButton toggle)||toggle.isEnabled()||!toggle.isSelected()||toggle.getActionListeners().length!=0)throw new AssertionError("Expected passive selected toggle");
   c=panel.table.prepareRenderer(panel.table.getCellRenderer(1,2),1,2);
   if(c instanceof JToggleButton)throw new AssertionError("Count rendered as toggle");
   if(!panel.model.getValueAt(0,3).toString().contains("locked"))throw new AssertionError("Configurable fields must be marked locked");
   panel.sorter.toggleSortOrder(2);panel.sorter.setRowFilter(javax.swing.RowFilter.regexFilter("Enabled"));
   if(panel.table.getRowCount()!=1)throw new AssertionError("Typed values must remain filterable");
  });System.out.println("PASS passive switches, counters, access labels and filtering");
 }
}
