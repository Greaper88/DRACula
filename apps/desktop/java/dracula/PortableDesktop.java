// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;

import java.awt.*;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.security.*;
import java.time.Duration;
import java.util.*;
import java.util.List;
import java.util.function.Consumer;
import java.util.zip.GZIPInputStream;
import javax.swing.*;
import org.apache.commons.compress.archivers.tar.*;

/** Executable release JAR: prepare an isolated shared core and private Python. */
public final class PortableDesktop {
    record RuntimeSpec(URI url,String hash,String executable) {}
    record Link(Path destination,Path target) {}
    static String platform(String os,String arch) {
        os=os.toLowerCase(Locale.ROOT);arch=arch.toLowerCase(Locale.ROOT);
        String family=os.startsWith("windows")?"windows":os.contains("mac")||os.contains("darwin")?"macos":os.contains("linux")?"linux":"unsupported";
        String cpu=Set.of("amd64","x86_64").contains(arch)?"x86_64":Set.of("aarch64","arm64").contains(arch)?"aarch64":"unsupported";
        if(family.equals("unsupported")||cpu.equals("unsupported"))throw new IllegalArgumentException("This release supports Windows, macOS and Linux on x64 or ARM64, with Java 17 or newer.");
        return family+"-"+cpu;
    }
    static Path dataHome() {
        String override=System.getProperty("dracula.home");if(override!=null)return Path.of(override).toAbsolutePath();
        String os=System.getProperty("os.name").toLowerCase(Locale.ROOT),home=System.getProperty("user.home");
        if(os.startsWith("windows")){String local=System.getenv("LOCALAPPDATA");return Path.of(local==null?home:local,"DRACula");}
        if(os.contains("mac"))return Path.of(home,"Library","Application Support","DRACula");
        String xdg=System.getenv("XDG_DATA_HOME");return (xdg==null||xdg.isBlank()?Path.of(home,".local","share"):Path.of(xdg)).resolve("dracula");
    }
    static void privateDirectory(Path path)throws IOException {
        Files.createDirectories(path);
        try{Files.setPosixFilePermissions(path,java.nio.file.attribute.PosixFilePermissions.fromString("rwx------"));}catch(UnsupportedOperationException ignored){}
    }
    static byte[] resource(String name)throws IOException {
        try(InputStream in=PortableDesktop.class.getResourceAsStream(name)){if(in==null)throw new IOException("Missing packaged support file: "+name);return in.readAllBytes();}
    }
    static String digest(byte[] data)throws GeneralSecurityException{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));}
    static String digest(Path path)throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");try(InputStream in=Files.newInputStream(path)){byte[] buffer=new byte[65536];int size;while((size=in.read(buffer))!=-1)digest.update(buffer,0,size);}return HexFormat.of().formatHex(digest.digest());
    }
    static RuntimeSpec runtime(String platform)throws IOException {
        Properties values=new Properties();values.load(new ByteArrayInputStream(resource("/bootstrap/python-runtimes.properties")));
        String url=values.getProperty(platform+".url"),hash=values.getProperty(platform+".sha256"),exe=values.getProperty(platform+".executable");
        if(url==null||hash==null||exe==null||!hash.matches("[0-9a-f]{64}"))throw new IOException("No reviewed backend runtime for "+platform);
        URI uri=URI.create(url);if(!uri.getScheme().equals("https")||!uri.getHost().equals("github.com"))throw new IOException("Invalid backend runtime source");
        return new RuntimeSpec(uri,hash,exe);
    }
    static Path confined(Path root,String name)throws IOException {
        if(name.isEmpty()||name.contains("\\")||name.contains(":"))throw new IOException("Invalid archive path");
        Path relative=Path.of(name);Path path=root.resolve(relative).normalize();if(relative.isAbsolute()||!path.startsWith(root)||path.equals(root))throw new IOException("Archive path escapes destination");return path;
    }
    static void extractTar(InputStream compressed,Path root)throws IOException {
        List<Link> links=new ArrayList<>();long total=0;int count=0;
        try(TarArchiveInputStream tar=new TarArchiveInputStream(new GZIPInputStream(compressed))){
            TarArchiveEntry entry;
            while((entry=tar.getNextEntry())!=null){
                if(++count>100000||entry.getSize()<0||(total+=entry.getSize())>1_500_000_000L)throw new IOException("Runtime archive exceeds limits");
                Path target=confined(root,entry.getName());
                if(entry.isDirectory()){Files.createDirectories(target);continue;}
                if(entry.isSymbolicLink()||entry.isLink()){
                    String name=entry.getLinkName();if(name.contains("\\")||name.contains(":")||Path.of(name).isAbsolute())throw new IOException("Invalid runtime link");
                    Path source=(entry.isLink()?root:target.getParent()).resolve(name).normalize();if(!source.startsWith(root))throw new IOException("Runtime link escapes destination");links.add(new Link(target,source));continue;
                }
                if(!entry.isFile())throw new IOException("Unsupported runtime archive entry");
                Files.createDirectories(target.getParent());
                try(OutputStream output=Files.newOutputStream(target,StandardOpenOption.CREATE_NEW)){tar.transferTo(output);}
                if((entry.getMode()&0111)!=0&&!target.toFile().setExecutable(true,true)&&!System.getProperty("os.name").startsWith("Windows"))throw new IOException("Cannot make backend runtime executable");
            }
        }
        // Materialize internal file aliases rather than requiring Windows symlink privileges.
        while(!links.isEmpty()){
            boolean changed=false;for(Iterator<Link> it=links.iterator();it.hasNext();){Link link=it.next();if(!Files.isRegularFile(link.target(),LinkOption.NOFOLLOW_LINKS))continue;Files.createDirectories(link.destination().getParent());Files.copy(link.target(),link.destination(),StandardCopyOption.COPY_ATTRIBUTES);it.remove();changed=true;}
            if(!changed)throw new IOException("Unresolved or directory runtime link");
        }
    }
    static void removeTree(Path root)throws IOException {
        if(!Files.exists(root))return;try(var paths=Files.walk(root)){for(Path path:paths.sorted(Comparator.reverseOrder()).toList())Files.deleteIfExists(path);}
    }
    static Path extractCore(Path home)throws Exception {
        byte[] manifest=resource("/bootstrap/payload.manifest");Path root=home.resolve("core-"+digest(manifest).substring(0,16));
        if(Files.exists(root.resolve(".complete")))return root;
        Path temp=Files.createTempDirectory(home,"core-prepare-");
        try {
            for(String line:new String(manifest,java.nio.charset.StandardCharsets.UTF_8).lines().toList()){
                String[] fields=line.split(" ",2);if(fields.length!=2||!fields[0].matches("[0-9a-f]{64}"))throw new IOException("Invalid support manifest");
                byte[] bytes=resource("/payload/"+fields[1]);if(!digest(bytes).equals(fields[0]))throw new IOException("Support checksum mismatch");
                Path file=confined(temp,fields[1]);Files.createDirectories(file.getParent());Files.write(file,bytes,StandardOpenOption.CREATE_NEW);
            }
            Files.writeString(temp.resolve(".complete"),"0.1.2\n");Files.move(temp,root);return root;
        }finally{removeTree(temp);}
    }
    static Path preparePython(Path home,String platform,Consumer<String> status)throws Exception {
        RuntimeSpec spec=runtime(platform);Path runtimes=home.resolve("runtimes");privateDirectory(runtimes);Path installed=runtimes.resolve("python-"+spec.hash().substring(0,16));Path exe=confined(installed,spec.executable());
        if(Files.isRegularFile(exe)&&Files.exists(installed.resolve(".verified")))return exe;
        Path archive=runtimes.resolve("python-"+spec.hash()+".tar.gz");
        if(!Files.isRegularFile(archive)||!digest(archive).equals(spec.hash())){
            status.accept("Downloading the private desktop backend…");Path download=Files.createTempFile(runtimes,"download-",".tmp");
            try {
                HttpClient client=HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).connectTimeout(Duration.ofSeconds(20)).build();
                HttpRequest request=HttpRequest.newBuilder(spec.url()).timeout(Duration.ofMinutes(3)).header("User-Agent","DRACula/0.1.2").build();
                HttpResponse<InputStream> response=client.send(request,HttpResponse.BodyHandlers.ofInputStream());
                try(InputStream in=response.body();OutputStream out=Files.newOutputStream(download)){
                    if(response.statusCode()!=200)throw new IOException("Backend download failed (HTTP "+response.statusCode()+")");
                    byte[] buffer=new byte[65536];long total=0;int n;while((n=in.read(buffer))!=-1){if((total+=n)>120_000_000)throw new IOException("Oversized backend runtime");out.write(buffer,0,n);}
                }
                if(!digest(download).equals(spec.hash()))throw new IOException("Backend runtime checksum mismatch");Files.move(download,archive,StandardCopyOption.REPLACE_EXISTING);
            }finally{Files.deleteIfExists(download);}
        }
        status.accept("Preparing the private desktop backend…");Path temp=Files.createTempDirectory(runtimes,"python-prepare-");
        try{
            extractTar(Files.newInputStream(archive),temp);Path prepared=confined(temp,spec.executable());if(!Files.isRegularFile(prepared))throw new IOException("Backend executable missing");
            Files.writeString(temp.resolve(".verified"),spec.hash());if(Files.exists(installed))removeTree(installed);Files.move(temp,installed);
        }finally{removeTree(temp);}
        return exe;
    }
    static void configure(Path home,Path core,Path python,String platform) {
        System.setProperty("dracula.root",core.toString());System.setProperty("dracula.state",home.resolve("state").toString());System.setProperty("dracula.python",python.toString());System.setProperty("dracula.portable","true");
        System.setProperty("dracula.kvm.supported",Boolean.toString(platform.equals("linux-x86_64")));
        System.setProperty("java.util.prefs.userRoot",home.resolve("preferences").toString());
    }
    public static void main(String[] args)throws Exception {
        if(System.getProperty("dracula.root")!=null){Manager.main(args);return;}
        boolean prepareOnly=Arrays.asList(args).contains("--prepare-only");JDialog[] progress={null};JLabel[] label={null};
        try {
            Path home=dataHome().toAbsolutePath().normalize();privateDirectory(home);System.setProperty("java.util.prefs.userRoot",home.resolve("preferences").toString());
            if(!prepareOnly&&!GraphicsEnvironment.isHeadless())SwingUtilities.invokeAndWait(()->{Manager.configureLookAndFeel();progress[0]=new JDialog((Frame)null,"DRACula · First launch",false);label[0]=new JLabel("Preparing desktop support files…");JPanel panel=new JPanel(new BorderLayout());panel.setBorder(BorderFactory.createEmptyBorder(24,24,24,24));panel.add(label[0]);progress[0].add(panel);progress[0].pack();progress[0].setLocationRelativeTo(null);progress[0].setVisible(true);});
            Consumer<String> status=message->{if(prepareOnly)System.out.println(message);else SwingUtilities.invokeLater(()->{if(label[0]!=null)label[0].setText(message);});};
            String platform=platform(System.getProperty("os.name"),System.getProperty("os.arch"));
            try(FileChannel lockFile=FileChannel.open(home.resolve("setup.lock"),StandardOpenOption.CREATE,StandardOpenOption.WRITE);FileLock lock=lockFile.lock()){
                Path core=extractCore(home),python=preparePython(home,platform,status);configure(home,core,python,platform);
                ProcessBuilder check=new ProcessBuilder(python.toString(),"-I","-c","import sys,ssl;assert sys.version_info >= (3,12)");check.environment().remove("PYTHONHOME");check.environment().remove("PYTHONPATH");Process process=check.start();if(!process.waitFor(15,java.util.concurrent.TimeUnit.SECONDS)){process.destroyForcibly();throw new IOException("Backend startup timed out");}if(process.exitValue()!=0)throw new IOException("The private backend could not start on this system");
            }
            if(prepareOnly){System.out.println("Desktop support ready; no device connection was made.");return;}
            Manager.main(args);
        }catch(Exception error){if(prepareOnly||GraphicsEnvironment.isHeadless())throw error;SwingUtilities.invokeAndWait(()->JOptionPane.showMessageDialog(null,"DRACula could not finish setup: "+error.getMessage()+"\nCheck network access and the desktop setup guide.","DRACula setup",JOptionPane.ERROR_MESSAGE));}
        finally{if(progress[0]!=null)SwingUtilities.invokeLater(()->progress[0].dispose());}
    }
}
