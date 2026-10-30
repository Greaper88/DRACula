package dracula;

import javax.swing.*;
import javax.swing.border.*;
import javax.swing.event.*;
import javax.swing.table.*;
import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.List;
import java.util.concurrent.*;

/** Modern desktop shell. Device access stays in the shared, read-only bridge. */
public final class Manager extends JFrame {
    static final Color BG=new Color(242,245,249), INK=new Color(31,43,64), ACCENT=new Color(128,39,65);
    final Path root=Path.of(System.getProperty("dracula.root", ".")).toAbsolutePath();
    final DeviceStore devices=openStore(root.resolve(".local/manager"));
    final JComboBox<String> deviceSelector=new JComboBox<>();
    boolean syncingDevices=false;
    final ExecutorService executor=Executors.newSingleThreadExecutor(r->{Thread t=new Thread(r,"dracula-status");t.setDaemon(true);return t;});
    final DefaultListModel<String> machines=new DefaultListModel<>();
    final JList<String> machineList=new JList<>(machines);
    final JTabbedPane sections=new JTabbedPane();
    final Map<String,PagePanel> pages=new LinkedHashMap<>();
    final JLabel banner=new JLabel("Select a machine and connect"), status=new JLabel("Disconnected");
    final JButton connect=new JButton("Connect"), refresh=new JButton("Refresh tab"), console=new JButton("Open KVM window");
    final JTextField search=new JTextField();
    volatile Bridge bridge;
    volatile int generation=0;
    char[] password=new char[0];
    String username="root",connectedHost="";
    boolean rebuilding=false;
    final Set<Process> consoles=Collections.synchronizedSet(new HashSet<>());

