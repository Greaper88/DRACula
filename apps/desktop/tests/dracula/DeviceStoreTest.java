package dracula;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public final class DeviceStoreTest {
 public static void main(String[] args)throws Exception {
  Path root=Files.createTempDirectory("dracula-vault-test-");
  try {
   String host="192.168.1.10", password="synthetic-device-secret";
   try(DeviceStore store=new DeviceStore(root)){
    store.unlock("synthetic-master".toCharArray());
    store.put(null,new DeviceStore.Profile("Lab",host,"operator",true),password.toCharArray());
   }
   String profile=Files.readString(root.resolve("devices.properties"));
   if(profile.contains(password)||profile.contains("synthetic-master"))throw new AssertionError("Plaintext profile contains secret");
   byte[] original=Files.readAllBytes(root.resolve("passwords.vault"));
   if(new String(original,StandardCharsets.ISO_8859_1).contains(password))throw new AssertionError("Vault contains plaintext password");
   try(DeviceStore store=new DeviceStore(root)){
    if(store.password(host).length!=0)throw new AssertionError("Password available before unlock");
    try{store.unlock("wrong".toCharArray());throw new AssertionError("Wrong master accepted");}catch(javax.crypto.AEADBadTagException expected){}
    if(!Arrays.equals(original,Files.readAllBytes(root.resolve("passwords.vault"))))throw new AssertionError("Failed unlock modified vault");
    store.unlock("synthetic-master".toCharArray());
    if(!password.equals(new String(store.password(host))))throw new AssertionError("Password did not round-trip");
    if(!store.profiles.get(host).user().equals("operator"))throw new AssertionError("Username lost");
    store.put(host,new DeviceStore.Profile("Moved","192.168.1.11","newuser",true),store.password(host));
    if(store.password(host).length!=0)throw new AssertionError("Old host credential retained");
   }
   try(DeviceStore store=new DeviceStore(root)){
    store.unlock("synthetic-master".toCharArray());
    if(!password.equals(new String(store.password("192.168.1.11"))))throw new AssertionError("Moved credential lost");
    store.remove("192.168.1.11");
   }
   byte[] tampered=Files.readAllBytes(root.resolve("passwords.vault"));tampered[tampered.length-1]^=1;Files.write(root.resolve("passwords.vault"),tampered);
   try(DeviceStore store=new DeviceStore(root)){
    try{store.unlock("synthetic-master".toCharArray());throw new AssertionError("Tampered vault accepted");}catch(javax.crypto.AEADBadTagException expected){}
   }
   System.out.println("PASS: encrypted credential persistence, wrong-password handling, host changes, removal, and tamper detection");
  }finally{try(var paths=Files.walk(root)){for(Path path:paths.sorted(Comparator.reverseOrder()).toList())Files.deleteIfExists(path);}}
 }
}
