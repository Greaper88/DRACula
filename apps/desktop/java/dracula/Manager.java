// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
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

/** Modern desktop shell. Device access stays in the shared management bridge. */
public final class Manager extends JFrame {
    final Path root=Path.of(System.getProperty("dracula.root", ".")).toAbsolutePath();
    final DeviceStore devices=openStore(Path.of(System.getProperty("dracula.state",root.resolve(".local").toString())).resolve("manager"));
    final JComboBox<String> deviceSelector=new JComboBox<>();
    boolean syncingDevices=false;
    final ExecutorService executor=Executors.newSingleThreadExecutor(r->{Thread t=new Thread(r,"dracula-status");t.setDaemon(true);return t;});
    final DefaultListModel<String> machines=new DefaultListModel<>();
    final JList<String> machineList=new JList<>(machines);
    final JTabbedPane sections=new JTabbedPane();
    final Map<String,PagePanel> pages=new LinkedHashMap<>();
    final JLabel banner=new JLabel("Select a machine and connect"), status=new JLabel("Disconnected"), mode=new JLabel("READ-ONLY ACCESS   ·   DRAC 5");
    final JButton theme=new JButton(DesktopTheme.action());
    final JButton connect=new JButton("Connect"), refresh=new JButton("Refresh tab"), console=new JButton("Open KVM window");
    final JTextField search=new JTextField();
    volatile Bridge bridge;
    volatile int generation=0;
    char[] password=new char[0];
    String username="root",connectedHost="";
    boolean rebuilding=false,kvmSupported=false;
    ConsoleStatusDialog consoleStatus;
    final Set<Process> consoles=Collections.synchronizedSet(new HashSet<>());