    Manager() {
        super("DRACula · Remote access manager");
        setDefaultCloseOperation(DO_NOTHING_ON_CLOSE);
        setSize(1220,820);setMinimumSize(new Dimension(900,650));setLocationRelativeTo(null);
        JPanel layout=new JPanel(new BorderLayout(16,16));layout.setBackground(BG);layout.setBorder(new EmptyBorder(20,20,14,20));setContentPane(layout);
        JPanel heading=new JPanel(new BorderLayout());heading.setOpaque(false);
        JLabel title=new JLabel("DRACula");title.setFont(new Font(Font.SANS_SERIF,Font.BOLD,30));title.setForeground(ACCENT);
        heading.add(title,BorderLayout.WEST);
        JPanel chooser=new JPanel(new FlowLayout(FlowLayout.CENTER,8,0));chooser.setOpaque(false);chooser.add(new JLabel("Device:"));deviceSelector.setPreferredSize(new Dimension(270,32));chooser.add(deviceSelector);JButton manage=new JButton("Manage devices");chooser.add(manage);heading.add(chooser,BorderLayout.CENTER);manage.addActionListener(e->manageDevices());
        JLabel mode=new JLabel("READ-ONLY ACCESS   ·   DRAC 5");mode.setForeground(ACCENT);heading.add(mode,BorderLayout.EAST);
        layout.add(heading,BorderLayout.NORTH);
        JPanel side=new JPanel(new BorderLayout(8,12));side.setPreferredSize(new Dimension(215,0));side.setOpaque(false);
        JLabel fleet=new JLabel("MACHINES");fleet.setForeground(INK);side.add(fleet,BorderLayout.NORTH);
        ListCellRenderer<? super String> profileRenderer=new DefaultListCellRenderer(){@Override public Component getListCellRendererComponent(JList<?> list,Object value,int index,boolean selected,boolean focus){DeviceStore.Profile profile=devices.profiles.get(Objects.toString(value,""));return super.getListCellRendererComponent(list,profile==null?value:profile.toString(),index,selected,focus);}};
        machineList.setCellRenderer(profileRenderer);deviceSelector.setRenderer(profileRenderer);
        machineList.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);machineList.setFixedCellHeight(44);
        machineList.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,15));side.add(new JScrollPane(machineList),BorderLayout.CENTER);
        JPanel addRemove=new JPanel(new GridLayout(1,2,6,0));addRemove.setOpaque(false);
        JButton add=new JButton("Add"),remove=new JButton("Remove");addRemove.add(add);addRemove.add(remove);side.add(addRemove,BorderLayout.SOUTH);
        add.addActionListener(e->{editProfile(null);});remove.addActionListener(e->removeMachine());
        JPanel content=new JPanel(new BorderLayout(0,12));content.setOpaque(false);
        JPanel top=new JPanel(new BorderLayout(8,10));top.setOpaque(false);
        banner.setFont(new Font(Font.SANS_SERIF,Font.BOLD,19));banner.setForeground(INK);top.add(banner,BorderLayout.NORTH);
        JPanel buttons=new JPanel(new FlowLayout(FlowLayout.LEFT,8,0));buttons.setOpaque(false);
        buttons.add(connect);buttons.add(refresh);buttons.add(console);buttons.add(new JLabel("Filter:"));search.setColumns(17);buttons.add(search);top.add(buttons,BorderLayout.SOUTH);
        content.add(top,BorderLayout.NORTH);content.add(sections,BorderLayout.CENTER);
        JSplitPane split=new JSplitPane(JSplitPane.HORIZONTAL_SPLIT,side,content);split.setBorder(null);split.setDividerSize(8);split.setResizeWeight(0);split.setOpaque(false);layout.add(split,BorderLayout.CENTER);
        status.setForeground(INK);layout.add(status,BorderLayout.SOUTH);
        connect.addActionListener(e->{if(bridge==null)connectDialog();else disconnect();});
        refresh.addActionListener(e->loadSelected(true));console.addActionListener(e->openConsole());
        sections.addChangeListener(e->loadSelected(false));
        search.getDocument().addDocumentListener(new DocumentListener(){public void insertUpdate(DocumentEvent e){filter();}public void removeUpdate(DocumentEvent e){filter();}public void changedUpdate(DocumentEvent e){filter();}});
        machineList.addListSelectionListener(e->{if(!e.getValueIsAdjusting()&&!syncingDevices){syncingDevices=true;deviceSelector.setSelectedItem(machineList.getSelectedValue());syncingDevices=false;disconnect();DeviceStore.Profile selected=devices.profiles.get(machineList.getSelectedValue());banner.setText(selected==null?"Select a machine":selected.toString());}});
        deviceSelector.addActionListener(e->{if(!syncingDevices)machineList.setSelectedValue(deviceSelector.getSelectedItem(),true);});
        addWindowListener(new WindowAdapter(){public void windowClosing(WindowEvent e){disconnect();synchronized(consoles){for(Process p:consoles)p.destroy();}executor.shutdownNow();devices.close();dispose();}});
        loadMachines();machineList.setSelectedValue("192.168.1.253",true);
        placeholder();availability(false);
    }
    void placeholder(){sections.removeAll();JLabel empty=new JLabel("Connect to load the machine’s DRAC tabs and current status.",SwingConstants.CENTER);empty.setForeground(INK);sections.addTab("Overview",empty);}
    void availability(boolean on){refresh.setEnabled(on);console.setEnabled(on);connect.setText(on?"Disconnect":"Connect");}
    static DeviceStore openStore(Path directory){try{return new DeviceStore(directory);}catch(IOException e){throw new IllegalStateException("Cannot open device profiles",e);}}
    void loadMachines(){reloadProfiles(machineList.getSelectedValue());}
    static boolean validHost(String text){String[] p=text.split("\\.",-1);if(p.length!=4)return false;try{for(String s:p)if(!s.matches("[0-9]{1,3}")||Integer.parseInt(s)>255||(s.length()>1&&s.startsWith("0")))return false;return true;}catch(NumberFormatException e){return false;}}
    void reloadProfiles(String selected){
        syncingDevices=true;machines.clear();deviceSelector.removeAllItems();
        for(String host:devices.profiles.keySet()){machines.addElement(host);deviceSelector.addItem(host);}
        if(selected==null||!devices.profiles.containsKey(selected))selected=machines.isEmpty()?null:machines.get(0);
        machineList.setSelectedValue(selected,true);deviceSelector.setSelectedItem(selected);syncingDevices=false;DeviceStore.Profile profile=devices.profiles.get(selected);banner.setText(profile==null?"Select a machine":profile.toString());
    }
    boolean unlockVault(){
        if(devices.unlocked())return true;
        JPasswordField key=new JPasswordField(24),confirm=new JPasswordField(24);JPanel form=new JPanel(new GridLayout(0,1,5,7));
        boolean existing=devices.hasVault();form.add(new JLabel(existing?"Unlock saved device passwords":"Create a password for encrypted credential storage"));form.add(key);
        if(!existing){form.add(new JLabel("Confirm unlock password"));form.add(confirm);}
        if(JOptionPane.showConfirmDialog(this,form,existing?"Unlock passwords":"Set up password storage",JOptionPane.OK_CANCEL_OPTION,JOptionPane.PLAIN_MESSAGE)!=JOptionPane.OK_OPTION){key.setText("");confirm.setText("");return false;}
        char[] first=key.getPassword(),second=confirm.getPassword();key.setText("");confirm.setText("");
        try{
            if(!existing&&!Arrays.equals(first,second)){JOptionPane.showMessageDialog(this,"The unlock passwords do not match.");return false;}
            devices.unlock(first);return true;
        }catch(Exception e){JOptionPane.showMessageDialog(this,"Could not unlock password storage. Check the unlock password.");return false;}
        finally{Arrays.fill(first,'\0');Arrays.fill(second,'\0');}
    }
    void manageDevices(){
        JDialog dialog=new JDialog(this,"Manage devices",true);dialog.setSize(700,420);dialog.setLocationRelativeTo(this);
        DefaultTableModel model=new DefaultTableModel(new String[]{"Name","IP address","Username","Password storage"},0){public boolean isCellEditable(int r,int c){return false;}};
        JTable table=new JTable(model);table.setRowHeight(30);table.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        Runnable refill=()->{model.setRowCount(0);for(DeviceStore.Profile profile:devices.profiles.values())model.addRow(new Object[]{profile.name(),profile.host(),profile.user(),profile.saved()?"Encrypted vault":"Session only"});};refill.run();
        dialog.add(new JScrollPane(table),BorderLayout.CENTER);JPanel buttons=new JPanel(new FlowLayout(FlowLayout.RIGHT));
        JButton add=new JButton("Add device"),edit=new JButton("Edit"),remove=new JButton("Remove"),done=new JButton("Done");
        buttons.add(add);buttons.add(edit);buttons.add(remove);buttons.add(done);dialog.add(buttons,BorderLayout.SOUTH);
        add.addActionListener(e->{editProfile(null);refill.run();});
        edit.addActionListener(e->{int row=table.getSelectedRow();if(row>=0){editProfile(model.getValueAt(row,1).toString());refill.run();}});
        remove.addActionListener(e->{int row=table.getSelectedRow();if(row>=0){removeProfile(model.getValueAt(row,1).toString());refill.run();}});
        done.addActionListener(e->dialog.dispose());dialog.setVisible(true);
    }
    void editProfile(String previous){
        DeviceStore.Profile old=previous==null?null:devices.profiles.get(previous);
        if(old!=null&&old.saved()&&!unlockVault())return;
        JTextField name=new JTextField(old==null?"DRAC 5":old.name()),host=new JTextField(old==null?"":old.host()),user=new JTextField(old==null?"root":old.user());
        JPasswordField secret=new JPasswordField();char[] stored=old==null?new char[0]:devices.password(old.host());secret.setText(new String(stored));Arrays.fill(stored,'\0');
        JCheckBox remember=new JCheckBox("Save password in encrypted local storage",old!=null&&old.saved());
        JPanel form=new JPanel(new GridLayout(0,1,4,5));for(JComponent field:new JComponent[]{new JLabel("Device name"),name,new JLabel("IP address"),host,new JLabel("Username"),user,new JLabel("Password"),secret,remember})form.add(field);
        int choice=JOptionPane.showConfirmDialog(this,form,old==null?"Add device":"Edit device",JOptionPane.OK_CANCEL_OPTION,JOptionPane.PLAIN_MESSAGE);
        if(choice!=JOptionPane.OK_OPTION){secret.setText("");return;}
        String address=host.getText().trim();if(!validHost(address)||user.getText().isBlank()||name.getText().isBlank()){secret.setText("");JOptionPane.showMessageDialog(this,"Enter a name, valid IPv4 address, and username.");return;}
        if(!address.equals(previous)&&devices.profiles.containsKey(address)){secret.setText("");JOptionPane.showMessageDialog(this,"That IP address is already configured.");return;}
        if(remember.isSelected()&&!unlockVault()){secret.setText("");return;}
        char[] value=secret.getPassword();secret.setText("");
        try{devices.put(previous,new DeviceStore.Profile(name.getText().trim(),address,user.getText().trim(),remember.isSelected()),value);disconnect();reloadProfiles(address);}
        catch(Exception e){JOptionPane.showMessageDialog(this,"Could not save the device profile: "+e.getMessage());}
        finally{Arrays.fill(value,'\0');}
    }
    void removeMachine(){String host=machineList.getSelectedValue();if(host!=null)removeProfile(host);}
    void removeProfile(String host){
        if(JOptionPane.showConfirmDialog(this,"Remove "+host+" from this manager?","Remove device",JOptionPane.OK_CANCEL_OPTION)!=JOptionPane.OK_OPTION)return;
        DeviceStore.Profile profile=devices.profiles.get(host);if(profile!=null&&profile.saved()&&!unlockVault())return;
        try{devices.remove(host);disconnect();reloadProfiles(null);}catch(Exception e){JOptionPane.showMessageDialog(this,"Could not remove the device profile.");}
    }
    void connectDialog(){
        String host=machineList.getSelectedValue();if(host==null)return;
        DeviceStore.Profile profile=devices.profiles.get(host);
        if(profile!=null&&profile.saved()&&!unlockVault())return;
        JTextField user=new JTextField(profile==null?username:profile.user(),20);JPasswordField secret=new JPasswordField(20);char[] stored=devices.password(host);secret.setText(new String(stored));Arrays.fill(stored,'\0');
        JCheckBox compatibility=new JCheckBox("Use legacy connection compatibility",true);
        JPanel form=new JPanel(new GridLayout(0,1,4,7));form.add(new JLabel("Connect to "+host));form.add(new JLabel("Username"));form.add(user);form.add(new JLabel("Password"));form.add(secret);form.add(compatibility);
        form.add(new JLabel("Read-only: settings, firmware and power actions stay disabled."));
        if(JOptionPane.showConfirmDialog(this,form,"DRAC connection",JOptionPane.OK_CANCEL_OPTION,JOptionPane.PLAIN_MESSAGE)!=JOptionPane.OK_OPTION){char[] cancelled=secret.getPassword();Arrays.fill(cancelled,'\0');secret.setText("");return;}
        if(!compatibility.isSelected()){secret.setText("");JOptionPane.showMessageDialog(this,"This DRAC 5 profile requires legacy connection compatibility.");return;}
        username=user.getText().trim();password=secret.getPassword();secret.setText("");connectedHost=host;
        int request=++generation;char[] auth=password.clone();String who=username;
        connect.setEnabled(false);status.setText("Connecting to "+host+"…");
        executor.submit(()->{
            Bridge created=null;
            try {
                created=new Bridge(root,host,who,auth);List<Record> catalog=created.readResponse();
                if(catalog.stream().noneMatch(r->r.kind.equals("READY")))throw new IOException(catalog.stream().filter(r->r.kind.equals("ERROR")).map(r->r.fields[0]).findFirst().orElse("Connection failed"));
                Bridge ready=created;
                SwingUtilities.invokeLater(()->{if(request!=generation){ready.close();return;}bridge=ready;buildTabs(catalog);availability(true);connect.setEnabled(true);banner.setText(host+" · DRAC 5");status.setText("Connected · Read-only access");loadSelected(true);});
            }catch(Exception failure){if(created!=null)created.close();SwingUtilities.invokeLater(()->{if(request==generation){status.setText("Connection failed: "+failure.getMessage());connect.setEnabled(true);availability(false);Arrays.fill(password,'\0');}});}
            finally{Arrays.fill(auth,'\0');}
        });
    }
    void disconnect(){
        ++generation;Bridge old=bridge;bridge=null;
        if(old!=null)old.close();Arrays.fill(password,'\0');password=new char[0];connectedHost="";
        rebuilding=true;pages.clear();placeholder();rebuilding=false;
        availability(false);connect.setEnabled(true);status.setText("Disconnected");
    }
    void buildTabs(List<Record> catalog){
        rebuilding=true;sections.removeAll();pages.clear();Map<String,JTabbedPane> groups=new LinkedHashMap<>();
        for(Record r:catalog)if(r.kind.equals("PAGE")&&r.fields.length==4){
            String section=r.fields[1];JTabbedPane group=groups.get(section);
            if(group==null){group=new JTabbedPane();group.addChangeListener(e->loadSelected(false));groups.put(section,group);sections.addTab(section,group);}
            PagePanel panel=new PagePanel(r.fields[0],r.fields[2],r.fields[3]);pages.put(panel.key,panel);group.addTab(r.fields[2],panel);
        }
        rebuilding=false;
    }
    PagePanel selected(){Component c=sections.getSelectedComponent();return c instanceof JTabbedPane t && t.getSelectedComponent() instanceof PagePanel p?p:null;}
    void filter(){PagePanel p=selected();if(p!=null){String term=search.getText();p.sorter.setRowFilter(term.isBlank()?null:RowFilter.regexFilter("(?i)"+java.util.regex.Pattern.quote(term)));}}
    void loadSelected(boolean force){
        if(rebuilding||bridge==null)return;PagePanel panel=selected();if(panel==null||panel.loading||(!force&&panel.loaded)){filter();return;}
        panel.loading=true;panel.message.setText("Reading current status…");int request=generation;Bridge current=bridge;
        executor.submit(()->{
            try {List<Record> result=current.readPage(panel.key);SwingUtilities.invokeLater(()->{if(request!=generation)return;panel.model.setRowCount(0);List<String> errors=new ArrayList<>();for(Record r:result){if(r.kind.equals("ROW")&&r.fields.length==3)panel.model.addRow(r.fields);if(r.kind.equals("ERROR"))errors.add(r.fields[0]);}panel.loaded=true;panel.loading=false;String time=LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss"));panel.message.setText(errors.isEmpty()?"Updated "+time+" · "+panel.model.getRowCount()+" fields":"Unavailable / partial: "+String.join(" · ",errors));status.setText(errors.isEmpty()?"Connected to "+connectedHost+" · Updated "+time:"Some fields could not be read; see tab status");filter();});}
            catch(Exception e){SwingUtilities.invokeLater(()->{if(request==generation){panel.loading=false;panel.message.setText("Read failed: "+e.getMessage());}});}
        });
    }
    void openConsole(){
        if(bridge==null)return;String host=connectedHost,user=username;char[] auth=password.clone();console.setEnabled(false);status.setText("Opening view-only KVM window…");
        Thread task=new Thread(()->{Process proc=null;try{
            ProcessBuilder builder=python(root,"--console");proc=builder.start();consoles.add(proc);
            try(BufferedWriter w=proc.outputWriter(StandardCharsets.UTF_8)){for(String field:List.of(host,user,new String(auth))){w.write(enc(field));w.newLine();}}
            StringBuilder output=new StringBuilder();try(BufferedReader r=proc.inputReader(StandardCharsets.UTF_8)){String line;while((line=r.readLine())!=null)if(output.length()<8000)output.append(line).append('\n');}
            int code=proc.waitFor();String message=code==0?"KVM window closed":"KVM could not open: "+output;
            SwingUtilities.invokeLater(()->{status.setText(message.replace('\n',' '));console.setEnabled(bridge!=null);});
        }catch(Exception e){SwingUtilities.invokeLater(()->{status.setText("KVM launch failed: "+e.getMessage());console.setEnabled(bridge!=null);});}
        finally{Arrays.fill(auth,'\0');if(proc!=null)consoles.remove(proc);}},"dracula-console");task.setDaemon(true);task.start();
    }
    static ProcessBuilder python(Path root,String... flags){
        List<String> cmd=new ArrayList<>(List.of("python3","-m","dracula.manager_bridge"));cmd.addAll(List.of(flags));
        ProcessBuilder b=new ProcessBuilder(cmd);b.directory(root.toFile());b.redirectErrorStream(true);b.environment().put("PYTHONPATH",root.resolve("src").toString());return b;
    }
    static String enc(String text){return Base64.getEncoder().encodeToString(text.getBytes(StandardCharsets.UTF_8));}
    record Record(String kind,String[] fields){}
    static final class Bridge {
        final Process process;final BufferedReader reader;final BufferedWriter writer;
        Bridge(Path root,String host,String user,char[] password)throws IOException{
            process=python(root).start();reader=process.inputReader(StandardCharsets.UTF_8);writer=process.outputWriter(StandardCharsets.UTF_8);
            for(String field:List.of(host,user,new String(password))){writer.write(enc(field));writer.newLine();}writer.flush();
        }
        List<Record> readResponse()throws IOException{
            List<Record> result=new ArrayList<>();String line;
            while((line=reader.readLine())!=null){if(line.equals("END"))return result;String[] pieces=line.split("\t",-1);String[] fields=new String[pieces.length-1];try{for(int i=1;i<pieces.length;i++)fields[i-1]=new String(Base64.getDecoder().decode(pieces[i]),StandardCharsets.UTF_8);}catch(IllegalArgumentException e){throw new IOException("Invalid local bridge response");}result.add(new Record(pieces[0],fields));}
            throw new IOException("Device session closed");
        }
        synchronized List<Record> readPage(String key)throws IOException{writer.write("READ\t"+key+"\n");writer.flush();return readResponse();}
        void close(){Thread cleanup=new Thread(()->{try{writer.write("QUIT\n");writer.flush();if(!process.waitFor(3,TimeUnit.SECONDS))process.destroy();}catch(Exception ignored){process.destroy();}},"dracula-disconnect");cleanup.setDaemon(true);cleanup.start();}
    }
    static final class PagePanel extends JPanel {
        final String key;final DefaultTableModel model=new DefaultTableModel(new String[]{"Group / record","Field","Value"},0){public boolean isCellEditable(int r,int c){return false;}};
        final JTable table=new JTable(model);final TableRowSorter<DefaultTableModel> sorter=new TableRowSorter<>(model);final JLabel message=new JLabel("Not loaded yet");boolean loaded=false,loading=false;
        PagePanel(String key,String title,String actions){
            super(new BorderLayout(0,10));this.key=key;setBorder(new EmptyBorder(14,14,14,14));setBackground(Color.WHITE);
            JLabel name=new JLabel(title);name.setFont(new Font(Font.SANS_SERIF,Font.BOLD,19));add(name,BorderLayout.NORTH);
            table.setRowSorter(sorter);table.setRowHeight(29);table.setFillsViewportHeight(true);table.setShowGrid(false);table.setIntercellSpacing(new Dimension(0,0));table.getTableHeader().setReorderingAllowed(false);
            table.getColumnModel().getColumn(0).setPreferredWidth(280);table.getColumnModel().getColumn(1).setPreferredWidth(220);table.getColumnModel().getColumn(2).setPreferredWidth(370);
            table.setDefaultRenderer(Object.class,new DefaultTableCellRenderer(){public Component getTableCellRendererComponent(JTable t,Object v,boolean selected,boolean focus,int row,int col){Component c=super.getTableCellRendererComponent(t,v,selected,focus,row,col);if(!selected)c.setBackground(row%2==0?Color.WHITE:new Color(246,248,251));setBorder(new EmptyBorder(0,7,0,7));setToolTipText(Objects.toString(v,""));return c;}});
            add(new JScrollPane(table),BorderLayout.CENTER);JPanel foot=new JPanel(new BorderLayout(0,9));foot.setOpaque(false);message.setForeground(INK);foot.add(message,BorderLayout.NORTH);
            if(!actions.isBlank()){JPanel disabled=new JPanel(new FlowLayout(FlowLayout.LEFT,6,4));disabled.setOpaque(false);for(String action:actions.split("; ")){JButton b=new JButton(action);b.setEnabled(false);b.setToolTipText("Requires explicit approval; writes are not enabled in this version.");disabled.add(b);}foot.add(disabled,BorderLayout.CENTER);JLabel note=new JLabel("Actions are disabled during read-only access.");note.setForeground(ACCENT);foot.add(note,BorderLayout.SOUTH);}
            add(foot,BorderLayout.SOUTH);
        }
    }
    static void configureLookAndFeel(){
        System.setProperty("awt.useSystemAAFontSettings","on");System.setProperty("swing.aatext","true");
        try{UIManager.setLookAndFeel("javax.swing.plaf.nimbus.NimbusLookAndFeel");}catch(Exception ignored){}
        UIManager.put("control",BG);UIManager.put("nimbusBase",ACCENT);UIManager.put("nimbusBlueGrey",new Color(220,226,235));UIManager.put("nimbusFocus",ACCENT);
        for(Object key:new ArrayList<>(UIManager.getDefaults().keySet()))if(UIManager.get(key) instanceof Font)UIManager.put(key,new javax.swing.plaf.FontUIResource(Font.SANS_SERIF,Font.PLAIN,13));
    }
    public static void main(String[] args)throws Exception{
        configureLookAndFeel();
        SwingUtilities.invokeLater(()->new Manager().setVisible(true));
    }
}
