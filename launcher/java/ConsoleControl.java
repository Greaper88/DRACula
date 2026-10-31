// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
import javax.swing.*;
import com.avocent.kvm.d.*;

/** Per-viewer input gate. Native hooks are never installed. */
final class ConsoleControl {
    final boolean capable;
    private final bi outgoingKeys;private final bj outgoingMouse;
    private final Set<Integer> keys=new HashSet<Integer>();private final Set<Integer> buttons=new HashSet<Integer>();
    private boolean connected,enabled;private int x,y;private long heartbeat;
    private final boolean leased="0".equals(System.getenv("DRACULA_VIEWER_CHROME"));
    private final String endpoint=System.getenv("DRACULA_INPUT_ENDPOINT");
    private final String token=UUID.randomUUID().toString();
    private static ConsoleControl current;
    ConsoleControl(bi keys,bj mouse,boolean capable){outgoingKeys=keys;outgoingMouse=mouse;this.capable=capable;if(capable)current=this;}
    static ConsoleControl current(){return current;}
    synchronized boolean enabled(){return capable&&connected&&enabled;}
    synchronized void connected(boolean value){if(!value)enable(false);connected=value;}
    synchronized boolean enable(boolean value){
        if(!value){
            // Release only keys/buttons this viewer actually forwarded.
            for(Integer key:new HashSet<Integer>(keys))try{outgoingKeys.b(key);}catch(IOException ignored){}
            for(Integer b:new HashSet<Integer>(buttons))try{outgoingMouse.b(x,y,0,b==1,b==2,b==3,1);}catch(IOException ignored){}
            keys.clear();buttons.clear();enabled=false;
        }else if(capable&&connected){enabled=true;heartbeat=System.nanoTime();}
        publish();ConsoleChrome.refreshMode();return enabled();
    }
    void publish(){String path=System.getenv("DRACULA_INPUT_STATE");if(path!=null)try{Files.write(Paths.get(path), (enabled()?"enabled":"disabled").getBytes("UTF-8"));}catch(IOException ignored){}}
    final bi keyboard=new bi(){
        public void a(int key)throws IOException{synchronized(ConsoleControl.this){if(enabled()&&key>=4&&key<=231){keys.add(key);outgoingKeys.a(key);}}}
        public void b(int key)throws IOException{synchronized(ConsoleControl.this){if(keys.remove(key))outgoingKeys.b(key);}}
        public void a(com.avocent.kvm.d.d.d listener){} // No global/native hook listeners.
    };
    final bj mouse=new bj(){
        public void a(int a,int b)throws IOException{synchronized(ConsoleControl.this){if(enabled()){x=a;y=b;outgoingMouse.a(a,b);}}}
        public void b(int a,int b)throws IOException{synchronized(ConsoleControl.this){if(enabled()){x=a;y=b;outgoingMouse.b(a,b);}}}
        public void c(int a,int b)throws IOException{synchronized(ConsoleControl.this){if(enabled()){x=a;y=b;outgoingMouse.c(a,b);}}}
        public void a(int a,int b,int z,boolean left,boolean middle,boolean right,int clicks)throws IOException{synchronized(ConsoleControl.this){if(enabled()){x=a;y=b;if(left)buttons.add(1);if(middle)buttons.add(2);if(right)buttons.add(3);outgoingMouse.a(a,b,z,left,middle,right,clicks);}}}
        public void b(int a,int b,int z,boolean left,boolean middle,boolean right,int clicks)throws IOException{synchronized(ConsoleControl.this){if(enabled()){x=a;y=b;if(left)buttons.remove(1);if(middle)buttons.remove(2);if(right)buttons.remove(3);outgoingMouse.b(a,b,z,left,middle,right,clicks);}}}
    };
    void watch(final JFrame frame){
        if(!capable)return;
        frame.addWindowFocusListener(new WindowAdapter(){public void windowLostFocus(WindowEvent event){Window next=event.getOppositeWindow();while(next!=null&&next!=frame)next=next.getOwner();if(next!=frame)enable(false);}});
        // Observe only this viewer's own focused window, without a native hook.
        KeyboardFocusManager.getCurrentKeyboardFocusManager().addKeyEventDispatcher(new KeyEventDispatcher(){public boolean dispatchKeyEvent(KeyEvent e){
            if(SwingUtilities.getWindowAncestor(e.getComponent())==frame&&e.isControlDown()&&e.isAltDown()&&e.isShiftDown()){enable(false);e.consume();return true;}return false;
        }});
    }
    void startBroker(){
        if(!capable||endpoint==null)return;
        Thread thread=new Thread(new Runnable(){public void run(){
            try(ServerSocket server=new ServerSocket(0,8,InetAddress.getByName("127.0.0.1"))){
                server.setSoTimeout(500);
                Path path=Paths.get(endpoint);Path temp=Paths.get(endpoint+".tmp");Files.write(temp,(server.getLocalPort()+"\n"+token).getBytes("UTF-8"));Files.move(temp,path,StandardCopyOption.REPLACE_EXISTING);
                while(true){
                    if(leased&&enabled()&&System.nanoTime()-heartbeat>3000000000L)enable(false);
                    try(Socket socket=server.accept()){
                        socket.setSoTimeout(1000);BufferedReader input=new BufferedReader(new InputStreamReader(socket.getInputStream(),"UTF-8"));
                        StringBuilder line=new StringBuilder();int ch;while(line.length()<128&&(ch=input.read())!=-1&&ch!='\n')line.append((char)ch);
                        String[] parts=line.toString().split(" ",2);String answer="disabled";
                        if(parts.length==2&&token.equals(parts[0])){
                            if(parts[1].equals("enable"))enable(true);
                            else if(parts[1].equals("disable")||parts[1].equals("release"))enable(false);
                            else if(parts[1].equals("ping"))heartbeat=System.nanoTime();
                            else if(!parts[1].equals("status")){enable(false);throw new IOException("Invalid control request");}
                            answer=enabled()?"enabled":"disabled";
                        }
                        socket.getOutputStream().write((answer+"\n").getBytes("UTF-8"));
                    }catch(SocketTimeoutException ignored){}
                }
            }catch(IOException ignored){enable(false);}
        }},"dracula-private-input-control");thread.setDaemon(true);thread.start();
    }
}
