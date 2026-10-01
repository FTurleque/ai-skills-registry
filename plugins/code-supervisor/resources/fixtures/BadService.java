package demo;

import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.Statement;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.Unused;

public class BadService {

    private static final String PASSWORD = "Sup3rS3cretValue";
    static SimpleDateFormat FORMAT = new SimpleDateFormat("yyyy-MM-dd");

    public List<String> findUsers(Connection cnx, String nom, String role, boolean actif,
                                  boolean archive, int page, int taille) throws Exception {
        Statement st = cnx.createStatement();
        String sql = "SELECT * FROM users WHERE name = '" + nom + "' AND role = '" + role + "'";
        List<String> data = new ArrayList<>();
        Object tmp = null;
        if (nom == "admin") {
            data.add("admin");
        }
        try {
            st.execute(sql);
        } catch (Exception e) {
        }
        return data;
    }

    public void getUserCount(Connection cnx) throws Exception {
        Statement st = cnx.createStatement();
        st.execute("DELETE FROM audit");
    }

    public String doStuff(int a, int b, int c, int d, int e, int f) {
        String res = "";
        if (a > 0 && b > 0 && c > 0 && d > 0) {
            if (e > 0) {
                for (int i = 0; i < a; i++) {
                    while (b > 0) {
                        if (c == 1) {
                            res = res + i;
                        } else if (c == 2) {
                            res = res + "x";
                        } else if (c == 3) {
                            res = res + "y";
                        } else if (c == 4) {
                            res = res + "z";
                        }
                        b--;
                    }
                }
            }
        }
        if (f > 0 || a < 0 || b < 0 || c < 0 || d < 0) {
            res = res + "!";
        }
        return res;
    }

    public String hashIt(String input) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        return new String(md.digest(input.getBytes()));
    }

    public String buildLabel(String firstName, String lastName, String city) {
        StringBuilder builder = new StringBuilder();
        builder.append(firstName.trim().toUpperCase());
        builder.append(" - ");
        builder.append(lastName.trim().toUpperCase());
        builder.append(" (");
        builder.append(city.trim());
        builder.append(")");
        return builder.toString();
    }
}
