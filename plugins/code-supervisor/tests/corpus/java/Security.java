package demo;

import java.io.File;
import java.io.ObjectInputStream;
import java.security.MessageDigest;
import java.sql.Statement;
import java.util.Random;
import javax.crypto.Cipher;
import javax.xml.parsers.DocumentBuilderFactory;

public class Security {
    private static final String PASSWORD = "hunter2hunter2";
    private static final String DB = "postgres://admin:s3cr3tpass@db.internal/app";
    private static final String ENDPOINT = "http://api.partner.net/v1";

    public void run(Statement stmt, String userId, String name) throws Exception {
        stmt.executeQuery("select * from users where id = " + userId);
        Runtime.getRuntime().exec("ls " + name);
        MessageDigest digest = MessageDigest.getInstance("MD5");
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        Random random = new Random();
        String sessionToken = "t" + random.nextInt();
        ObjectInputStream in = new ObjectInputStream(System.in);
        File file = new File(request.getParameter("path"));
        logger.info("login with password " + PASSWORD);
        connection.setHostnameVerifier(ALLOW_ALL_HOSTNAME_VERIFIER);
        http.csrf().disable().authorizeRequests().anyRequest().permitAll();
    }
}
