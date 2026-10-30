package dracula;

import javax.crypto.*;
import javax.crypto.spec.*;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;

/** Device addresses and usernames are separate from authenticated encrypted secrets. */
final class DeviceStore implements AutoCloseable {
    record Profile(String name,String host,String user,boolean saved) {
        @Override public String toString(){return name+" · "+host;}
    }
    final Path directory;
    final LinkedHashMap<String,Profile> profiles=new LinkedHashMap<>();
    final Map<String,char[]> passwords=new HashMap<>();
    char[] master;
    DeviceStore(Path directory)throws IOException {
        this.directory=directory;Files.createDirectories(directory);
        Properties p=new Properties();Path file=directory.resolve("devices.properties");
        if(Files.exists(file))try(InputStream in=Files.newInputStream(file)){p.load(in);}
        for(String host:p.getProperty("hosts","").split(","))if(Manager.validHost(host))profiles.put(host,new Profile(p.getProperty(host+".name",host),host,p.getProperty(host+".user","root"),Boolean.parseBoolean(p.getProperty(host+".saved","false"))));
        if(profiles.isEmpty()){
            Path old=directory.resolve("machines.txt");
            List<String> hosts=Files.exists(old)?Files.readAllLines(old):List.of("192.168.1.252","192.168.1.253","192.168.1.254");
            for(String host:hosts)if(Manager.validHost(host))profiles.put(host,new Profile("DRAC 5",host,"root",false));
        }
    }
    boolean hasVault(){return Files.exists(directory.resolve("passwords.vault"));}
    boolean unlocked(){return master!=null;}
    void unlock(char[] supplied)throws Exception {
        if(supplied.length==0)throw new IllegalArgumentException("An unlock password is required");
        Map<String,char[]> recovered=new HashMap<>();
        if(hasVault()){
            byte[] data=Files.readAllBytes(directory.resolve("passwords.vault"));
            if(data.length<48||data.length>1_000_000)throw new IOException("Invalid password vault");
            byte[] plain;
            try(DataInputStream in=new DataInputStream(new ByteArrayInputStream(data))){
                if(in.readInt()!=0x44524131)throw new IOException("Unsupported password vault");
                byte[] salt=in.readNBytes(16),nonce=in.readNBytes(12),ciphertext=in.readAllBytes();
                Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(supplied,salt),new GCMParameterSpec(128,nonce));
                plain=cipher.doFinal(ciphertext);
            }
            try {
                Properties values=new Properties();values.load(new ByteArrayInputStream(plain));
                for(String host:values.stringPropertyNames())if(profiles.containsKey(host)&&profiles.get(host).saved())recovered.put(host,values.getProperty(host).toCharArray());
            }finally{Arrays.fill(plain,(byte)0);}
        }
        passwords.putAll(recovered);if(master!=null)Arrays.fill(master,'\0');master=supplied.clone();
    }
    static SecretKey key(char[] password,byte[] salt)throws GeneralSecurityException {
        PBEKeySpec spec=new PBEKeySpec(password,salt,210_000,256);
        try {byte[] raw=SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();try{return new SecretKeySpec(raw,"AES");}finally{Arrays.fill(raw,(byte)0);}}
        finally{spec.clearPassword();}
    }
    char[] password(String host){char[] value=passwords.get(host);return value==null?new char[0]:value.clone();}
    void put(String previous,Profile profile,char[] password)throws Exception {
        if(profile.saved()&&!unlocked())throw new IllegalStateException("Unlock password storage before saving a password");
        if(previous!=null&&!previous.equals(profile.host())){
            profiles.remove(previous);char[] old=passwords.remove(previous);if(old!=null)Arrays.fill(old,'\0');
        }
        profiles.put(profile.host(),profile);char[] old=passwords.put(profile.host(),password.clone());if(old!=null)Arrays.fill(old,'\0');
        if(unlocked())saveVault();saveProfiles();
    }
    void remove(String host)throws Exception {
        profiles.remove(host);char[] old=passwords.remove(host);if(old!=null)Arrays.fill(old,'\0');
        if(unlocked())saveVault();saveProfiles();
    }
    void saveProfiles()throws IOException {
        Properties p=new Properties();p.setProperty("hosts",String.join(",",profiles.keySet()));
        for(Profile profile:profiles.values()){
            p.setProperty(profile.host()+".name",profile.name());p.setProperty(profile.host()+".user",profile.user());p.setProperty(profile.host()+".saved",Boolean.toString(profile.saved()));
        }
        ByteArrayOutputStream out=new ByteArrayOutputStream();p.store(out,"DRACula devices — passwords are kept in a separate encrypted vault");writePrivate(directory.resolve("devices.properties"),out.toByteArray());
    }
    void saveVault()throws Exception {
        Properties values=new Properties();
        for(Profile p:profiles.values())if(p.saved()&&passwords.containsKey(p.host()))values.setProperty(p.host(),new String(passwords.get(p.host())));
        ByteArrayOutputStream plain=new ByteArrayOutputStream();values.store(plain,"DRACula credentials");byte[] raw=plain.toByteArray();
        try {
            SecureRandom random=new SecureRandom();byte[] salt=new byte[16],nonce=new byte[12];random.nextBytes(salt);random.nextBytes(nonce);
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key(master,salt),new GCMParameterSpec(128,nonce));
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();try(DataOutputStream out=new DataOutputStream(bytes)){out.writeInt(0x44524131);out.write(salt);out.write(nonce);out.write(cipher.doFinal(raw));}
            writePrivate(directory.resolve("passwords.vault"),bytes.toByteArray());
        }finally{Arrays.fill(raw,(byte)0);}
    }
    static void writePrivate(Path destination,byte[] data)throws IOException {
        Path temp=Files.createTempFile(destination.getParent(),".save-",".tmp");
        try {try{Files.setPosixFilePermissions(temp,java.nio.file.attribute.PosixFilePermissions.fromString("rw-------"));}catch(UnsupportedOperationException ignored){}Files.write(temp,data);try{Files.move(temp,destination,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}catch(AtomicMoveNotSupportedException e){Files.move(temp,destination,StandardCopyOption.REPLACE_EXISTING);}}
        finally{Files.deleteIfExists(temp);}
    }
    public void close(){for(char[] p:passwords.values())Arrays.fill(p,'\0');passwords.clear();if(master!=null)Arrays.fill(master,'\0');master=null;}
}
