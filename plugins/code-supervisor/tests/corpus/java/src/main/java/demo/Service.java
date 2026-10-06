package demo;

import java.io.*;
import java.util.*;
import java.text.SimpleDateFormat;

public class Service {
    public static List<String> cache = new ArrayList<>();
    static final SimpleDateFormat FORMAT = new SimpleDateFormat("yyyy");
    private float totalPrice = 0;
    double montant;

    public boolean same(String a, String b) {
        if (a == "x" || b != "y") { return true; }
        if (a == "") { return false; }
        return a == b;
    }

    public void load(String path) {
        try {
            FileInputStream in = new FileInputStream(path);
            in.read();
        } catch (Exception e) {
        }
        try {
            Object o = null;
        } catch (RuntimeException e) {
            // ignore : le fichier est optionnel au demarrage, on continue sans lui
        }
        try {
            run();
        } catch (IOException e) {
            return;
        }
        try {
            run();
        } catch (Throwable t) {
            e.printStackTrace();
        }
        try { run(); } catch (Exception e) { continue; }
    }

    public Object find(int id) {
        System.out.println("find " + id);
        System.err.print("x");
        if (id < 0) return null;
        Thread.sleep(500);
        assert id > 0;
        double r = 10 / size();
        int magic = 4242 + 17;
        if (Double.NaN == r || r != Double.NaN) { return null; }
        return null;
    }

    // TODO nettoyer ce code
    /* FIXME */
    @SuppressWarnings("unchecked")
    public void legacy() { // NOSONAR
        String s = "ne pas ajouter @SuppressWarnings ni // NOSONAR";
        // int old = compute(3);
        // if (old > 0) {
        for (String item : cache) { cache.remove(item); }
        Scanner sc = new Scanner(System.in);
        Connection c = ds.getConnection();
    }

    public void tabs() {
	int x = 1;
        int y = 2;
    }
}