    Manager() {
        super("DRACula · Remote access manager");
        setDefaultCloseOperation(DO_NOTHING_ON_CLOSE);
        setSize(1220,820);setMinimumSize(new Dimension(900,650));setLocationRelativeTo(null);
        JPanel layout=new JPanel(new BorderLayout(16,16));DesktopTheme.style(layout,"background");layout.setBorder(new EmptyBorder(20,20,14,20));setContentPane(layout);
        JPanel heading=new JPanel(new BorderLayout());heading.setOpaque(false);
        JLabel title=new JLabel("DRACula");title.setFont(new Font(Font.SANS_SERIF,Font.BOLD,30));DesktopTheme.style(title,"accent");
        JPanel brand=new JPanel(new FlowLayout(FlowLayout.LEFT,10,0));brand.setOpaque(false);brand.add(title);brand.add(theme);heading.add(brand,BorderLayout.WEST);
        theme.addActionListener(e->changeTheme());updateThemeAction();DesktopTheme.style(connect,"primary");
        JPanel chooser=new JPanel(new FlowLayout(FlowLayout.CENTER,8,0));chooser.setOpaque(false);chooser.add(new JLabel("Device:"));deviceSelector.setPreferredSize(new Dimension(270,32));chooser.add(deviceSelector);JButton manage=new JButton("Manage devices");chooser.add(manage);heading.add(chooser,BorderLayout.CENTER);manage.addActionListener(e->manageDevices());
        DesktopTheme.style(mode,"accent");mode.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,11));heading.add(mode,BorderLayout.EAST);
        layout.add(heading,BorderLayout.NORTH);
        JPanel side=new JPanel(new BorderLayout(8,12));side.setPreferredSize(new Dimension(215,0));side.setOpaque(false);
        JLabel fleet=new JLabel("MACHINES");DesktopTheme.style(fleet,"muted");side.add(fleet,BorderLayout.NORTH);
        ListCellRenderer<? super String> profileRenderer=new DefaultListCellRenderer(){@Override public Component getListCellRendererComponent(JList<?> list,Object value,int index,boolean selected,boolean focus){DeviceStore.Profile profile=devices.profiles.get(Objects.toString(value,""));return super.getListCellRendererComponent(list,profile==null?value:profile.toString(),index,selected,focus);}};
        machineList.setCellRenderer(profileRenderer);deviceSelector.setRenderer(profileRenderer);
        machineList.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);machineList.setFixedCellHeight(44);
        machineList.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,15));side.add(new JScrollPane(machineList),BorderLayout.CENTER);
        JPanel addRemove=new JPanel(new GridLayout(1,2,6,0));addRemove.setOpaque(false);
        JButton add=new JButton("Add"),remove=new JButton("Remove");addRemove.add(add);addRemove.add(remove);side.add(addRemove,BorderLayout.SOUTH);
        add.addActionListener(e->{editProfile(null);});remove.addActionListener(e->removeMachine());
        JPanel content=new JPanel(new BorderLayout(0,12));content.setOpaque(false);
        JPanel top=new JPanel(new BorderLayout(8,10));top.setOpaque(false);
        banner.setFont(new Font(Font.SANS_SERIF,Font.BOLD,19));DesktopTheme.style(banner,"ink");top.add(banner,BorderLayout.NORTH);
        JPanel buttons=new JPanel(new FlowLayout(FlowLayout.LEFT,8,0));buttons.setOpaque(false);
        buttons.add(connect);buttons.add(refresh);buttons.add(console);buttons.add(new JLabel("Filter:"));search.setColumns(17);buttons.add(search);top.add(buttons,BorderLayout.SOUTH);
        content.add(top,BorderLayout.NORTH);content.add(sections,BorderLayout.CENTER);
        JSplitPane split=new JSplitPane(JSplitPane.HORIZONTAL_SPLIT,side,content);split.setBorder(null);split.setDividerSize(8);split.setResizeWeight(0);split.setOpaque(false);layout.add(split,BorderLayout.CENTER);
        DesktopTheme.style(status,"muted");layout.add(status,BorderLayout.SOUTH);
        connect.addActionListener(e->{if(bridge==null)connectDialog();else disconnect();});
        refresh.addActionListener(e->loadSelected(true));console.addActionListener(e->openConsole());
        sections.addChangeListener(e->loadSelected(false));
        search.getDocument().addDocumentListener(new DocumentListener(){public void insertUpdate(DocumentEvent e){filter();}public void removeUpdate(DocumentEvent e){filter();}public void changedUpdate(DocumentEvent e){filter();}});
        machineList.addListSelectionListener(e->{if(!e.getValueIsAdjusting()&&!syncingDevices){syncingDevices=true;deviceSelector.setSelectedItem(machineList.getSelectedValue());syncingDevices=false;disconnect();DeviceStore.Profile selected=devices.profiles.get(machineList.getSelectedValue());banner.setText(selected==null?"Select a machine":selected.toString());}});
        deviceSelector.addActionListener(e->{if(!syncingDevices)machineList.setSelectedValue(deviceSelector.getSelectedItem(),true);});
        addWindowListener(new WindowAdapter(){public void windowClosing(WindowEvent e){if(settingsInProgress()){JOptionPane.showMessageDialog(Manager.this,"Wait for Apply to finish or cancel the settings review first.");return;}disconnect();synchronized(consoles){for(Process p:consoles)p.destroy();}executor.shutdownNow();devices.close();dispose();}});
        loadMachines();
        placeholder();availability(false);DesktopTheme.applyTree(this);
    }
    void placeholder(){sections.removeAll();JLabel empty=new JLabel("Connect to load the machine’s DRAC tabs and current status.",SwingConstants.CENTER);DesktopTheme.style(empty,"muted");sections.addTab("Overview",empty);}
    void availability(boolean on){refresh.setEnabled(on);console.setEnabled(on&&kvmSupported);console.setVisible(on&&kvmSupported);connect.setText(on?"Disconnect":"Connect");}
    static DeviceStore openStore(Path directory){try{return new DeviceStore(directory);}catch(IOException e){throw new IllegalStateException("Cannot open device profiles",e);}}
    void loadMachines(){reloadProfiles(machineList.getSelectedValue());}
    static boolean validHost(String text){String[] p=text.split("\\.",-1);if(p.length!=4)return false;try{for(String s:p)if(!s.matches("[0-9]{1,3}")||Integer.parseInt(s)>255||(s.length()>1&&s.startsWith("0")))return false;return true;}catch(NumberFormatException e){return false;}}
    void reloadProfiles(String selected){
        syncingDevices=true;machines.clear();deviceSelector.removeAllItems();
        for(String host:devices.profiles.keySet()){machines.addElement(host);deviceSelector.addItem(host);}
        if(selected==null||!devices.profiles.containsKey(selected))selected=machines.isEmpty()?null:machines.get(0);
        machineList.setSelectedValue(selected,true);deviceSelector.setSelectedItem(selected);syncingDevices=false;DeviceStore.Profile profile=devices.profiles.get(selected);banner.setText(profile==null?"Add a device using Manage devices":profile.toString());connect.setEnabled(profile!=null);
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
        if(settingsInProgress()){JOptionPane.showMessageDialog(this,"Finish or cancel the settings review first.");return;}
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

        JPanel form=new JPanel(new GridLayout(0,1,4,7));form.add(new JLabel("Connect to "+host));form.add(new JLabel("Username"));form.add(user);form.add(new JLabel("Password"));form.add(secret);
        form.add(new JLabel("Settings and power actions require a separate review and confirmation."));
        if(JOptionPane.showConfirmDialog(this,form,"Device connection",JOptionPane.OK_CANCEL_OPTION,JOptionPane.PLAIN_MESSAGE)!=JOptionPane.OK_OPTION){char[] cancelled=secret.getPassword();Arrays.fill(cancelled,'\0');secret.setText("");return;}
        username=user.getText().trim();password=secret.getPassword();secret.setText("");connectedHost=host;
        int request=++generation;char[] auth=password.clone();String who=username;
        connect.setEnabled(false);status.setText("Connecting to "+host+"…");
        executor.submit(()->{
            Bridge created=null;
            try {
                created=new Bridge(root,host,who,auth);List<Record> catalog=created.readResponse();
                if(catalog.stream().noneMatch(r->r.kind.equals("READY")))throw new IOException(catalog.stream().filter(r->r.kind.equals("ERROR")).map(r->r.fields[0]).findFirst().orElse("Connection failed"));
                Bridge ready=created;
                SwingUtilities.invokeLater(()->{if(request!=generation){ready.close();return;}bridge=ready;mode.setText("CONFIRMED SETTINGS · KVM VIEW ONLY");buildTabs(catalog);applyCapabilities(catalog);availability(true);connect.setEnabled(true);banner.setText(host+" · Management controller");status.setText("Connected · Changes require confirmation");loadSelected(true);});
            }catch(Exception failure){if(created!=null)created.close();SwingUtilities.invokeLater(()->{if(request==generation){status.setText("Connection failed: "+failure.getMessage());connect.setEnabled(true);availability(false);Arrays.fill(password,'\0');}});}
            finally{Arrays.fill(auth,'\0');}
        });
    }
    void disconnect(){
        if(settingsInProgress()){status.setText("Finish or cancel the settings review first.");return;}
        ++generation;Bridge old=bridge;bridge=null;mode.setText("READ-ONLY ACCESS · DRAC 5");
        if(consoleStatus!=null){consoleStatus.cancelled=true;consoleStatus.dispose();consoleStatus=null;}
        synchronized(consoles){for(Process process:consoles)process.destroy();}
        if(old!=null)old.close();Arrays.fill(password,'\0');password=new char[0];connectedHost="";
        rebuilding=true;pages.clear();placeholder();rebuilding=false;
        availability(false);connect.setEnabled(true);status.setText("Disconnected");
    }
    void buildTabs(List<Record> catalog){
        rebuilding=true;sections.removeAll();pages.clear();Map<String,JTabbedPane> groups=new LinkedHashMap<>();
        for(Record r:catalog)if(r.kind.equals("PAGE")&&r.fields.length==4){
            String section=r.fields[1];JTabbedPane group=groups.get(section);
            if(group==null){group=new JTabbedPane();group.addChangeListener(e->loadSelected(false));groups.put(section,group);sections.addTab(section,group);}
            PagePanel panel=new PagePanel(r.fields[0],r.fields[2],r.fields[3]);panel.apply.addActionListener(e->applySettings(panel));panel.powerAction=action->reviewAction(panel,action);pages.put(panel.key,panel);group.addTab(r.fields[2],panel);
        }
        rebuilding=false;
    }
    PagePanel selected(){Component c=sections.getSelectedComponent();return c instanceof JTabbedPane t && t.getSelectedComponent() instanceof PagePanel p?p:null;}
    void filter(){PagePanel p=selected();if(p!=null){String term=search.getText();p.sorter.setRowFilter(term.isBlank()?null:RowFilter.regexFilter("(?i)"+java.util.regex.Pattern.quote(term)));}}
    void loadSelected(boolean force){
        if(rebuilding||bridge==null)return;PagePanel panel=selected();if(panel==null||panel.loading||(!force&&panel.loaded)){filter();return;}
        if(panel.busy)return;
        if(force&&panel.dirty()&&JOptionPane.showConfirmDialog(this,panel.needsCheck?"The submission was not verified. Discard the draft and read current settings?":"Discard staged changes and refresh? Nothing has been sent.","Discard staged changes",JOptionPane.OK_CANCEL_OPTION)!=JOptionPane.OK_OPTION)return;
        panel.loading=true;panel.message.setText("Reading current status…");int request=generation;Bridge current=bridge;
        executor.submit(()->{
            try {List<Record> result=current.readPage(panel.key);SwingUtilities.invokeLater(()->{if(request!=generation)return;List<String> errors=new ArrayList<>();for(Record r:result)if(r.kind.equals("ERROR"))errors.add(r.fields[0]);applyCapabilities(result);panel.loadRecords(result,validHost(connectedHost));panel.loaded=true;panel.loading=false;String time=LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm:ss"));panel.message.setText(errors.isEmpty()?"Updated "+time+" · "+panel.model.getRowCount()+" fields":"Unavailable / partial: "+String.join(" · ",errors));status.setText(errors.isEmpty()?"Connected to "+connectedHost+" · Updated "+time:"Some fields could not be read; see tab status");filter();if(selected()!=panel)loadSelected(false);});}
            catch(Exception e){SwingUtilities.invokeLater(()->{if(request==generation){panel.loading=false;panel.message.setText("Read failed: "+e.getMessage());}});}
        });
    }
    boolean settingsInProgress(){return pages.values().stream().anyMatch(panel->panel.busy);}
    void settingsBusy(PagePanel panel,boolean busy){panel.setBusy(busy);boolean active=settingsInProgress();connect.setEnabled(!active);deviceSelector.setEnabled(!active);machineList.setEnabled(!active);}
    void applyCapabilities(List<Record> records){
        Set<String> supported=new HashSet<>();
        for(Record r:records){if(r.kind.equals("CAPABILITY")&&r.fields.length==1)supported.add(r.fields[0]);if(r.kind.equals("FEATURES")&&r.fields.length==3){kvmSupported=r.fields[0].equals("true")&&Boolean.parseBoolean(System.getProperty("dracula.kvm.supported","true"));console.setVisible(kvmSupported);console.setEnabled(bridge!=null&&kvmSupported);mode.setText(r.fields[2]+" · "+(r.fields[1].equals("true")?"CONFIRMED SETTINGS":"STATUS AND CONFIRMED POWER"));}}
        if(supported.isEmpty())return;
        rebuilding=true;
        for(int i=sections.getTabCount()-1;i>=0;i--){JTabbedPane group=(JTabbedPane)sections.getComponentAt(i);for(int j=group.getTabCount()-1;j>=0;j--){PagePanel p=(PagePanel)group.getComponentAt(j);if(!supported.contains(p.key)){group.removeTabAt(j);pages.remove(p.key);}}if(group.getTabCount()==0)sections.removeTabAt(i);}
        rebuilding=false;
    }
    void applySettings(PagePanel panel){reviewAction(panel,null);}
    void reviewAction(PagePanel panel,String powerAction){
        if(bridge==null||!validHost(connectedHost)||panel.busy)return;
        if(panel.table.isEditing()&&!panel.table.getCellEditor().stopCellEditing())return;
        boolean power=powerAction!=null;Map<String,String> changes=panel.changes();if(!power&&changes.isEmpty())return;
        int request=generation;Bridge current=bridge;String target=connectedHost;String revision=power?panel.powerRevision:panel.revision();settingsBusy(panel,true);panel.message.setText("Preparing review · No settings sent…");
        StringJoiner fields=new StringJoiner(",","{","}");changes.forEach((key,value)->fields.add(FieldCells.quote(key)+":"+FieldCells.quote(value)));
        String json=power?"{\"op\":\"power-review\",\"action\":"+FieldCells.quote(powerAction)+",\"revision\":"+FieldCells.quote(revision)+"}":"{\"op\":\"review\",\"page\":"+FieldCells.quote(panel.key)+",\"revision\":"+FieldCells.quote(revision)+",\"changes\":"+fields+"}";
        executor.submit(()->{try{
            List<Record> records=current.settings(json);Record review=records.stream().filter(r->r.kind.equals("REVIEW")&&r.fields.length==5).findFirst().orElseThrow(()->new IOException("No settings review returned"));
            SwingUtilities.invokeLater(()->{
                if(request!=generation||bridge!=current){settingsBusy(panel,false);return;}
                if(!review.fields[1].equals(target)){settingsBusy(panel,false);panel.message.setText("Unexpected review target; nothing sent");return;}
                DefaultTableModel model=new DefaultTableModel(new String[]{"Setting","Current","Proposed"},0){public boolean isCellEditable(int r,int c){return false;}};
                for(Record row:records)if(row.kind.equals("CHANGE")&&row.fields.length==4)model.addRow(new String[]{row.fields[0]+" / "+row.fields[1],row.fields[2],row.fields[3]});
                JTable table=new JTable(model);DefaultTableCellRenderer reviewRenderer=new DefaultTableCellRenderer();reviewRenderer.putClientProperty("html.disable",Boolean.TRUE);table.setDefaultRenderer(Object.class,reviewRenderer);table.setRowHeight(30);table.setPreferredScrollableViewportSize(new Dimension(740,Math.min(320,Math.max(90,model.getRowCount()*30+25))));
                JPanel content=new JPanel(new BorderLayout(0,12));content.add(new JLabel("Apply to "+review.fields[1]+" · "+review.fields[2]),BorderLayout.NORTH);content.add(new JScrollPane(table),BorderLayout.CENTER);
                JTextArea warning=new JTextArea(review.fields[4]+" Confirmation must be submitted within "+review.fields[3]+" seconds.");warning.setLineWrap(true);warning.setWrapStyleWord(true);warning.setEditable(false);warning.setOpaque(false);warning.setRows(4);content.add(warning,BorderLayout.SOUTH);
                int answer=JOptionPane.showOptionDialog(this,content,(power?"Confirm power action for ":"Confirm settings for ")+target,JOptionPane.OK_CANCEL_OPTION,JOptionPane.WARNING_MESSAGE,null,new Object[]{(power?"Confirm power action on ":"Confirm and apply to ")+target,"Cancel"},"Cancel");
                if(answer!=JOptionPane.OK_OPTION||request!=generation||bridge!=current){
                    settingsBusy(panel,false);panel.message.setText("Review cancelled · Nothing sent");executor.submit(()->{try{current.settings("{\"op\":"+FieldCells.quote(power?"power-cancel":"cancel")+",\"token\":"+FieldCells.quote(review.fields[0])+"}");}catch(Exception ignored){}});return;
                }
                panel.message.setText("Applying the confirmed batch · Checking reported settings…");
                executor.submit(()->{try{
                    List<Record> applied=current.settings("{\"op\":"+FieldCells.quote(power?"power-confirm":"confirm")+",\"token\":"+FieldCells.quote(review.fields[0])+",\"confirmed\":true}");
                    Record result=applied.stream().filter(r->r.kind.equals("RESULT")&&r.fields.length==3).findFirst().orElseThrow(()->new IOException("No Apply result returned"));
                    SwingUtilities.invokeLater(()->{if(request!=generation||bridge!=current)return;settingsBusy(panel,false);panel.message.setText(result.fields[1]);status.setText(result.fields[1]);
                        if(result.fields[0].equals("verified")||result.fields[0].equals("submitted")){panel.model.setRowCount(0);panel.loaded=false;if(selected()==panel)loadSelected(true);}
                        else{panel.allowEdits=false;panel.needsCheck=true;panel.updatePending();panel.table.repaint();panel.message.setText(result.fields[1]+" Refresh before editing again.");}
                    });
                }catch(Exception failure){SwingUtilities.invokeLater(()->{if(request==generation){settingsBusy(panel,false);panel.allowEdits=false;panel.needsCheck=true;panel.updatePending();panel.table.repaint();panel.message.setText("Apply stopped: "+failure.getMessage()+" Check the controller before retrying.");}});}});
            });
        }catch(Exception failure){SwingUtilities.invokeLater(()->{if(request==generation){settingsBusy(panel,false);panel.message.setText("Review failed · Nothing sent: "+failure.getMessage());}});}});
    }
    void openConsole(){
        if(bridge==null)return;int request=generation;String host=connectedHost,user=username;char[] auth=password.clone();console.setEnabled(false);status.setText("Opening KVM window…");
        if(consoleStatus!=null)consoleStatus.dispose();
        ConsoleStatusDialog panel=new ConsoleStatusDialog(this,host);consoleStatus=panel;panel.showState("starting",0,0);
        Thread task=new Thread(()->{Process proc=null;try{
            ProcessBuilder builder=python(root,"--console-managed");proc=builder.start();consoles.add(proc);
            panel.cancelAction=proc::destroy;
            if(request!=generation||panel.cancelled){proc.destroy();return;}
            try(BufferedWriter w=proc.outputWriter(StandardCharsets.UTF_8)){for(String field:List.of(host,user,new String(auth))){w.write(enc(field));w.newLine();}}
            StringBuilder output=new StringBuilder();try(BufferedReader r=proc.inputReader(StandardCharsets.UTF_8)){String line;while((line=r.readLine())!=null){
                if(line.startsWith("CONSOLE_META\t")){
                    String[] parts=line.split("\t");
                    String phase=new String(Base64.getDecoder().decode(parts[1]),StandardCharsets.UTF_8);
                    int attempt=Integer.parseInt(new String(Base64.getDecoder().decode(parts[2]),StandardCharsets.UTF_8));
                    int retryIn=Integer.parseInt(new String(Base64.getDecoder().decode(parts[3]),StandardCharsets.UTF_8));
                    SwingUtilities.invokeLater(()->{if(request==generation)panel.showState(phase,attempt,retryIn);});
                }else if(line.startsWith("CONSOLE\t")){
                    String phase=new String(Base64.getDecoder().decode(line.substring(8)),StandardCharsets.UTF_8);
                    String message=switch(phase){case "connected"->"KVM connected · Input can be enabled in the viewer";case "reconnecting"->"KVM disconnected · Retrieving a fresh launch file with saved credentials…";case "failed"->"KVM reconnect attempts exhausted";case "closing"->"Closing KVM…";default->"Opening KVM…";};
                    SwingUtilities.invokeLater(()->{if(request==generation){status.setText(message);panel.showState(phase,0,0);}});
                }else if(line.startsWith("ERROR\t")&&output.length()<8000)output.append(new String(Base64.getDecoder().decode(line.substring(6)),StandardCharsets.UTF_8)).append('\n');
            }}
            int code=proc.waitFor();String message=code==0?"KVM window closed":"KVM could not open: "+output;
            SwingUtilities.invokeLater(()->{if(request==generation){status.setText(panel.cancelled?"KVM closed":message.replace('\n',' '));console.setEnabled(bridge!=null&&kvmSupported);if(code==0||panel.cancelled)panel.dispose();else panel.showFailure(output.toString());}});
        }catch(Exception e){if(proc!=null&&proc.isAlive())proc.destroy();SwingUtilities.invokeLater(()->{if(request==generation){status.setText("KVM launch failed: "+e.getMessage());console.setEnabled(bridge!=null&&kvmSupported);panel.showFailure(e.getMessage());}});}
        finally{Arrays.fill(auth,'\0');if(proc!=null)consoles.remove(proc);SwingUtilities.invokeLater(()->{if(request==generation){console.setEnabled(bridge!=null&&kvmSupported);if(panel.cancelled){panel.dispose();status.setText("KVM closed");}}});}},"dracula-console");task.setDaemon(true);task.start();
    }
    static ProcessBuilder python(Path root,String... flags){
        List<String> cmd=new ArrayList<>(List.of(System.getProperty("dracula.python","python3"),"-m","dracula.manager_bridge"));cmd.addAll(List.of(flags));
        ProcessBuilder b=new ProcessBuilder(cmd);b.directory(root.toFile());b.redirectErrorStream(true);b.environment().put("PYTHONPATH",root.resolve("src").toString());
        if(Boolean.getBoolean("dracula.portable")){b.environment().remove("PYTHONHOME");b.environment().put("PYTHONNOUSERSITE","1");b.environment().put("DRACULA_HTTP_TRANSPORT","stdlib");b.environment().put("DRACULA_CACHE",System.getProperty("dracula.state"));b.environment().put("DRACULA_AUTO_JAVA","1");}
        return b;
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
        synchronized List<Record> settings(String json)throws IOException{writer.write("SETTINGS\t"+enc(json)+"\n");writer.flush();List<Record> result=readResponse();for(Record r:result)if(r.kind.equals("ERROR"))throw new IOException(r.fields[0]);return result;}
        void close(){Thread cleanup=new Thread(()->{try{writer.write("QUIT\n");writer.flush();if(!process.waitFor(3,TimeUnit.SECONDS))process.destroy();}catch(Exception ignored){process.destroy();}},"dracula-disconnect");cleanup.setDaemon(true);cleanup.start();}
    }
    static final class PagePanel extends JPanel {
        java.util.function.Consumer<String> powerAction=action->{};String powerRevision="";
        final Map<String,JButton> powerButtons=new LinkedHashMap<>();final Map<String,Boolean> powerEnabled=new HashMap<>();
        final String key;boolean allowEdits=false,busy=false,loadingData=false,needsCheck=false;
        final DefaultTableModel model=new DefaultTableModel(new String[]{"Group / record","Field","Value","Access"},0){public boolean isCellEditable(int r,int c){return c==2&&allowEdits&&!busy&&getValueAt(r,c) instanceof FieldCells.Value value&&value.edit()!=null;}};
        final JTable table=new JTable(model);final TableRowSorter<DefaultTableModel> sorter=new TableRowSorter<>(model);final JLabel message=new JLabel("Not loaded yet"),pending=new JLabel(""),note=new JLabel("Configurable fields and actions stay locked during read-only access.");
        final JButton apply=new JButton("Apply changes…"),discard=new JButton("Discard edits");final java.util.List<JButton> originalApply=new ArrayList<>();boolean loaded=false,loading=false;
        PagePanel(String key,String title,String actions){
            super(new BorderLayout(0,10));this.key=key;setBorder(new EmptyBorder(14,14,14,14));DesktopTheme.style(this,"surface");
            JLabel name=new JLabel(title);name.setFont(new Font(Font.SANS_SERIF,Font.BOLD,19));add(name,BorderLayout.NORTH);
            table.setRowSorter(sorter);table.setRowHeight(36);table.setFillsViewportHeight(true);table.setShowGrid(false);table.setIntercellSpacing(new Dimension(0,0));table.getTableHeader().setReorderingAllowed(false);
            table.getColumnModel().getColumn(0).setPreferredWidth(280);table.getColumnModel().getColumn(1).setPreferredWidth(220);table.getColumnModel().getColumn(2).setPreferredWidth(230);table.getColumnModel().getColumn(3).setPreferredWidth(180);
            table.setDefaultRenderer(Object.class,new FieldCells.Renderer());table.getColumnModel().getColumn(2).setCellEditor(new FieldCells.Editor());
            add(new JScrollPane(table),BorderLayout.CENTER);JPanel foot=new JPanel(new BorderLayout(0,9));foot.setOpaque(false);DesktopTheme.style(message,"muted");foot.add(message,BorderLayout.NORTH);
            JPanel controls=new JPanel(new FlowLayout(FlowLayout.LEFT,6,4));controls.setOpaque(false);controls.add(pending);controls.add(apply);controls.add(discard);
            apply.setVisible(false);discard.setVisible(false);discard.addActionListener(e->{if(table.isEditing())table.getCellEditor().cancelCellEditing();for(int r=0;r<model.getRowCount();r++)if(model.getValueAt(r,2) instanceof FieldCells.Value value&&value.edit()!=null)model.setValueAt(value.changed(value.edit().initial),r,2);});
            if(key.equals("power")){String[] ids={"on","off","cycle","reset","soft"};String[] labels={"Power on","Power off","Power cycle","Reset","Graceful shutdown"};for(int i=0;i<ids.length;i++){String id=ids[i];JButton button=new JButton(labels[i]);button.setEnabled(false);button.addActionListener(e->powerAction.accept(id));powerButtons.put(id,button);controls.add(button);}}

            foot.add(controls,BorderLayout.CENTER);DesktopTheme.style(note,"accent");foot.add(note,BorderLayout.SOUTH);add(foot,BorderLayout.SOUTH);
            model.addTableModelListener(e->{if(!loadingData)updatePending();});
        }
        void loadRecords(List<Record> records,boolean writable){
            powerEnabled.clear();powerRevision="";powerButtons.values().forEach(button->button.setVisible(false));
            for(Record r:records){if(r.kind.equals("POWER")&&r.fields.length==3)powerRevision=r.fields[0];if(r.kind.equals("POWER_ACTION")&&r.fields.length==5&&powerButtons.containsKey(r.fields[0])){powerButtons.get(r.fields[0]).setVisible(true);powerEnabled.put(r.fields[0],r.fields[2].equals("true"));powerButtons.get(r.fields[0]).setToolTipText(r.fields[3].isBlank()?"Review via "+r.fields[4]:r.fields[3]);}}
            loadingData=true;Map<String,FieldCells.Edit> editors=new HashMap<>();
            for(Record r:records)if(r.kind.equals("EDIT")&&r.fields.length==10)editors.put(r.fields[0],new FieldCells.Edit(r.fields));
            for(Record r:records)if(r.kind.equals("OPTION")&&r.fields.length==3&&editors.containsKey(r.fields[0]))editors.get(r.fields[0]).choices.add(new FieldCells.Choice(r.fields[1],r.fields[2]));
            model.setRowCount(0);allowEdits=writable;needsCheck=false;
            for(Record r:records){if(r.kind.equals("FIELD")&&r.fields.length>=6)model.addRow(FieldCells.row(r.fields,writable&&r.fields.length>=7?editors.get(r.fields[6]):null));if(r.kind.equals("ROW")&&r.fields.length==3)model.addRow(r.fields);}
            loadingData=false;boolean editable=writable&&!editors.isEmpty();apply.setVisible(editable);discard.setVisible(editable);for(JButton button:originalApply)button.setVisible(!editable);
            note.setText(key.equals("power")?"Every power action requires confirmation for the selected device.":editable?"Edits are staged locally · Apply shows exact changes and requires confirmation for the selected device.":"Fields are read-only here; unsupported forms remain locked.");updatePending();
        }
        Map<String,String> changes(){Map<String,String> changes=new LinkedHashMap<>();for(int r=0;r<model.getRowCount();r++)if(model.getValueAt(r,2) instanceof FieldCells.Value value&&value.dirty())changes.put(value.edit().key,value.raw());return changes;}
        boolean dirty(){return !changes().isEmpty();}
        String revision(){for(int r=0;r<model.getRowCount();r++)if(model.getValueAt(r,2) instanceof FieldCells.Value value&&value.edit()!=null)return value.edit().revision;return "";}
        void setBusy(boolean value){busy=value;updatePending();table.repaint();}
        void updatePending(){int count=changes().size();pending.setText(apply.isVisible()?(count==0?"No staged changes":count+" staged changes · Nothing sent yet"):"");apply.setEnabled(allowEdits&&!busy&&count>0);discard.setEnabled(!busy&&count>0);powerButtons.forEach((id,button)->button.setEnabled(!busy&&!needsCheck&&powerEnabled.getOrDefault(id,false)));}
    }
    void updateThemeAction(){theme.setText(DesktopTheme.action());theme.setToolTipText("Switch to "+(DesktopTheme.dark()?"light":"dark")+" mode");theme.getAccessibleContext().setAccessibleName(theme.getToolTipText());}
    void changeTheme(){
        for(Window window:Window.getWindows())if(!DesktopTheme.finishEditors(window))return;
        boolean wasRebuilding=rebuilding,wasSyncing=syncingDevices;rebuilding=true;syncingDevices=true;
        try{DesktopTheme.install(!DesktopTheme.dark());DesktopTheme.refreshWindows();updateThemeAction();DesktopTheme.remember();}
        finally{rebuilding=wasRebuilding;syncingDevices=wasSyncing;}
    }
    static void configureLookAndFeel(){
        System.setProperty("awt.useSystemAAFontSettings","on");System.setProperty("swing.aatext","true");DesktopTheme.load();
    }
    public static void main(String[] args)throws Exception{
        configureLookAndFeel();
        SwingUtilities.invokeLater(()->new Manager().setVisible(true));
    }
}
