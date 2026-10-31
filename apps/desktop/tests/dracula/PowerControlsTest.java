// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;
import javax.swing.*;import java.util.*;
public class PowerControlsTest {
 public static void main(String[] args)throws Exception{SwingUtilities.invokeAndWait(()->{
  Manager.PagePanel p=new Manager.PagePanel("power","Power","Power on; Power off; Reset; Graceful shutdown");
  p.loadRecords(List.of(new Manager.Record("POWER",new String[]{"revision","ON","DRAC HTTP"}),new Manager.Record("POWER_ACTION",new String[]{"on","Power on","false","Requires off","DRAC HTTP"}),new Manager.Record("POWER_ACTION",new String[]{"reset","Reset","true","","DRAC HTTP"})),true);
  if(p.powerButtons.get("on").isEnabled()||!p.powerButtons.get("reset").isEnabled())throw new AssertionError("Invalid state availability");
  if(p.powerButtons.get("soft").isVisible())throw new AssertionError("Unsupported power operation visible");
  List<String> called=new ArrayList<>();p.powerAction=called::add;p.powerButtons.get("reset").doClick();if(!called.equals(List.of("reset")))throw new AssertionError("Wrong reviewed action");
  p.setBusy(true);if(p.powerButtons.get("reset").isEnabled())throw new AssertionError("Power active during review");p.setBusy(false);p.needsCheck=true;p.updatePending();if(p.powerButtons.get("reset").isEnabled())throw new AssertionError("Power active after unknown result");
 });System.out.println("PASS power state, capability hiding, review callback and uncertain-result lock");}
}
