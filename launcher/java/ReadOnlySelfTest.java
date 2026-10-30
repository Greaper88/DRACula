package dracula;

/** Exercise every input method with a tripwire in the real outgoing packet path. */
public final class ReadOnlySelfTest {
    static final class Tripwire extends ReadOnlyViewer.Transport {
        @Override public com.avocent.kvm.d.b.g y() {
            throw new AssertionError("An input method reached the packet queue");
        }
    }
    public static void main(String[] args) throws Exception {
        Tripwire t = new Tripwire();
        t.d().a(65); t.d().b(65); t.d().a((com.avocent.kvm.d.d.d)null);
        t.e().a(10,20); t.e().b(10,20); t.e().c(10,20);
        t.e().a(1,2,3,true,true,true,4); t.e().b(1,2,3,true,true,true,4);
        for (int op=0; op<10; op++) {
            try { t.a(op,null,null); throw new AssertionError("Command allowed"); }
            catch (SecurityException expected) { }
        }
        System.out.println("PASS: all keyboard/mouse entry points and generic commands blocked");
        System.exit(0);
    }
}
