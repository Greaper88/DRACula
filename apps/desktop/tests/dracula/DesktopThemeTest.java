// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;
import java.awt.Component;import java.util.*;import javax.swing.*;
/** Appearance changes must preserve local settings drafts and their typed controls. */
public class DesktopThemeTest {
 public static void main(String[] args)throws Exception{SwingUtilities.invokeAndWait(()->{
  DesktopTheme.install(true);Manager.PagePanel p=new Manager.PagePanel("services","Services","Apply service settings");
  p.loadRecords(List.of(new Manager.Record("FIELD",new String[]{"Services","SSH","Enabled","true","configurable","Reviewed","flag"}),new Manager.Record("EDIT",new String[]{"flag","boolean","1","snapshot","","","false","","Enabled","Disabled"}),new Manager.Record("FIELD",new String[]{"Services","Timeout","300","","configurable","Reviewed","number"}),new Manager.Record("EDIT",new String[]{"number","number","300","snapshot","60","1920","false","","",""})),true);
  p.table.editCellAt(1,2);((JTextField)p.table.getEditorComponent()).setText("301");
  if(!DesktopTheme.finishEditors(p))throw new AssertionError("Editor could not finish");
  DesktopTheme.install(false);SwingUtilities.updateComponentTreeUI(p);DesktopTheme.applyTree(p);
  if(!p.changes().equals(Map.of("number","301")))throw new AssertionError("Appearance switch lost a text draft");
  Component value=p.table.prepareRenderer(p.table.getCellRenderer(0,2),0,2);if(!(value instanceof JToggleButton))throw new AssertionError("Appearance switch replaced the typed renderer");
  p.table.editCellAt(0,2);((JToggleButton)p.table.getEditorComponent()).doClick();
  DesktopTheme.finishEditors(p);DesktopTheme.install(true);SwingUtilities.updateComponentTreeUI(p);DesktopTheme.applyTree(p);
  if(!p.changes().equals(Map.of("number","301","flag","0")))throw new AssertionError("Appearance switch lost a toggle draft");
  p.discard.doClick();if(p.dirty())throw new AssertionError("Discard no longer works after a theme switch");
 });System.out.println("PASS theme switching preserves text/toggle drafts, typed controls, and discard");}
}
