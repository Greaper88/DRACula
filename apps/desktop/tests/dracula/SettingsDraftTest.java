// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;
import javax.swing.*;import java.util.*;
public class SettingsDraftTest {
 public static void main(String[] args)throws Exception{SwingUtilities.invokeAndWait(()->{
  var records=List.of(new Manager.Record("FIELD",new String[]{"Services","SSH","Enabled","true","configurable","Reviewed","key"}),new Manager.Record("EDIT",new String[]{"key","boolean","1","revision","","","false","","Enabled","Disabled"}));
  Manager.PagePanel panel=new Manager.PagePanel("services","Services","Apply service settings");
  panel.loadRecords(records,false);if(panel.table.isCellEditable(0,2))throw new AssertionError("Unavailable fields editable");
  panel.loadRecords(records,true);if(!panel.table.isCellEditable(0,2))throw new AssertionError("Supported field not editable");
  if(panel.apply.isEnabled())throw new AssertionError("Apply enabled without changes");
  panel.table.editCellAt(0,2);JToggleButton toggle=(JToggleButton)panel.table.getEditorComponent();toggle.doClick();
  if(!panel.changes().equals(Map.of("key","0"))||!panel.apply.isEnabled())throw new AssertionError("Toggle did not stage locally");
  panel.discard.doClick();if(panel.dirty()||panel.apply.isEnabled())throw new AssertionError("Discard did not clear draft");
  
  panel.loadRecords(List.of(new Manager.Record("FIELD",new String[]{"Services","Timeout","300","","configurable","Reviewed","number"}),new Manager.Record("EDIT",new String[]{"number","number","300","revision","60","1920","false","","",""})),true);
  panel.table.editCellAt(0,2);((JTextField)panel.table.getEditorComponent()).setText("301");if(!panel.apply.isEnabled()||!panel.changes().equals(Map.of("number","301")))throw new AssertionError("Typing must immediately enable Apply without sending anything");panel.table.getCellEditor().cancelCellEditing();if(panel.dirty())throw new AssertionError("Escape must restore the cell draft");
  panel.setBusy(true);if(panel.table.isCellEditable(0,2))throw new AssertionError("Editor usable during Apply");
  if(!FieldCells.quote("a\"b\\c\n").equals("\"a\\\"b\\\\c\\n\""))throw new AssertionError("Unsafe JSON string encoding");
 });System.out.println("PASS staged toggles, unavailable fields, discard, busy state and safe request encoding");}
}
