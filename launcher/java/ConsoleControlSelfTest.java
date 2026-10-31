// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;
import java.util.*;import com.avocent.kvm.d.*;
/** Local input-policy tests; fake delegates never contact a device. */
public final class ConsoleControlSelfTest {
 public static void main(String[] ignored)throws Exception{
  final List<String> events=new ArrayList<String>();
  bi key=new bi(){public void a(int k){events.add("down:"+k);}public void b(int k){events.add("up:"+k);}public void a(com.avocent.kvm.d.d.d l){}};
  bj mouse=new bj(){public void a(int x,int y){events.add("move");}public void b(int x,int y){}public void c(int x,int y){}public void a(int x,int y,int z,boolean l,boolean m,boolean r,int c){events.add("press");}public void b(int x,int y,int z,boolean l,boolean m,boolean r,int c){events.add("release");}};
  ConsoleControl c=new ConsoleControl(key,mouse,true);c.connected(true);c.keyboard.a(4);c.mouse.a(1,2);if(!events.isEmpty())throw new AssertionError("Input forwarded before enable");
  c.enable(true);c.keyboard.a(4);c.keyboard.a(224);c.keyboard.a(0);c.mouse.a(1,2,0,true,false,false,1);c.enable(false);
  if(!events.contains("down:4")||!events.contains("up:4")||!events.contains("up:224")||!events.contains("release")||events.contains("down:0"))throw new AssertionError("Held inputs not released");
  int count=events.size();c.keyboard.a(5);c.mouse.a(2,3);if(events.size()!=count)throw new AssertionError("Disabled input forwarded");
  c.enable(true);c.connected(false);if(c.enabled()||c.enable(true))throw new AssertionError("Input enabled after disconnect");
  javax.swing.JOptionPane confirmation=new javax.swing.JOptionPane("Power off this server?",javax.swing.JOptionPane.QUESTION_MESSAGE);if(ReadOnlyViewer.hasConnectionError(confirmation))throw new AssertionError("Power confirmation treated as disconnect");
  javax.swing.JOptionPane error=new javax.swing.JOptionPane("Socket connection lost",javax.swing.JOptionPane.ERROR_MESSAGE);if(!ReadOnlyViewer.hasConnectionError(error))throw new AssertionError("Connection error missed");
  System.out.println("PASS gated input, key/button release, disconnect reset and ordinary viewer dialogs");System.exit(0);
 }
}
