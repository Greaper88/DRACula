// Copyright 2026 DRACula contributors
// SPDX-License-Identifier: Apache-2.0
package dracula;
import java.io.*;import java.nio.file.*;import java.util.*;import java.util.zip.*;
import org.apache.commons.compress.archivers.tar.*;
public final class PortableDesktopTest {
 static byte[] archive(String name,String link)throws Exception{
  ByteArrayOutputStream out=new ByteArrayOutputStream();try(TarArchiveOutputStream tar=new TarArchiveOutputStream(new GZIPOutputStream(out))){TarArchiveEntry entry=new TarArchiveEntry(name,link==null?(byte)'0':(byte)'2',true);if(link==null)entry.setSize(2);else entry.setLinkName(link);tar.putArchiveEntry(entry);if(link==null)tar.write(new byte[]{1,2});tar.closeArchiveEntry();}return out.toByteArray();
 }
 public static void main(String[] args)throws Exception{
  for(String[] item:new String[][]{{"Linux","amd64","linux-x86_64"},{"Windows 11","aarch64","windows-aarch64"},{"Mac OS X","arm64","macos-aarch64"},{"Darwin","x86_64","macos-x86_64"}})if(!PortableDesktop.platform(item[0],item[1]).equals(item[2]))throw new AssertionError("Platform selection");
  try{PortableDesktop.platform("Linux","sparc");throw new AssertionError("Unsupported platform accepted");}catch(IllegalArgumentException expected){}
  for(String platform:List.of("linux-x86_64","linux-aarch64","windows-x86_64","windows-aarch64","macos-x86_64","macos-aarch64")){var spec=PortableDesktop.runtime(platform);if(!spec.hash().matches("[0-9a-f]{64}")||!spec.url().getScheme().equals("https"))throw new AssertionError("Unpinned runtime");}
  Path root=Files.createTempDirectory("dracula-portable-test-");
  try{
   PortableDesktop.extractTar(new ByteArrayInputStream(archive("python/bin/python3",null)),root);if(Files.size(root.resolve("python/bin/python3"))!=2)throw new AssertionError("Tar extraction");
   for(String name:List.of("../escape","/absolute","C:/escape","python\\escape"))try{PortableDesktop.extractTar(new ByteArrayInputStream(archive(name,null)),root);throw new AssertionError("Traversal accepted");}catch(IOException expected){}
   try{PortableDesktop.extractTar(new ByteArrayInputStream(archive("python/alias","../../escape")),root);throw new AssertionError("Escaping link accepted");}catch(IOException expected){}
   PortableDesktop.extractTar(new ByteArrayInputStream(archive("python/alias","bin/python3")),root);if(Files.isSymbolicLink(root.resolve("python/alias"))||Files.size(root.resolve("python/alias"))!=2)throw new AssertionError("Internal alias materialization");
   Path core=PortableDesktop.extractCore(root);if(!Files.exists(core.resolve("src/dracula/manager_bridge.py"))||!Files.exists(core.resolve("launcher/legacy-java.security")))throw new AssertionError("Packaged core incomplete");if(!PortableDesktop.extractCore(root).equals(core))throw new AssertionError("Core changed between launches");
  }finally{PortableDesktop.removeTree(root);}
  System.out.println("PASS portable platform selection, pinned downloads, safe extraction, link handling and embedded core");
 }
}
